"""Reference model — structured ground truth with provenance and versioning.

Loads/saves ReferenceDataset from JSON. Supports:
  - Auto-extraction from DataHub metadata
  - Manual authoring
  - Version tracking with provenance
  - Migration between schema versions
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

from evaluation.models import (
    ReferenceDataset,
    ReferenceExpected,
    ReferenceProvenance,
    ReferenceSample,
)


def create_reference_sample(
    sample_id: str,
    question: str,
    *,
    answer_contains: list[str] | None = None,
    answer_not_contains: list[str] | None = None,
    entities: list[str] | None = None,
    entity_types: list[str] | None = None,
    intent: str = "",
    is_no_answer: bool = False,
    fields: list[str] | None = None,
    domain: str = "",
    owner: str = "",
    citations: list[str] | None = None,
    glossary_terms: list[str] | None = None,
    lineage_upstreams: list[str] | None = None,
    lineage_downstreams: list[str] | None = None,
    metadata_fields: dict[str, str] | None = None,
    tags: list[str] | None = None,
    difficulty: str = "medium",
    category: str = "",
    notes: str = "",
    provenance_source: str = "manual",
    provenance_confidence: float = 1.0,
) -> ReferenceSample:
    """Factory for creating a ReferenceSample with proper structure."""
    return ReferenceSample(
        id=sample_id,
        question=question,
        expected=ReferenceExpected(
            answer_contains=answer_contains or [],
            answer_not_contains=answer_not_contains or [],
            entities=entities or [],
            entity_types=entity_types or [],
            intent=intent,
            is_no_answer=is_no_answer,
            fields=fields or [],
            domain=domain,
            owner=owner,
            lineage_upstreams=lineage_upstreams or [],
            lineage_downstreams=lineage_downstreams or [],
            glossary_terms=glossary_terms or [],
            citations=citations or [],
            metadata_fields=metadata_fields or {},
        ),
        provenance=ReferenceProvenance(
            source=provenance_source,
            confidence=provenance_confidence,
        ),
        tags=tags or [],
        difficulty=difficulty,
        category=category,
        notes=notes,
    )


def save_reference_dataset(dataset: ReferenceDataset, path: str | Path) -> None:
    """Save a reference dataset to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset.updated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset.to_dict(), f, indent=2, ensure_ascii=False)


def load_reference_dataset(path: str | Path) -> ReferenceDataset:
    """Load a reference dataset from JSON."""
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    samples = []
    for s in data.get("samples", []):
        expected_data = s.get("expected", {})
        provenance_data = s.get("provenance", {})
        samples.append(ReferenceSample(
            id=s.get("id", ""),
            question=s.get("question", ""),
            expected=ReferenceExpected(**expected_data),
            provenance=ReferenceProvenance(**provenance_data),
            tags=s.get("tags", []),
            difficulty=s.get("difficulty", "medium"),
            category=s.get("category", ""),
            notes=s.get("notes", ""),
            schema_version=s.get("schema_version", "1.0"),
        ))

    return ReferenceDataset(
        name=data.get("name", ""),
        version=data.get("version", "1.0"),
        description=data.get("description", ""),
        samples=samples,
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        schema_version=data.get("schema_version", "1.0"),
    )


def migrate_reference_dataset(
    dataset: ReferenceDataset,
    from_version: str,
    to_version: str,
) -> ReferenceDataset:
    """Migrate a reference dataset between schema versions.

    Currently only supports 1.0 -> 1.1 migration (adding category field).
    """
    if from_version == "1.0" and to_version == "1.1":
        for sample in dataset.samples:
            if not sample.category:
                # Infer category from tags
                if "no-answer" in sample.tags or "unanswerable" in sample.tags:
                    sample.category = "negation"
                elif "listing" in sample.tags or "count" in sample.tags:
                    sample.category = "listing"
                elif "conversational" in sample.tags:
                    sample.category = "conversational"
                else:
                    sample.category = "single_hop"
            sample.schema_version = "1.1"
        dataset.schema_version = "1.1"
        dataset.version = to_version
    return dataset
