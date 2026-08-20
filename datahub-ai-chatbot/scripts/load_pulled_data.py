"""Load DataHub JSONL pull (datahub_pull/*.txt) into PostgreSQL + OpenSearch.

Reuses the existing ingestion mappers, SyncOrchestrator persistence logic and
IndexingPipeline (chunking + embedding + vector index). Idempotent: entities
whose content_hash is unchanged are skipped unless --force is given.

Usage:
    python scripts/load_pulled_data.py [--types dataset,dashboard] [--limit N]
"""
import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

import structlog

from config.settings import settings
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from database.session import async_session_factory, init_db
from indexing.pipeline import IndexingPipeline
from ingestion.mappers.dashboard import DashboardMapper
from ingestion.mappers.dataset import DatasetMapper
from ingestion.mappers.glossary import GlossaryNodeMapper, GlossaryTermMapper
from ingestion.models import CanonicalEntity
from ingestion.normalizer import compute_content_hash
from ingestion.url_builder import DataHubUrlBuilder

log = structlog.get_logger()

PULL_DIR = Path(__file__).resolve().parent.parent / "datahub_pull"

MAPPERS = {
    "DATASET": DatasetMapper(),
    "DASHBOARD": DashboardMapper(),
    "GLOSSARY_TERM": GlossaryTermMapper(),
    "GLOSSARY_NODE": GlossaryNodeMapper(),
}

TYPE_TO_FILE = {
    "dataset": "dataset.txt",
    "dashboard": "dashboard.txt",
    "glossary_term": "glossary_term.txt",
    "glossary_node": "glossary_node.txt",
}

TYPE_TO_RAW_TYPE = {
    "dataset": "DATASET",
    "dashboard": "DASHBOARD",
    "glossary_term": "GLOSSARY_TERM",
    "glossary_node": "GLOSSARY_NODE",
}


def read_lines(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def map_to_canonical(raw: dict, url_builder: DataHubUrlBuilder | None) -> CanonicalEntity | None:
    raw_type = (raw.get("type") or "").upper()
    mapper = MAPPERS.get(raw_type)
    if mapper is None:
        return None
    try:
        return mapper.to_canonical(raw, url_builder)
    except Exception:
        log.exception("mapper_failed", urn=raw.get("urn"), raw_type=raw_type)
        return None


async def process_type(
    session,
    entity_type: str,
    limit: int,
    force: bool,
    url_builder: DataHubUrlBuilder | None,
) -> dict:
    path = PULL_DIR / TYPE_TO_FILE[entity_type]
    if not path.exists():
        log.warning("pull_file_missing", entity_type=entity_type, path=str(path))
        return {"total": 0, "synced": 0, "skipped": 0, "errors": 0, "no_chunks": 0}

    entity_repo = EntityRepository(session)
    pipeline = IndexingPipeline(session)
    total = synced = skipped = errors = no_chunks = 0

    try:
        for raw in read_lines(path):
            if limit and total >= limit:
                break
            total += 1
            canonical = map_to_canonical(raw, url_builder)
            if canonical is None:
                errors += 1
                continue
            try:
                content_hash = compute_content_hash(canonical)
                existing = await entity_repo.get_by_urn(canonical.urn)
                if existing and existing.content_hash == content_hash and not force:
                    skipped += 1
                    continue

                await pipeline.process_entity(canonical)

                entity = Entity(
                    urn=canonical.urn,
                    entity_type=canonical.entity_type,
                    name=canonical.name,
                    display_name=canonical.display_name,
                    description=canonical.description,
                    platform=canonical.platform,
                    environment=canonical.environment,
                    domain=canonical.domain,
                    datahub_url=canonical.datahub_url,
                    payload=canonical.model_dump(mode="json", exclude={"raw_payload"}),
                    content_hash=content_hash,
                )
                await entity_repo.upsert(entity)
                synced += 1
                if total % 100 == 0:
                    log.info(
                        "progress",
                        entity_type=entity_type,
                        total=total,
                        synced=synced,
                        skipped=skipped,
                        errors=errors,
                    )
            except Exception:
                errors += 1
                log.exception("load_failed", urn=canonical.urn, entity_type=entity_type)
    finally:
        await pipeline.close()

    return {"total": total, "synced": synced, "skipped": skipped, "errors": errors, "no_chunks": no_chunks}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load DataHub JSONL pull into PG + OpenSearch")
    parser.add_argument("--types", default="dataset,dashboard,glossary_term,glossary_node")
    parser.add_argument("--limit", type=int, default=0, help="max entities per type (0 = all)")
    parser.add_argument("--force", action="store_true", help="re-index even if content unchanged")
    args = parser.parse_args()

    await init_db()

    url_builder = DataHubUrlBuilder() if settings.DATAHUB_FRONTEND_URL else None
    summary: Counter = Counter()
    async with async_session_factory() as session:
        for entity_type in [t.strip() for t in args.types.split(",") if t.strip()]:
            if entity_type not in TYPE_TO_FILE:
                log.warning("unknown_type", entity_type=entity_type)
                continue
            log.info("loading_type_start", entity_type=entity_type)
            res = await process_type(session, entity_type, args.limit, args.force, url_builder)
            log.info("loading_type_done", entity_type=entity_type, **res)
            summary[entity_type] = res["synced"]

    log.info("loading_complete", summary=dict(summary))


if __name__ == "__main__":
    asyncio.run(main())
