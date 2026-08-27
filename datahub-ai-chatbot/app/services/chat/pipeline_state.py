"""Pipeline state and turn context models for chat service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.auth.models import UserContext
from app.services.chat.entity_suggestion import EntityCorrection
from retrieval.intent import QueryIntent
from retrieval.query_models import QueryPlan


@dataclass
class TurnContext:
    """Carries inputs and authorization for a single conversation turn."""
    question: str
    user: UserContext | None = None
    conversation_id: str | None = None
    suggested_name: str | None = None
    model: str | None = None
    selected_action: str | None = None
    images: list[str] | None = None
    ragas_enabled: bool = False
    trace_id: str | None = None


@dataclass
class PipelineState:
    """Accumulates intermediate artifacts as a turn moves through the pipeline."""
    intent: QueryIntent = QueryIntent.GENERAL
    plan: QueryPlan | None = None
    target_entity: str | None = None
    corrections: list[EntityCorrection] = field(default_factory=list)
    correction_note: str | None = None
    search_results: list[Any] = field(default_factory=list)
    context_docs: list[Any] = field(default_factory=list)
    context_xml: str = ""
    citations: list[Any] = field(default_factory=list)
    system_prompt: str = ""
    answer_text: str = ""
    resolved_via: str = "hybrid"
