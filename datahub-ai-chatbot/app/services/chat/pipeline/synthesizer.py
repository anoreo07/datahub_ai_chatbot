"""Response synthesizer, postprocessor, logging, and evaluation trigger."""
from __future__ import annotations

import os
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import structlog

from app.schemas.chat import ChatResponse
from app.services.chat.pipeline.grounding import build_grounded_fallback
from guardrails.validation import NO_EVIDENCE_RESPONSE
from retrieval.context_builder import build_context
from retrieval.intent import QueryIntent

if TYPE_CHECKING:
    from app.services.chat.context import ChatContext

log = structlog.get_logger()


async def log_interaction_async(op: str, **kwargs: Any) -> None:
    """Write interaction log using a dedicated session to avoid autoflush conflicts."""
    if os.getenv("APP_ENV") == "test":
        return
    try:
        from app.services.interaction_logger import InteractionLogger
        from database.session import async_session_factory

        async with async_session_factory() as bg_session:
            logger = InteractionLogger(bg_session)
            if op == "request":
                await logger.log_request(**kwargs)
            elif op == "response":
                await logger.log_response(**kwargs)
            await bg_session.commit()
    except Exception:  # noqa: BLE001
        log.warning("interaction_log_async_failed", op=op)


async def postprocess_response(
    ctx: ChatContext,
    res: ChatResponse,
    t_start: float,
    uid: str,
    cid: str,
    question: str,
) -> ChatResponse:
    """Updates response duration and records render state in conversation history."""
    if res.response_time_ms is None:
        res.response_time_ms = int((time.perf_counter() - t_start) * 1000)

    # Data fidelity verification (E-CONTRA auto-correction)
    try:
        if hasattr(ctx, "fidelity_checker") and hasattr(ctx, "anchor_builder"):
            anchor = ctx.anchor_builder.build(question, [])
            fidelity_report = await ctx.fidelity_checker.check(
                anchor=anchor,
                intent=res.intent or "GENERAL",
                answer=res.answer,
                resolved_entities=res.entities or [],
            )
            if not fidelity_report.passed and fidelity_report.corrected_answer:
                res.answer = fidelity_report.corrected_answer
                log.info("fidelity_correction_applied", trace_id=res.trace_id, violations=len(fidelity_report.violations))
    except Exception:  # noqa: BLE001
        log.warning("fidelity_check_in_postprocess_failed", exc_info=True)

    try:

        from database.models import ConversationHistory
        from sqlalchemy import select

        result = await ctx.session.execute(
            select(ConversationHistory)
            .where(
                ConversationHistory.user_id == uid,
                ConversationHistory.conversation_id == cid,
            )
            .order_by(ConversationHistory.id.desc())
            .limit(1)
        )
        latest = result.scalars().first()
        if latest:
            rs = dict(latest.render_state or {})
            rs["response_time_ms"] = res.response_time_ms
            if res.intent:
                rs["intent"] = res.intent
            if res.trace_id:
                rs["trace_id"] = res.trace_id
            if res.confidence:
                rs["confidence"] = res.confidence
            if res.entities:
                rs["entities"] = [e.model_dump() for e in res.entities]
            if res.citations:
                rs["citations"] = [
                    c.model_dump() if hasattr(c, "model_dump") else dict(c)
                    for c in res.citations
                ]
            if res.lineage:
                rs["lineage"] = res.lineage.model_dump()
            if res.selected_action:
                rs["selected_action"] = res.selected_action

            latest.render_state = rs
            await ctx.session.commit()

    except Exception as exc:
        log.exception(
            "postprocess_response_render_state_failed",
            trace_id=res.trace_id,
            error=str(exc),
        )

    return res


async def background_ragas_eval(
    ctx: ChatContext | None,
    trace_id: str,
    question: str,
    answer: str,
    contexts: list[Any],
    history: list[Any] | None = None,
) -> None:
    """Run RAGAS evaluation in background. Never raises, never blocks chat."""
    if os.getenv("APP_ENV") == "test":
        return

    from database.repositories.job_repository import JobRepository
    from database.repositories.notification_repository import NotificationRepository
    from database.session import async_session_factory

    try:
        from evaluation.ragas_evaluator import evaluate_interaction

        async with async_session_factory() as bg_session:
            job_repo = JobRepository(bg_session)
            notif_repo = NotificationRepository(bg_session)

            user_id = (
                getattr(ctx, "user", None).user_id
                if ctx and hasattr(ctx, "user") and getattr(ctx, "user", None)
                else None
            )
            job = await job_repo.create(
                type="ragas_evaluation",
                title="RAGAS Evaluation",
                message=f"Starting evaluation for trace {trace_id[:8]}...",
                user_id=user_id,
                job_metadata={"trace_id": trace_id},
            )

            await notif_repo.create(
                job_id=job.id,
                user_id=user_id or "system",
                type="ragas_evaluation",
                title="RAGAS Evaluation",
                message="Starting evaluation...",
                status="running",
            )

            from app.services.interaction_logger import InteractionLogger

            ctx_strings: list[str] = []
            for c in contexts:
                if isinstance(c, str):
                    ctx_strings.append(c)
                elif hasattr(c, "content"):
                    ctx_strings.append(str(c.content))
                else:
                    ctx_strings.append(str(c))

            bg_logger = InteractionLogger(bg_session)
            await bg_logger.set_evaluation_status(trace_id, "RUNNING")

            if history:
                from evaluation.ragas_evaluator import evaluate_conversation_turn

                result = await evaluate_conversation_turn(
                    question=question,
                    answer=answer,
                    retrieved_contexts=ctx_strings,
                    conversation_history=history,
                    reference="\n".join(ctx_strings) if ctx_strings else None,
                    timeout_seconds=120.0,
                )
            else:
                result = await evaluate_interaction(
                    question=question,
                    answer=answer,
                    retrieved_contexts=ctx_strings,
                    reference="\n".join(ctx_strings) if ctx_strings else None,
                    timeout_seconds=120.0,
                )

            await bg_logger.update_ragas_scores(
                trace_id=trace_id,
                faithfulness=result.faithfulness,
                faithfulness_status=result.faithfulness_status,
                answer_relevancy=result.answer_relevancy,
                answer_relevancy_status=result.answer_relevancy_status,
                context_precision=result.context_precision,
                context_precision_status=result.context_precision_status,
                context_recall=result.context_recall,
                context_recall_status=result.context_recall_status,
                evaluation_model=result.evaluation_model,
                evaluation_error=result.error,
            )

            await job_repo.mark_success(job.id)
            await bg_session.commit()
            log.info("ragas_background_eval_done", trace_id=trace_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("ragas_background_eval_failed", trace_id=trace_id, error=str(exc))


async def generate_or_fallback(
    generator: Any,
    question: str,
    results: Sequence[Any],
    intent: QueryIntent,
    history: list[Any] | None,
    on_token: Any,
    recommendation: Any,
) -> tuple[str, list[Any], list[Any], str, str]:
    """LLM generation with a deterministic, metadata-grounded fallback."""
    if on_token:
        answer_text, citations, docs, context_xml, confidence = (
            await generator.generate_stream(
                question,
                results,
                intent,
                history=history,
                on_token=on_token,
                recommendation=recommendation,
            )
        )
    else:
        answer_text, citations, docs, context_xml, confidence = (
            await generator.generate(
                question,
                results,
                intent,
                history=history,
                recommendation=recommendation,
            )
        )
    if answer_text and "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời" not in answer_text:
        return answer_text, citations, docs, context_xml, confidence
    fallback = build_grounded_fallback(intent, results)
    if not fallback:
        return NO_EVIDENCE_RESPONSE, citations, docs, context_xml, "low"
    docs, context_xml = build_context(results)
    log.info(
        "generation_fallback_deterministic",
        intent=intent.value,
        question=question[:100],
        entities=len(results),
    )
    return fallback, citations, docs, context_xml, "low"
