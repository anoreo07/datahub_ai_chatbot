"""Benchmark generator — creates evaluation scenarios from DataHub metadata.

All generated samples are GENERAL (not optimized for specific testcases).
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.entity_repository import EntityRepository
from evaluation.models import ReferenceDataset
from evaluation.reference_model import (
    create_reference_sample,
    save_reference_dataset,
)

log = structlog.get_logger(__name__)


async def generate_benchmark_from_datahub(
    session: AsyncSession,
    *,
    max_samples: int = 50,
    output_path: str | None = None,
) -> ReferenceDataset:
    """Generate a benchmark dataset from live DataHub metadata."""
    repo = EntityRepository(session)
    samples = []
    counter = 0

    datasets = await repo.list_by_type("dataset")
    dashboards = await repo.list_by_type("dashboard")
    glossary_terms = await repo.list_by_type("glossary_term")

    # Schema lookup
    for entity in datasets[: min(10, max_samples // 4)]:
        counter += 1
        payload = entity.payload or {}
        fields = [f.get("name", "") for f in payload.get("schema_fields", []) if f.get("name")]
        if fields:
            samples.append(create_reference_sample(
                sample_id=f"BENCH-{counter:03d}",
                question=f"{entity.name} co nhung field nao?",
                entities=[entity.urn], intent="SCHEMA_LOOKUP",
                fields=fields[:5], tags=["schema", "benchmark", "auto"],
                difficulty="easy", category="single_hop",
                provenance_source="datahub_query",
            ))
        if len(samples) >= max_samples:
            break

    # Owner lookup
    for entity in datasets[: min(8, max_samples // 5)]:
        counter += 1
        payload = entity.payload or {}
        owners = [o.get("name", "") for o in payload.get("owners", []) if o.get("name")]
        if owners:
            samples.append(create_reference_sample(
                sample_id=f"BENCH-{counter:03d}",
                question=f"Ai la owner cua {entity.name}?",
                entities=[entity.urn], intent="OWNER_LOOKUP",
                owner=owners[0], tags=["owner", "benchmark", "auto"],
                difficulty="easy", category="single_hop",
                provenance_source="datahub_query",
            ))
        if len(samples) >= max_samples:
            break

    # Glossary terms
    for term in glossary_terms[: min(6, max_samples // 6)]:
        counter += 1
        samples.append(create_reference_sample(
            sample_id=f"BENCH-{counter:03d}",
            question=f"Glossary term {term.name} la gi?",
            entities=[term.urn], intent="TERM_DEFINITION",
            answer_contains=[term.name] if term.name else [],
            tags=["glossary", "benchmark", "auto"],
            difficulty="easy", category="single_hop",
            provenance_source="datahub_query",
        ))
        if len(samples) >= max_samples:
            break

    # Lineage
    for entity in datasets[: min(5, max_samples // 7)]:
        counter += 1
        payload = entity.payload or {}
        upstreams = payload.get("upstreams", [])
        samples.append(create_reference_sample(
            sample_id=f"BENCH-{counter:03d}",
            question=f"{entity.name} lay du lieu tu dau?",
            entities=[entity.urn], intent="LINEAGE",
            lineage_upstreams=upstreams[:3] if upstreams else [],
            tags=["lineage", "benchmark", "auto"],
            difficulty="medium", category="single_hop",
            provenance_source="datahub_query",
        ))
        if len(samples) >= max_samples:
            break

    # Missing metadata
    no_desc = [e for e in datasets if not (e.payload or {}).get("description")]
    if no_desc:
        counter += 1
        samples.append(create_reference_sample(
            sample_id=f"BENCH-{counter:03d}",
            question="Dataset nao chua co mo ta?",
            intent="MISSING_DESCRIPTION", tags=["metadata", "listing", "auto"],
            difficulty="medium", category="listing",
            provenance_source="datahub_query",
        ))

    no_owner = [e for e in datasets if not (e.payload or {}).get("owners")]
    if no_owner:
        counter += 1
        samples.append(create_reference_sample(
            sample_id=f"BENCH-{counter:03d}",
            question="Dataset thieu chu so huu",
            intent="MISSING_OWNER", tags=["metadata", "listing", "auto"],
            difficulty="medium", category="listing",
            provenance_source="datahub_query",
        ))

    # No-answer cases
    counter += 1
    samples.append(create_reference_sample(
        sample_id=f"BENCH-{counter:03d}",
        question="Company XYZ khong ton tai co ton tai khong?",
        is_no_answer=True, intent="ENTITY_EXISTS",
        tags=["no-answer", "benchmark", "auto"],
        difficulty="easy", category="negation",
        provenance_source="synthetic",
    ))

    counter += 1
    samples.append(create_reference_sample(
        sample_id=f"BENCH-{counter:03d}",
        question="Mau sac yeu thich cua CEO la gi?",
        is_no_answer=True, intent="GENERAL",
        tags=["no-answer", "unanswerable", "benchmark", "auto"],
        difficulty="easy", category="negation",
        provenance_source="synthetic",
    ))

    # Count query
    counter += 1
    samples.append(create_reference_sample(
        sample_id=f"BENCH-{counter:03d}",
        question="Co bao nhieu dataset trong he thong?",
        intent="COUNT_ENTITIES",
        tags=["count", "listing", "benchmark", "auto"],
        difficulty="easy", category="listing",
        provenance_source="datahub_query",
        metadata_fields={"count": str(len(datasets))},
    ))

    dataset = ReferenceDataset(
        name="DataHub Auto-Generated Benchmark",
        version="1.0",
        description="Auto-generated from DataHub metadata",
        samples=samples,
        created_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
    )

    if output_path:
        save_reference_dataset(dataset, output_path)
        log.info("benchmark_generated", path=output_path, sample_count=len(samples))

    return dataset
