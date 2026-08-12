"""Thinking Mode orchestrator.

Pipeline (independent layer between intent detection and execution):

    User Question
        -> Context Resolver (conversation + active entity)
        -> Complexity Classifier  (complex ? continue : None)
        -> Thinking Planner       (decompose into ExecutionPlan)
        -> Executor              (run each sub-question against metadata)
        -> Synthesizer           (merge evidence -> structured answer)

``maybe_answer`` returns ``None`` for simple questions so the caller's normal
single-intent pipeline is unchanged; it returns a fully-formed answer only for
complex / system-level / multi-hop questions. The answer is structured
(conclusion, reasons, steps, entities, risks, gaps, next steps) and grounded
solely in the metadata that actually exists.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from retrieval.thinking.complexity import ComplexityClassifier, ComplexityVerdict
from retrieval.thinking.context import ContextResolver
from retrieval.thinking.executor import ThinkingExecutor
from retrieval.thinking.planner import ThinkingPlanner
from retrieval.thinking.synthesizer import ThinkingSynthesizer

log = structlog.get_logger()


class ThinkingModeOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self._complexity = ComplexityClassifier()
        self._context = ContextResolver(session)
        self._planner = ThinkingPlanner(session)
        self._executor = ThinkingExecutor(session)
        self._synthesizer = ThinkingSynthesizer()

    async def maybe_answer(
        self,
        question: str,
        entity_mentions: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str | None:
        """Return a structured markdown answer if the question is complex;
        otherwise ``None`` (leave to the normal pipeline)."""
        # Always resolve conversational + domain context first so entity-mention
        # count (a complexity signal) is grounded, even when the caller didn't
        # pass mentions explicitly.
        ctx = await self._context.resolve(question, history=history)
        mentions = (
            list(entity_mentions or [])
            or list(ctx.active_entities or [])
            or list(ctx.all_entities or [])
        )
        verdict: ComplexityVerdict = self._complexity.evaluate(
            question, entity_mentions=mentions or None,
        )
        if not verdict.complex:
            log.info("thinking_skip", reason="simple", question=question[:100])
            return None

        plan, _ctx = await self._planner.plan(
            question, verdict, history=history,
        )
        plan = await self._executor.execute(plan)
        result = self._synthesizer.synthesize(plan)

        md = result.to_dict_md()
        log.info("thinking_answer", complex=True, steps=len(plan.steps),
                 question=question[:100])
        return md

    async def analyze(
        self,
        question: str,
        entity_mentions: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Full structured diagnostic (used by tests and for debugging)."""
        verdict = self._complexity.evaluate(question, entity_mentions)
        if not verdict.complex:
            return {"decision": "simple", "reasons": verdict.reasons}
        plan, ctx = await self._planner.plan(question, verdict, history=history)
        plan = await self._executor.execute(plan)
        result = self._synthesizer.synthesize(plan)
        return {
            "decision": "complex",
            "intent": plan.intent,
            "reasons": verdict.reasons,
            "steps": [s.to_dict() for s in plan.steps],
            "entities": plan.entities,
            "result": {
                "conclusion": result.conclusion,
                "reasons": result.key_reasons,
                "risks": result.risks,
                "missing": result.missing,
                "entities": result.related_entities,
            },
        }

    async def is_complex(
        self,
        question: str,
        entity_mentions: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> bool:
        """Expose the complexity verdict only (used to signal UI state).

        Shares the exact classifier the orchestrator uses so the caller can
        emit a ``thinking`` state event *before* running the plan and only for
        questions that will actually enter the thinking pipeline.
        """
        ctx = await self._context.resolve(question, history=history)
        mentions = (
            list(entity_mentions or [])
            or list(ctx.active_entities or [])
            or list(ctx.all_entities or [])
        )
        verdict: ComplexityVerdict = self._complexity.evaluate(
            question, entity_mentions=mentions or None,
        )
        return verdict.complex
