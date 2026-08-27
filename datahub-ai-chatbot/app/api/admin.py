"""Admin API endpoints for interaction logs, RAGAS evaluation, and human review."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.services.interaction_logger import InteractionLogger
from database.session import get_session

log = structlog.get_logger(__name__)
router = APIRouter()


def _require_admin(user=Depends(get_current_user)):
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# GET /conversations — grouped interactions by conversation_id
# ---------------------------------------------------------------------------
@router.get("/conversations")
async def list_conversations(
    user_id: str | None = Query(None),
    evaluation_status: str | None = Query(None),
    intent: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List conversations (grouped interactions) for admin review."""
    logger = InteractionLogger(session)
    items, total = await logger.get_conversations(
        user_id=user_id,
        evaluation_status=evaluation_status,
        intent=intent,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# GET /conversations/{conversation_id} — full conversation detail with all turns
# ---------------------------------------------------------------------------
@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get full conversation detail including all turns with retrieved context."""
    logger = InteractionLogger(session)
    conversation = await logger.get_conversation_detail(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


# ---------------------------------------------------------------------------
# POST /conversations/{conversation_id}/evaluate — evaluate all turns in conversation
# ---------------------------------------------------------------------------
@router.post("/conversations/{conversation_id}/evaluate")
async def evaluate_conversation(
    conversation_id: str,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Trigger RAGAS evaluation for all turns in a conversation with context."""
    logger = InteractionLogger(session)
    conversation = await logger.get_conversation_detail(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    turns = conversation.get("turns", [])
    evaluated_count = 0
    for turn in turns:
        if turn.get("evaluation_status") in ("COMPLETED", "RUNNING"):
            continue
        ctx_data = turn.get("retrieved_contexts") or {}
        contexts = ctx_data.get("contexts", []) if isinstance(ctx_data, dict) else []
        if not contexts:
            continue

        # Build conversation history for this turn (previous turns only)
        history_for_turn = []
        for prev_turn in turns:
            if prev_turn["turn_index"] >= turn["turn_index"]:
                break
            history_for_turn.append({
                "question": prev_turn["question"],
                "answer": prev_turn["answer"],
            })

        await logger.set_evaluation_status(turn["trace_id"], "RUNNING")
        asyncio.create_task(
            _run_conversation_aware_evaluation(
                turn["trace_id"], turn, contexts, history_for_turn, logger
            )
        )
        evaluated_count += 1

    return {
        "status": "RUNNING",
        "conversation_id": conversation_id,
        "turns_evaluated": evaluated_count,
    }


# ---------------------------------------------------------------------------
# POST /conversations/{conversation_id}/review — review entire conversation
# ---------------------------------------------------------------------------
@router.post("/conversations/{conversation_id}/review")
async def review_conversation(
    conversation_id: str,
    review: str = Query(..., description="accepted|needs_review|incorrect|hallucination|insufficient_evidence"),
    note: str | None = Query(None),
    turn_reviews: str | None = Query(None, description='JSON: {"turn_index": "accepted", ...}'),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Set human review for a conversation. Optionally override per-turn reviews."""
    import json as _json

    valid_reviews = {"accepted", "needs_review", "incorrect", "hallucination", "insufficient_evidence"}
    if review not in valid_reviews:
        raise HTTPException(status_code=400, detail=f"Invalid review. Must be one of: {valid_reviews}")

    logger = InteractionLogger(session)
    conversation = await logger.get_conversation_detail(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Parse per-turn overrides
    per_turn = {}
    if turn_reviews:
        try:
            per_turn = _json.loads(turn_reviews)
        except Exception:
            pass

    turns = conversation.get("turns", [])
    for turn in turns:
        turn_review = per_turn.get(str(turn["turn_index"]), review)
        if turn_review not in valid_reviews:
            turn_review = review
        await logger.set_human_review(turn["trace_id"], turn_review, note)

    return {"status": "ok", "conversation_id": conversation_id, "human_review": review}


# ---------------------------------------------------------------------------
# GET /interactions — paginated list with filters
# ---------------------------------------------------------------------------
@router.get("/interactions")
async def list_interactions(
    user_id: str | None = Query(None),
    evaluation_status: str | None = Query(None),
    intent: str | None = Query(None),
    min_faithfulness: float | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List chat interactions for admin review with filtering, sorting, pagination."""
    logger = InteractionLogger(session)
    items, total = await logger.get_interactions(
        user_id=user_id,
        evaluation_status=evaluation_status,
        intent=intent,
        min_faithfulness=min_faithfulness,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# GET /interactions/{trace_id} — full detail
# ---------------------------------------------------------------------------
@router.get("/interactions/{trace_id}")
async def get_interaction(
    trace_id: str,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get a single interaction with full detail including RAGAS scores and context."""
    logger = InteractionLogger(session)
    interaction = await logger.get_interaction(trace_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


# ---------------------------------------------------------------------------
# POST /interactions/{trace_id}/evaluate — trigger/retry RAGAS evaluation
# ---------------------------------------------------------------------------
@router.post("/interactions/{trace_id}/evaluate")
async def trigger_evaluation(
    trace_id: str,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Trigger or retry RAGAS evaluation for a single interaction."""
    logger = InteractionLogger(session)
    interaction = await logger.get_interaction(trace_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")

    # Extract contexts from stored snapshot
    ctx_data = interaction.get("retrieved_contexts") or {}
    contexts = ctx_data.get("contexts", []) if isinstance(ctx_data, dict) else []

    if not contexts:
        raise HTTPException(
            status_code=400,
            detail="No retrieved contexts available for this interaction",
        )

    # Mark as running
    await logger.set_evaluation_status(trace_id, "RUNNING")

    # Run evaluation in background
    asyncio.create_task(_run_evaluation_task(trace_id, interaction, contexts, logger))

    return {"status": "RUNNING", "trace_id": trace_id}


# ---------------------------------------------------------------------------
# POST /interactions/{trace_id}/review — set human review
# ---------------------------------------------------------------------------
@router.post("/interactions/{trace_id}/review")
async def set_human_review(
    trace_id: str,
    review: str = Query(..., description="accepted|needs_review|incorrect|hallucination|insufficient_evidence"),
    note: str | None = Query(None),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Set human review status for an interaction."""
    valid_reviews = {"accepted", "needs_review", "incorrect", "hallucination", "insufficient_evidence"}
    if review not in valid_reviews:
        raise HTTPException(status_code=400, detail=f"Invalid review. Must be one of: {valid_reviews}")

    logger = InteractionLogger(session)
    await logger.set_human_review(trace_id, review, note)
    return {"status": "ok", "trace_id": trace_id, "human_review": review}


# ---------------------------------------------------------------------------
# GET /ragas/summary — aggregate statistics
# ---------------------------------------------------------------------------
@router.get("/ragas/summary")
async def ragas_summary(
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregate RAGAS evaluation statistics for the admin dashboard."""
    logger = InteractionLogger(session)
    return await logger.get_summary()


# ---------------------------------------------------------------------------
# POST /interactions/{trace_id}/diagnose — compute root-cause diagnostics
# ---------------------------------------------------------------------------
@router.post("/interactions/{trace_id}/diagnose")
async def diagnose_interaction(
    trace_id: str,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Compute root-cause diagnostics for an existing interaction.

    Uses the stored interaction data to classify WHERE/WHY the query may have failed.
    System metrics are computed from available stored data.  Metrics that require
    reference/ground-truth data are marked NOT_EVALUATED (not 0).
    """
    from evaluation.diagnostics import classify_from_ragas
    from evaluation.models import MetricStatus, PipelineTrace, SystemMetrics

    logger = InteractionLogger(session)
    interaction = await logger.get_interaction(trace_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")

    # Build a basic pipeline trace from stored data
    trace = PipelineTrace(
        trace_id=trace_id,
        question=interaction.get("question", ""),
        intent_detected=interaction.get("intent", ""),
        entity_resolved_urn=interaction.get("entity_resolved_urn"),
        entity_resolved_name=interaction.get("entity_resolved_name"),
        entity_candidates=[interaction.get("entity_resolved_urn")] if interaction.get("entity_resolved_urn") else [],
        retrieval_results_count=interaction.get("result_count", 0),
        answer_text=interaction.get("answer", "")[:500],
        confidence=interaction.get("confidence", "low"),
    )

    # Build system metrics from available stored data
    # For existing interactions WITHOUT reference data, most metrics are NOT_EVALUATED
    system_metrics = SystemMetrics(
        processing_time_ms=interaction.get("processing_time_ms") or 0,
    )

    # Metrics we CAN compute from stored data:
    result_count = interaction.get("result_count", 0)
    answer_text = interaction.get("answer", "")
    confidence = interaction.get("confidence", "low")

    # retrieval_hit: can infer from result_count
    if result_count is not None:
        has_results = result_count > 0
        system_metrics.set_metric(
            "retrieval_hit", has_results, MetricStatus.COMPLETED,
            None if has_results else "No retrieval results stored",
        )
    else:
        system_metrics.set_metric("retrieval_hit", None, MetricStatus.NOT_EVALUATED,
                                  "No result_count in stored interaction")

    # no_answer_accuracy: can partially infer from answer + confidence
    refusal_phrases = [
        "khong tim thay", "khong co", "khong the", "xin loi",
        "khong biet", "khong du", "i don't know", "cannot",
        "not enough", "not found", "no information",
    ]
    is_refusal = any(p in answer_text.lower() for p in refusal_phrases) or confidence == "low"
    has_answer = bool(answer_text.strip())
    if has_answer and not is_refusal:
        system_metrics.set_metric("no_answer_accuracy", 1.0, MetricStatus.COMPLETED,
                                  "Answer provided with acceptable confidence")
    elif not has_answer:
        system_metrics.set_metric("no_answer_accuracy", 0.0, MetricStatus.COMPLETED,
                                  "Empty answer stored")
    else:
        system_metrics.set_metric("no_answer_accuracy", None, MetricStatus.NOT_EVALUATED,
                                  "Cannot determine expected behavior without reference")

    # All other metrics: NOT_EVALUATED (need reference data)
    for name in ["entity_accuracy", "entity_precision", "entity_recall",
                 "retrieval_top_k_recall", "context_coverage",
                 "citation_correctness", "citation_completeness",
                 "intent_accuracy", "metadata_field_accuracy"]:
        if system_metrics.get_metric_status(name) == MetricStatus.NOT_EVALUATED:
            system_metrics.set_metric(name, None, MetricStatus.NOT_EVALUATED,
                                      "No reference data available for existing interaction")

    # Use RAGAS-based classification if we have scores
    faithfulness = interaction.get("faithfulness")
    answer_relevancy = interaction.get("answer_relevancy")
    context_precision = interaction.get("context_precision")
    context_recall = interaction.get("context_recall")
    has_reference = False  # We don't have reference data for existing interactions

    root_cause = classify_from_ragas(
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_precision=context_precision,
        context_recall=context_recall,
        has_reference=has_reference,
    )

    return {
        "trace_id": trace_id,
        "root_cause": root_cause.to_dict(),
        "system_metrics": system_metrics.to_dict(),
        "pipeline_trace": trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Background evaluation task
# ---------------------------------------------------------------------------
async def _run_evaluation_task(
    trace_id: str,
    interaction: dict,
    contexts: list[str],
    logger: InteractionLogger,
) -> None:
    """Run RAGAS evaluation asynchronously (fire-and-forget)."""
    try:
        from evaluation.ragas_evaluator import evaluate_interaction

        result = await evaluate_interaction(
            question=interaction.get("question", ""),
            answer=interaction.get("answer", ""),
            retrieved_contexts=contexts,
        )

        await logger.update_ragas_scores(
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
        log.info("ragas_evaluation_completed", trace_id=trace_id)
    except Exception as exc:
        log.warning("ragas_evaluation_task_failed", trace_id=trace_id, error=str(exc))
        await logger.set_evaluation_status(trace_id, "FAILED", error=str(exc))


async def _run_conversation_aware_evaluation(
    trace_id: str,
    turn: dict,
    contexts: list[str],
    history: list[dict],
    logger: InteractionLogger,
) -> None:
    """Run RAGAS evaluation with conversation history context."""
    try:
        from evaluation.ragas_evaluator import evaluate_conversation_turn

        result = await evaluate_conversation_turn(
            question=turn.get("question", ""),
            answer=turn.get("answer", ""),
            retrieved_contexts=contexts,
            conversation_history=history,
        )

        await logger.update_ragas_scores(
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
        log.info("ragas_conversation_eval_completed", trace_id=trace_id)
    except Exception as exc:
        log.warning("ragas_conversation_eval_failed", trace_id=trace_id, error=str(exc))
        await logger.set_evaluation_status(trace_id, "FAILED", error=str(exc))
