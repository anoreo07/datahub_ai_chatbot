"""Structured data models for the Visual Understanding layer.

Visual Understanding is an independent image-analysis layer (Qwen2.5-VL via
Fireworks) that performs OCR + structured extraction of data-related images.
It reads, understands, extracts and normalises information from dashboards,
ERD / data-model diagrams, SQL screenshots, error screenshots, metadata /
catalog screenshots, requirement / data-dictionary screenshots, Excel / table
screenshots, lineage / dependency screenshots and business-process / workflow
screenshots.

The raw vision-model output is never answered directly to the user; it is first
parsed and normalised into this structured :class:`VisionResult`, which the
router / existing skills then consume as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class VisionImageType(StrEnum):
    """Category of the recognised image, used to pick the follow-up behaviour."""

    DASHBOARD = "dashboard"
    ERD = "erd"
    SQL = "sql"
    SQL_ERROR = "sql_error"
    ERROR = "error"
    METADATA = "metadata"
    REQUIREMENT = "requirement"
    TABLE = "table"
    LINEAGE = "lineage"
    WORKFLOW = "workflow"
    ACCESS_PERMISSION = "access_permission"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


# Explicit categories the classifier must choose from (before processing).
CLASSIFIABLE_TYPES = tuple(
    t.value
    for t in (
        VisionImageType.DASHBOARD,
        VisionImageType.ERD,
        VisionImageType.SQL,
        VisionImageType.ERROR,
        VisionImageType.METADATA,
        VisionImageType.REQUIREMENT,
        VisionImageType.TABLE,
        VisionImageType.LINEAGE,
        VisionImageType.WORKFLOW,
        VisionImageType.ACCESS_PERMISSION,
        VisionImageType.IRRELEVANT,
    )
)


class VisionQuality(StrEnum):
    """Signal about how reliably the image could be read."""

    CLEAR = "clear"
    BLURRY = "blurry"
    TOO_SMALL = "too_small"
    CROPPED = "cropped"
    LOW_CONTRAST = "low_contrast"
    UNKNOWN = "unknown"


@dataclass
class VisionEntity:
    """A single detected entity / candidate (never auto-selected)."""

    name: str
    type: str = "unknown"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "confidence": self.confidence}


@dataclass
class VisionCandidate:
    """A candidate mapping for a detected signal (used when ambiguous)."""

    detected: str
    candidates: list[VisionEntity] = field(default_factory=list)
    note: str = ""


@dataclass
class VisionResult:
    """Normalised, structured output of the vision layer.

    Field semantics deliberately mirror the required JSON contract:
    ``image_type``, ``ocr_text``, ``detected_entities``, ``detected_metrics``,
    ``detected_tables``, ``detected_columns``, ``detected_relationships``,
    ``detected_errors``, ``detected_questions``, ``confidence``,
    ``recommended_skills`` and ``notes``.
    """

    image_type: VisionImageType = VisionImageType.UNKNOWN
    ocr_text: str = ""
    detected_entities: list[VisionEntity] = field(default_factory=list)
    detected_metrics: list[str] = field(default_factory=list)
    detected_tables: list[str] = field(default_factory=list)
    detected_columns: list[str] = field(default_factory=list)
    detected_relationships: list[str] = field(default_factory=list)
    detected_errors: list[dict[str, Any]] = field(default_factory=list)
    detected_questions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommended_skills: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    quality: VisionQuality = VisionQuality.CLEAR
    irrelevant: bool = False
    refusal_reason: str = ""
    candidates: list[VisionCandidate] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def readable(self) -> bool:
        """Whether the image gave us a usable, data-related signal."""
        return (
            not self.irrelevant
            and bool(self.ocr_text.strip() or self.detected_entities or self.detected_tables)
        )

    def all_mentioned(self) -> list[str]:
        """Aggregate every name-like signal for follow-up resolution."""
        out: list[str] = []
        for e in self.detected_entities:
            if e.name and e.name not in out:
                out.append(e.name)
        for t in self.detected_tables:
            if t and t not in out:
                out.append(t)
        for c in self.detected_columns:
            if c and c not in out:
                out.append(c)
        for m in self.detected_metrics:
            if m and m not in out:
                out.append(m)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_type": self.image_type.value,
            "quality": self.quality.value,
            "ocr_text": self.ocr_text,
            "detected_entities": [e.to_dict() for e in self.detected_entities],
            "detected_metrics": self.detected_metrics,
            "detected_tables": self.detected_tables,
            "detected_columns": self.detected_columns,
            "detected_relationships": self.detected_relationships,
            "detected_errors": self.detected_errors,
            "detected_questions": self.detected_questions,
            "confidence": self.confidence,
            "recommended_skills": self.recommended_skills,
            "notes": self.notes,
            "irrelevant": self.irrelevant,
            "refusal_reason": self.refusal_reason,
            "candidates": [
                {
                    "detected": c.detected,
                    "candidates": [e.to_dict() for e in c.candidates],
                    "note": c.note,
                }
                for c in self.candidates
            ],
        }
