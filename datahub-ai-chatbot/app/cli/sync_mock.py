#!/usr/bin/env python3
"""CLI to sync mock DataHub data to PostgreSQL."""
import argparse
import asyncio
from collections import Counter

import structlog

from config.settings import settings
from database.repositories.entity_repository import EntityRepository
from database.session import async_session_factory, init_db
from indexing.pipeline import IndexingPipeline
from ingestion.mock_source import MockDataHubSource
from ingestion.sync import SyncOrchestrator

log = structlog.get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync mock DataHub data to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Print entities that would be synced without writing to DB")
    parser.add_argument("--entity-type", type=str, help="Sync only this entity type (e.g. dataset, dashboard)")
    parser.add_argument("--urn", type=str, help="Sync only this entity URN")
    parser.add_argument("--rebuild", action="store_true", help="Also run IndexingPipeline after sync")
    args = parser.parse_args()
    asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> None:
    log.info("sync_mock_started", dry_run=args.dry_run, entity_type=args.entity_type, urn=args.urn, rebuild=args.rebuild)

    if not args.dry_run and settings.USE_IN_MEMORY_DATABASE:
        await init_db()

    source = MockDataHubSource(fixtures_dir=settings.MOCK_DATAHUB_FIXTURES_PATH)

    if args.dry_run:
        entities = list(source.list_all())
        if args.entity_type:
            entities = [e for e in entities if e.entity_type == args.entity_type]
        if args.urn:
            entities = [e for e in entities if e.urn == args.urn]

        type_counts = Counter(e.entity_type for e in entities)
        log.info("dry_run_result", count=len(entities), types=dict(type_counts))
        for entity in sorted(entities, key=lambda e: (e.entity_type, e.urn)):
            print(f"  {entity.urn}  ({entity.entity_type})  {entity.name}")
        print(f"\nTotal: {len(entities)} entities")
        if type_counts:
            print(f"By type: {dict(type_counts)}")
        return

    async with async_session_factory() as session:
        orchestrator = SyncOrchestrator(session)

        if args.urn:
            success = await orchestrator.sync_entity_by_urn(args.urn)
            log.info("sync_by_urn_complete", urn=args.urn, success=success)
        elif args.entity_type:
            count = await orchestrator.sync_entity_type(args.entity_type)
            log.info("sync_by_type_complete", entity_type=args.entity_type, count=count)
        else:
            results = await orchestrator.run_full_sync()
            log.info("full_sync_complete", results=results)

        if args.rebuild:
            pipeline = IndexingPipeline(session)
            processed = await pipeline.process_pending_jobs(max_jobs=100)
            log.info("rebuild_complete", processed=processed)

        repo = EntityRepository(session)
        total = await repo.count_by_type()
        by_type = [(t, await repo.count_by_type(t)) for t in
                   ("dataset", "dashboard", "glossary_term", "glossary_node", "document")]
        by_type = {t: c for t, c in by_type if c > 0}
        log.info("sync_summary", total=total, by_type=by_type)
        print(f"\nSync complete — total entities in DB: {total}")
        if by_type:
            print(f"By type: {by_type}")


if __name__ == "__main__":
    main()
