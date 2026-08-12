"""Data models for the Thinking Mode layer.

Thinking Mode is an independent planning/reasoning layer between intent
detection and execution. It decomposes system-level / multi-hop questions into
an ExecutionPlan of sub-steps, each planned with one or more retrieval
"knowledge sources", then merges the per-step evidence into a structured,
traceable answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class KnowledgeSource(StrEnum):
    DATASET_METADATA = "dataset_metadata"
    SCHEMA_FIELD = "schema_field"
    GLOSSARY = "glossary"
    LINEAGE = "lineage"
    OWNER = "owner"
    DOCUMENT = "document"
    DOMAIN = "domain"
    DATA_QUALITY = "data_quality"
    DOWNSTREAM = "downstream"
    UPSTREAM = "upstream"
    PERMISSION = "permission"
    SUGGESTION = "suggestion"


@dataclass
class EvidenceRecord:
    urn: str
    detail: str
    source: KnowledgeSource
    snippet: str = ""
    confidence: float = 0.0
    entity_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "urn": self.urn,
            "detail": self.detail,
            "source": self.source.value,
            "snippet": self.snippet,
            "confidence": self.confidence,
            "entity_type": self.entity_type,
            "extra": self.extra,
        }


@dataclass
class PlanStep:
    """One sub-question of an execution plan."""

    step_id: str
    name: str
    sub_question: str
    goal: str
    sources: list[KnowledgeSource] = field(default_factory=list)
    entity: str | None = None
    conclusion_criteria: str = ""
    stop_condition: str = ""
    status: str = "pending"          # pending | done | insufficient | failed
    evidence: list[EvidenceRecord] = field(default_factory=list)
    note: str = ""

    @property
    def is_complete(self) -> bool:
        return self.status in ("done", "insufficient")

    def sources_str(self) -> str:
        return ", ".join(s.value for s in self.sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "sub_question": self.sub_question,
            "goal": self.goal,
            "sources": [s.value for s in self.sources],
            "entity": self.entity,
            "conclusion_criteria": self.conclusion_criteria,
            "stop_condition": self.stop_condition,
            "status": self.status,
            "note": self.note,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class ExecutionPlan:
    """The full multi-step, multi-source plan for a complex question."""

    question: str
    intent: str                    # THINKING_<CATEGORY> e.g. THINKING_OVERVIEW
    goal: str
    entities: list[str] = field(default_factory=list)
    steps: list[PlanStep] = field(default_factory=list)
    system_view: str = ""          # requested architectural/overview angle (optional)

    @property
    def is_complex(self) -> bool:
        return len(self.steps) > 1 or self.intent.startswith("THINKING_")


@dataclass
class EffortResult:
    """Aggregated structured answer collected from an ExecutionPlan."""

    conclusion: str
    key_reasons: list[str] = field(default_factory=list)
    steps_log: list[str] = field(default_factory=list)   # one line per step + how decided
    related_entities: list[tuple[str, str]] = field(default_factory=list)  # (name, urn)
    risks: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)     # steps with no data

    def to_answer_md(self) -> str:
        """Render the structured result into a markdown chat answer (VI + EN)."""
        lines: list[str] = []
        lines.append("### Kết luận")
        lines.append(self.conclusion.strip())
        lines.append("")
        if self.key_reasons:
            lines.append("### Lý do chính")
            for r in self.key_reasons:
                lines.append(f"- {r}")
            lines.append("")
        if self.related_entities:
            lines.append("### Các thực thể liên quan")
            for name, urn in self.related_entities:
                lines.append(f"- {name} `{urn}`")
            lines.append("")
        if self.risks:
            lines.append("### Rủi ro / điểm chưa chắc chắn")
            for r in self.risks:
                lines.append(f"- {r}")
            lines.append("")
        if self.missing:
            lines.append("### Thiếu dữ liệu")
            lines.append("Các bước/khía cạnh chưa có dữ liệu đủ để khẳng định:")
            for m in self.missing:
                lines.append(f"- {m}")
            lines.append("")
        if self.next_steps:
            lines.append("### Khuyến nghị tiếp theo")
            for n in self.next_steps:
                lines.append(f"- {n}")
        return "\n".join(lines).strip()

    def to_dict_md(self) -> str:
        return self.to_answer_md()



@dataclass
class ThinkingContext:
    """Resolved conversational + domain context for a question."""

    question: str
    active_entities: list[str] = field(default_factory=list)
    all_entities: list[str] = field(default_factory=list)
    conversation_summary: str = ""
    related_terms: list[str] = field(default_factory=list)
    related_domains: list[str] = field(default_factory=list)
    multi_goal: bool = False
    cross_domain: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "active_entities": self.active_entities,
            "all_entities": self.all_entities,
            "multi_goal": self.multi_goal,
            "cross_domain": self.cross_domain,
        }
