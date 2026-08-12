"""Image Context Manager — build, store and reconstruct the internal Image Context.

An :class:`ImageContext` is the normalised, DataHub-grounded interpretation of
one uploaded image: OCR, entities, candidate dataset / dashboard / glossary
mappings, fields, lineage, SQL and any fetched metadata. It is *internal
evidence* used for reasoning — it is never shown verbatim to the user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class ImageContext:
    image_id: str
    user_id: str = ""
    conversation_id: str | None = None
    image_type: str = "unknown"
    file_name: str = ""
    ocr_text: str = ""
    detected_entities: list[dict[str, Any]] = field(default_factory=list)
    detected_metrics: list[str] = field(default_factory=list)
    detected_tables: list[str] = field(default_factory=list)
    detected_columns: list[str] = field(default_factory=list)
    detected_relationships: list[str] = field(default_factory=list)
    detected_errors: list[dict[str, Any]] = field(default_factory=list)
    detected_questions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    irrelevant: bool = False
    refusal_reason: str = ""
    # DataHub mapping (filled during enrichment).
    dataset_name: str | None = None
    dataset_urn: str | None = None
    # DataHub-grounded domain / glossary / dashboard / lineage / metadata facts.
    domain: str | None = None
    owner: str | None = None
    description: str | None = None
    platform: str | None = None
    glossary_terms: list[str] = field(default_factory=list)
    graphics_summary: str = ""
    lineage_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    parse_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "image_type": self.image_type,
            "file_name": self.file_name,
            "ocr_text": self.ocr_text,
            "detected_entities": self.detected_entities,
            "detected_metrics": self.detected_metrics,
            "detected_tables": self.detected_tables,
            "detected_columns": self.detected_columns,
            "detected_relationships": self.detected_relationships,
            "detected_errors": self.detected_errors,
            "detected_questions": self.detected_questions,
            "notes": self.notes,
            "confidence": self.confidence,
            "irrelevant": self.irrelevant,
            "refusal_reason": self.refusal_reason,
            "dataset_name": self.dataset_name,
            "dataset_urn": self.dataset_urn,
            "domain": self.domain,
            "owner": self.owner,
            "description": self.description,
            "platform": self.platform,
            "glossary_terms": self.glossary_terms,
            "graphics_summary": self.graphics_summary,
            "metadata": self.metadata,
            "parse_error": self.parse_error,
        }


class ImageContextManager:
    """Builds and serialises :class:`ImageContext` from a raw vision result."""

    def build(
        self,
        image_id: str,
        user_id: str,
        conversation_id: str | None,
        file_name: str,
        result: dict[str, Any],
    ) -> ImageContext:
        entities = result.get("detected_entities") or []
        tables = result.get("detected_tables") or []
        columns = result.get("detected_columns") or []
        relationships = result.get("detected_relationships") or []
        metrics = result.get("detected_metrics") or []

        image_type = str(result.get("image_type") or "unknown")

        # Best dataset candidate: prefer explicit dataset entities, else tables.
        dataset_name = result.get("dataset_name")
        dataset_urn = result.get("dataset_urn")
        if not dataset_name:
            for e in entities:
                if str(e.get("type") or "") in ("dataset", "datahub_dataset"):
                    dataset_name = e.get("name")
                    break
        if not dataset_name and tables:
            dataset_name = tables[0]

        # Domain / owner / platform / description pushed in by enrichment.
        metadata = result.get("metadata") or {}
        domain = result.get("domain") or metadata.get("domain")
        owner = result.get("owner") or metadata.get("owner")
        description = result.get("description") or metadata.get("description")
        platform = result.get("platform") or metadata.get("platform")

        return ImageContext(
            image_id=image_id,
            user_id=user_id,
            conversation_id=conversation_id,
            image_type=image_type,
            file_name=file_name,
            ocr_text=str(result.get("ocr_text") or ""),
            detected_entities=entities,
            detected_metrics=metrics,
            detected_tables=tables,
            detected_columns=columns,
            detected_relationships=relationships,
            detected_errors=result.get("detected_errors") or [],
            detected_questions=result.get("detected_questions") or [],
            notes=result.get("notes") or [],
            confidence=float(result.get("confidence") or 0.0),
            irrelevant=bool(result.get("irrelevant")),
            refusal_reason=str(result.get("refusal_reason") or ""),
            dataset_name=dataset_name,
            dataset_urn=dataset_urn,
            domain=domain,
            owner=owner,
            description=description,
            platform=platform,
            glossary_terms=result.get("glossary_terms") or [],
            graphics_summary=str(result.get("graphics_summary") or ""),
            metadata=metadata,
            parse_error=bool(result.get("parse_error")),
        )


def context_from_dict(data: dict[str, Any]) -> ImageContext:
    """Reconstruct an ImageContext from a stored/transmitted dict."""
    return ImageContext(
        image_id=data.get("image_id") or "",
        user_id=data.get("user_id") or "",
        conversation_id=data.get("conversation_id"),
        image_type=data.get("image_type") or "unknown",
        file_name=data.get("file_name") or "",
        ocr_text=data.get("ocr_text") or "",
        detected_entities=data.get("detected_entities") or [],
        detected_metrics=data.get("detected_metrics") or [],
        detected_tables=data.get("detected_tables") or [],
        detected_columns=data.get("detected_columns") or [],
        detected_relationships=data.get("detected_relationships") or [],
        detected_errors=data.get("detected_errors") or [],
        detected_questions=data.get("detected_questions") or [],
        notes=data.get("notes") or [],
        confidence=float(data.get("confidence") or 0.0),
        irrelevant=bool(data.get("irrelevant")),
        refusal_reason=data.get("refusal_reason") or "",
        dataset_name=data.get("dataset_name"),
        dataset_urn=data.get("dataset_urn"),
        domain=data.get("domain"),
        owner=data.get("owner"),
        description=data.get("description"),
        platform=data.get("platform"),
        glossary_terms=data.get("glossary_terms") or [],
        graphics_summary=data.get("graphics_summary") or "",
        metadata=data.get("metadata") or {},
        parse_error=bool(data.get("parse_error")),
    )
