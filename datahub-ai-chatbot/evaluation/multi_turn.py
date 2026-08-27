"""Multi-turn evaluation support — evaluates conversation flows across turns.

Tracks entity propagation, context continuity, anaphora resolution,
and cross-turn citation consistency.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any

from evaluation.models import (
    EvaluationReport,
    EvaluationResult,
    FailureLayer,
    FailureReason,
    PipelineTrace,
    ReferenceExpected,
    ReferenceSample,
    RootCause,
    SystemMetrics,
)


@dataclass
class ConversationTurn:
    """A single turn in a multi-turn evaluation conversation."""
    turn_id: str
    question: str
    expected: ReferenceExpected = field(default_factory=ReferenceExpected)
    # What we expect from conversation context
    expected_active_entity: str | None = None
    expected_referenced_evidence: list[str] = field(default_factory=list)
    depends_on_turn: str | None = None  # turn_id this turn depends on


@dataclass
class ConversationScenario:
    """A multi-turn conversation scenario for evaluation."""
    scenario_id: str
    name: str
    description: str = ""
    turns: list[ConversationTurn] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class TurnResult:
    """Evaluation result for a single turn in a multi-turn conversation."""
    turn_id: str
    question: str
    answer: str
    system_metrics: SystemMetrics = field(default_factory=SystemMetrics)
    root_cause: RootCause = field(default_factory=RootCause)
    # Cross-turn metrics
    entity_propagated: bool = False
    context_continuity: float = 0.0
    anaphora_resolved: bool = False
    citation_consistent: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "question": self.question,
            "answer": self.answer[:300],
            "system_metrics": self.system_metrics.to_dict(),
            "root_cause": self.root_cause.to_dict(),
            "entity_propagated": self.entity_propagated,
            "context_continuity": self.context_continuity,
            "anaphora_resolved": self.anaphora_resolved,
            "citation_consistent": self.citation_consistent,
            "error": self.error,
        }


@dataclass
class MultiTurnResult:
    """Complete result for a multi-turn conversation evaluation."""
    scenario_id: str
    scenario_name: str
    turn_results: list[TurnResult] = field(default_factory=list)
    overall_success: bool = False
    conversation_flow_score: float = 0.0
    entity_tracking_accuracy: float = 0.0
    context_propagation_score: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "turn_results": [t.to_dict() for t in self.turn_results],
            "overall_success": self.overall_success,
            "conversation_flow_score": self.conversation_flow_score,
            "entity_tracking_accuracy": self.entity_tracking_accuracy,
            "context_propagation_score": self.context_propagation_score,
            "timestamp": self.timestamp,
        }


class MultiTurnEvaluator:
    """Evaluates multi-turn conversation scenarios."""

    def __init__(self, chat_service_fn: Any):
        self._chat_fn = chat_service_fn

    async def evaluate_scenario(
        self,
        scenario: ConversationScenario,
        conversation_id: str | None = None,
    ) -> MultiTurnResult:
        """Run a full multi-turn conversation scenario."""
        from app.schemas.chat import ChatRequest

        cid = conversation_id or f"eval_{scenario.scenario_id}"
        turn_results: list[TurnResult] = []
        prev_answer = ""
        prev_entity = None
        prev_citations: list[str] = []

        for turn in scenario.turns:
            try:
                response = await self._chat_fn(
                    turn.question,
                    conversation_id=cid,
                )

                answer = getattr(response, "answer", "")
                entities = getattr(response, "entities", [])
                citations = getattr(response, "citations", [])
                confidence = getattr(response, "confidence", "low")

                # Entity propagation check
                entity_urns = [
                    e.urn if hasattr(e, "urn") else str(e) for e in entities
                ] if entities else []
                entity_propagated = False
                if turn.expected_active_entity:
                    entity_propagated = turn.expected_active_entity in entity_urns
                elif prev_entity:
                    entity_propagated = prev_entity in entity_urns

                # Context continuity — answer references previous context
                context_continuity = 0.0
                if prev_answer:
                    prev_keywords = set(prev_answer.lower().split())
                    curr_keywords = set(answer.lower().split())
                    overlap = prev_keywords.intersection(curr_keywords)
                    if prev_keywords:
                        context_continuity = len(overlap) / len(prev_keywords)

                # Anaphora resolution
                anaphora_resolved = True
                pronouns = ["no", "do", "nay", "day", "do", "chung"]
                if any(p in turn.question.lower() for p in pronouns):
                    anaphora_resolved = len(entity_urns) > 0

                # Citation consistency
                citation_uris = [
                    c.entity_urn for c in citations if hasattr(c, "entity_urn")
                ] if citations else []
                citation_consistent = True
                if prev_citations and citation_uris:
                    citation_consistent = bool(
                        set(citation_uris).intersection(set(prev_citations))
                    )

                # Build metrics
                system_metrics = SystemMetrics(
                    entity_accuracy=1.0 if entity_propagated else 0.0,
                    retrieval_hit=len(entity_urns) > 0,
                    context_coverage=context_continuity,
                )

                root_cause = RootCause(
                    primary_layer=FailureLayer.PASSED,
                    primary_reason=FailureReason.NONE,
                    confidence=0.8,
                )

                turn_result = TurnResult(
                    turn_id=turn.turn_id,
                    question=turn.question,
                    answer=answer[:500],
                    system_metrics=system_metrics,
                    root_cause=root_cause,
                    entity_propagated=entity_propagated,
                    context_continuity=context_continuity,
                    anaphora_resolved=anaphora_resolved,
                    citation_consistent=citation_consistent,
                )
                turn_results.append(turn_result)

                prev_answer = answer
                prev_entity = entity_urns[0] if entity_urns else prev_entity
                prev_citations = citation_uris

            except Exception as exc:
                turn_results.append(TurnResult(
                    turn_id=turn.turn_id,
                    question=turn.question,
                    answer="",
                    root_cause=RootCause(
                        primary_layer=FailureLayer.EVALUATION,
                        primary_reason=FailureReason.EVALUATION_ERROR,
                        detail=str(exc),
                    ),
                    error=str(exc),
                ))

        # Aggregate scores
        n = len(turn_results)
        if n == 0:
            return MultiTurnResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
            )

        entity_tracking = sum(1 for t in turn_results if t.entity_propagated) / n
        context_prop = sum(t.context_continuity for t in turn_results) / n
        anaphora_score = sum(1 for t in turn_results if t.anaphora_resolved) / n
        citation_score = sum(1 for t in turn_results if t.citation_consistent) / n

        flow_score = (entity_tracking + context_prop + anaphora_score + citation_score) / 4
        overall = all(t.root_cause.primary_layer == FailureLayer.PASSED for t in turn_results)

        return MultiTurnResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            turn_results=turn_results,
            overall_success=overall,
            conversation_flow_score=round(flow_score, 4),
            entity_tracking_accuracy=round(entity_tracking, 4),
            context_propagation_score=round(context_prop, 4),
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        )
