"""Data Quality Report schema.

Defines the structured quality report returned by the Data Quality Check
feature. The report is intentionally dependency-free (no imports from other
schema modules) so it can be embedded in ``ChatResponse`` without creating an
import cycle, and rendered/exported (TXT/PDF) without regeneration.
"""
import datetime
from enum import StrEnum

from pydantic import BaseModel


class QualityStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"
    SOURCE_ERROR = "source_error"


class QualityFinding(BaseModel):
    name: str = ""
    status: QualityStatus = QualityStatus.NOT_EVALUATED
    detail: str = ""
    value: str = ""
    applicable: bool = True
    source: str = "metadata"


class QualitySection(BaseModel):
    key: str = ""
    title: str = ""
    score: int = 0
    status: QualityStatus = QualityStatus.NOT_EVALUATED
    findings: list[QualityFinding] = []


class QualityRecommendation(BaseModel):
    priority: str = "medium"  # high | medium | low
    text: str = ""


class QualityReport(BaseModel):
    dataset: str = ""
    entity_name: str = ""
    entity_type: str = "dataset"
    platform: str = ""
    urn: str = ""
    url: str | None = None
    generated_at: str = ""
    generated_by: str = ""
    overall_score: int = 0
    rating: str = "Poor"  # Excellent | Good | Fair | Poor
    profiling_available: bool = False
    sections: list[QualitySection] = []
    recommendations: list[QualityRecommendation] = []
    not_evaluated_checks: list[str] = []
    missing_fields: list[str] = []
    not_applicable_fields: list[str] = []
    valid: bool = True

    @staticmethod
    def now_iso() -> str:
        return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

