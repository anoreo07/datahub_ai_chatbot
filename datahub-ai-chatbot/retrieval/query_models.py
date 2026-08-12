"""Structured models for the semantic intent classifier and query planner.

These dataclasses are the contract between the LLM classifier/planner and the
execution layer (tool registry + graph traversal). Keeping them in one module
avoids circular imports between ``classifier``, ``planner_executor`` and the
service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryFilter:
    """A single dimension filter extracted from the question."""

    dimension: str | None = None  # domain | platform | tag | owner | certified | None
    value: str | None = None


@dataclass
class QueryParams:
    """Free-form parameters extracted from the question."""

    depth: int | None = None
    top_k: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryPlan:
    """The structured interpretation of a user question."""

    intent: str = "GENERAL"
    entity_refs: list[str] = field(default_factory=list)
    entity_type: str | None = None
    filter: QueryFilter = field(default_factory=QueryFilter)
    direction: str | None = None  # upstream | downstream | both | None
    params: QueryParams = field(default_factory=QueryParams)
    is_composite: bool = False
    confidence: str = "medium"  # high | medium | low
    steps: list[PlanStep] = field(default_factory=list)
    source: str = "classifier"  # classifier | regex | mock | fallback

    @property
    def primary_entity(self) -> str | None:
        """The first non-empty entity reference, trimmed."""
        for ref in self.entity_refs:
            name = (ref or "").strip()
            if name:
                return name
        return None

    def to_step_dicts(self) -> list[dict[str, Any]]:
        """Steps serialized as plain dicts (for logging / tests)."""
        return [s.to_dict() for s in self.steps]


@dataclass
class PlanStep:
    """A single executable step produced by the query planner."""

    op: str
    params: dict[str, Any] = field(default_factory=dict)
    purpose: str = ""
    depends_on: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "params": self.params,
            "purpose": self.purpose,
            "depends_on": self.depends_on,
        }
