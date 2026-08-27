"""Admin response log -- records every chat interaction for audit and RAGAS evaluation."""

from __future__ import annotations

import datetime as _dt
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataclasses import dataclass, field
from database.models import InteractionLog

log = structlog.get_logger(__name__)


@dataclass
class HallucinationAuditRecord:
    """Ghi nhận mọi potential hallucination event để review sau."""

    trace_id: str
    timestamp: str
    query: str
    anchor_mentions: list[str] = field(default_factory=list)
    resolved_entities: list[str] = field(default_factory=list)
    context_entities: list[str] = field(default_factory=list)
    answer_entities: list[str] = field(default_factory=list)
    has_entity_drift: bool = False
    has_entity_miss: bool = False
    has_ghost_entity: bool = False
    has_contradiction: bool = False
    has_confabulation: bool = False
    correction_applied: bool = False
    correction_type: str = ""
    fidelity_score: float = 1.0
    anchor_coverage: float = 1.0


class InteractionLogger:
    """Logs chat interactions to the database for admin review and RAGAS evaluation."""


    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entries: dict[str, InteractionLog] = {}

    async def log_request(
        self,
        trace_id: str,
        question: str,
        user_id: str,
        conversation_id: str,
        selected_action: str | None = None,
        model: str | None = None,
    ) -> None:
        """Log the incoming request before processing.

        Uses a deferred write: the entry is added to the session identity map
        but NOT flushed immediately to avoid triggering autoflush conflicts
        with concurrent ORM operations.  The session will persist the entry
        when it commits naturally at the end of the request lifecycle.
        """
        try:
            entry = InteractionLog(
                trace_id=trace_id,
                user_id=user_id,
                conversation_id=conversation_id,
                question=question[:4000],
                selected_action=selected_action,
                model=model,
                intent="pending",
                answer="",
            )
            self._session.add(entry)
            self._entries[trace_id] = entry
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_request_failed", trace_id=trace_id)

    async def log_response(
        self,
        trace_id: str,
        answer: str,
        intent: str,
        confidence: str | None = None,
        ambiguous: bool = False,
        insufficient_context: bool = False,
        result_count: int = 0,
        top_score: float | None = None,
        citation_count: int = 0,
        processing_time_ms: int | None = None,
        message_intent: str | None = None,
        routing_decision: str | None = None,
        chosen_tool: str | None = None,
        entity_hint: str | None = None,
        entity_resolved_name: str | None = None,
        entity_resolved_urn: str | None = None,
        resolution_state: str | None = None,
        retrieved_contexts: list[str] | None = None,
    ) -> None:
        """Update the interaction log with the response details."""
        try:
            entry = self._entries.get(trace_id)
            if entry is None:
                # Fallback: query from DB (for cases where entry was created elsewhere)
                result = await self._session.execute(
                    select(InteractionLog).where(InteractionLog.trace_id == trace_id)
                )
                entry = result.scalar_one_or_none()
                if entry is None:
                    log.warning("interaction_log_not_found", trace_id=trace_id)
                    return

            entry.answer = answer[:8000]
            entry.intent = intent
            entry.confidence = confidence
            entry.ambiguous = ambiguous
            entry.insufficient_context = insufficient_context
            entry.result_count = result_count
            entry.top_score = top_score
            entry.citation_count = citation_count
            entry.processing_time_ms = processing_time_ms
            entry.message_intent = message_intent
            entry.routing_decision = routing_decision
            entry.chosen_tool = chosen_tool
            entry.entity_hint = entity_hint
            entry.entity_resolved_name = entity_resolved_name
            entry.entity_resolved_urn = entity_resolved_urn
            entry.resolution_state = resolution_state

            # Persist retrieved context snapshot for RAGAS evaluation
            if retrieved_contexts is not None:
                ctx_strs = []
                for c in retrieved_contexts:
                    if isinstance(c, str):
                        ctx_strs.append(c)
                    elif hasattr(c, "content"):
                        ctx_strs.append(c.content)
                    else:
                        ctx_strs.append(str(c))
                entry.retrieved_contexts = {"contexts": ctx_strs[:10]}

            # Set evaluation as pending if we have context to evaluate
            if retrieved_contexts and entry.evaluation_status == "NOT_EVALUATED":
                entry.evaluation_status = "PENDING"

            # No explicit flush — let the session commit naturally at request end
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_response_failed", trace_id=trace_id)

    async def update_ragas_scores(
        self,
        trace_id: str,
        faithfulness: float | None = None,
        faithfulness_status: str | None = None,
        answer_relevancy: float | None = None,
        answer_relevancy_status: str | None = None,
        context_precision: float | None = None,
        context_precision_status: str | None = None,
        context_recall: float | None = None,
        context_recall_status: str | None = None,
        evaluation_model: str | None = None,
        evaluation_error: str | None = None,
    ) -> None:
        """Update RAGAS scores (computed async after response)."""
        try:
            entry = self._entries.get(trace_id)
            if entry is None:
                result = await self._session.execute(
                    select(InteractionLog).where(InteractionLog.trace_id == trace_id)
                )
                entry = result.scalar_one_or_none()
                if entry is None:
                    return

            if faithfulness is not None:
                entry.faithfulness = faithfulness
            if faithfulness_status is not None:
                entry.faithfulness_status = faithfulness_status or "COMPLETED"
            if answer_relevancy is not None:
                entry.answer_relevancy = answer_relevancy
            if answer_relevancy_status is not None:
                entry.answer_relevancy_status = answer_relevancy_status or "COMPLETED"
            if context_precision is not None:
                entry.context_precision = context_precision
            if context_precision_status is not None:
                entry.context_precision_status = context_precision_status or "COMPLETED"
            if context_recall is not None:
                entry.context_recall = context_recall
            if context_recall_status is not None:
                entry.context_recall_status = context_recall_status or "COMPLETED"

            if evaluation_model:
                entry.evaluation_model = evaluation_model
            if evaluation_error:
                entry.evaluation_error = evaluation_error

            # Determine overall evaluation status
            statuses = [
                entry.faithfulness_status,
                entry.answer_relevancy_status,
                entry.context_precision_status,
                entry.context_recall_status,
            ]
            if any(s == "FAILED" for s in statuses if s):
                entry.evaluation_status = "FAILED"
            elif all(s in ("COMPLETED", "NOT_EVALUATED") for s in statuses if s):
                entry.evaluation_status = "COMPLETED"

            entry.evaluated_at = _dt.datetime.now(_dt.UTC)
            # Flush only if entry was loaded from DB (not in local cache)
            if trace_id not in self._entries:
                await self._session.flush()
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_ragas_failed", trace_id=trace_id)

    async def set_evaluation_status(
        self,
        trace_id: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update the evaluation status (PENDING/RUNNING/COMPLETED/FAILED)."""
        try:
            entry = self._entries.get(trace_id)
            if entry is None:
                result = await self._session.execute(
                    select(InteractionLog).where(InteractionLog.trace_id == trace_id)
                )
                entry = result.scalar_one_or_none()
                if entry is None:
                    return
            entry.evaluation_status = status
            if error:
                entry.evaluation_error = error
            if trace_id not in self._entries:
                await self._session.flush()
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_eval_status_failed", trace_id=trace_id)

    async def set_human_review(
        self,
        trace_id: str,
        review: str,
        note: str | None = None,
    ) -> None:
        """Set human review status for an interaction."""
        try:
            entry = self._entries.get(trace_id)
            if entry is None:
                result = await self._session.execute(
                    select(InteractionLog).where(InteractionLog.trace_id == trace_id)
                )
                entry = result.scalar_one_or_none()
                if entry is None:
                    return
            entry.human_review = review
            entry.human_review_note = note
            entry.human_reviewed_at = _dt.datetime.now(_dt.UTC)
            if trace_id not in self._entries:
                await self._session.flush()
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_human_review_failed", trace_id=trace_id)

    async def get_interactions(
        self,
        user_id: str | None = None,
        evaluation_status: str | None = None,
        intent: str | None = None,
        min_faithfulness: float | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query interactions for admin UI. Returns (items, total_count)."""
        try:
            stmt = select(InteractionLog)
            count_stmt = select(func.count(InteractionLog.id))

            if user_id:
                stmt = stmt.where(InteractionLog.user_id == user_id)
                count_stmt = count_stmt.where(InteractionLog.user_id == user_id)
            if evaluation_status:
                stmt = stmt.where(InteractionLog.evaluation_status == evaluation_status)
                count_stmt = count_stmt.where(InteractionLog.evaluation_status == evaluation_status)
            if intent:
                stmt = stmt.where(InteractionLog.intent == intent)
                count_stmt = count_stmt.where(InteractionLog.intent == intent)
            if min_faithfulness is not None:
                stmt = stmt.where(InteractionLog.faithfulness >= min_faithfulness)
                count_stmt = count_stmt.where(InteractionLog.faithfulness >= min_faithfulness)
            if search:
                search_pattern = f"%{search}%"
                stmt = stmt.where(
                    InteractionLog.question.ilike(search_pattern)
                    | InteractionLog.answer.ilike(search_pattern)
                )
                count_stmt = count_stmt.where(
                    InteractionLog.question.ilike(search_pattern)
                    | InteractionLog.answer.ilike(search_pattern)
                )

            # Sorting
            sort_col = getattr(InteractionLog, sort_by, InteractionLog.created_at)
            if sort_order == "asc":
                stmt = stmt.order_by(sort_col.asc())
            else:
                stmt = stmt.order_by(sort_col.desc())

            # Total count
            total_result = await self._session.execute(count_stmt)
            total = total_result.scalar() or 0

            # Paginated results
            stmt = stmt.limit(limit).offset(offset)
            result = await self._session.execute(stmt)
            entries = result.scalars().all()

            return [
                {
                    "trace_id": e.trace_id,
                    "user_id": e.user_id,
                    "conversation_id": e.conversation_id,
                    "question": e.question,
                    "answer": e.answer[:500],
                    "intent": e.intent,
                    "confidence": e.confidence,
                    "ambiguous": e.ambiguous,
                    "result_count": e.result_count,
                    "top_score": e.top_score,
                    "citation_count": e.citation_count,
                    "processing_time_ms": e.processing_time_ms,
                    "evaluation_status": e.evaluation_status,
                    "faithfulness": e.faithfulness,
                    "faithfulness_status": e.faithfulness_status,
                    "answer_relevancy": e.answer_relevancy,
                    "answer_relevancy_status": e.answer_relevancy_status,
                    "context_precision": e.context_precision,
                    "context_precision_status": e.context_precision_status,
                    "context_recall": e.context_recall,
                    "context_recall_status": e.context_recall_status,
                    "evaluation_model": e.evaluation_model,
                    "human_review": e.human_review,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ], total
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_query_failed")
            return [], 0

    async def get_interaction(self, trace_id: str) -> dict[str, Any] | None:
        """Get a single interaction by trace_id."""
        try:
            result = await self._session.execute(
                select(InteractionLog).where(InteractionLog.trace_id == trace_id)
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                return None

            return {
                "id": entry.id,
                "trace_id": entry.trace_id,
                "user_id": entry.user_id,
                "conversation_id": entry.conversation_id,
                "question": entry.question,
                "answer": entry.answer,
                "intent": entry.intent,
                "message_intent": entry.message_intent,
                "routing_decision": entry.routing_decision,
                "confidence": entry.confidence,
                "chosen_tool": entry.chosen_tool,
                "entity_hint": entry.entity_hint,
                "entity_resolved_name": entry.entity_resolved_name,
                "entity_resolved_urn": entry.entity_resolved_urn,
                "resolution_state": entry.resolution_state,
                "ambiguous": entry.ambiguous,
                "insufficient_context": entry.insufficient_context,
                "result_count": entry.result_count,
                "top_score": entry.top_score,
                "citation_count": entry.citation_count,
                "processing_time_ms": entry.processing_time_ms,
                "retrieved_contexts": entry.retrieved_contexts,
                "evaluation_status": entry.evaluation_status,
                "evaluation_error": entry.evaluation_error,
                "evaluation_model": entry.evaluation_model,
                "evaluated_at": entry.evaluated_at.isoformat() if entry.evaluated_at else None,
                "faithfulness": entry.faithfulness,
                "faithfulness_status": entry.faithfulness_status,
                "answer_relevancy": entry.answer_relevancy,
                "answer_relevancy_status": entry.answer_relevancy_status,
                "context_precision": entry.context_precision,
                "context_precision_status": entry.context_precision_status,
                "context_recall": entry.context_recall,
                "context_recall_status": entry.context_recall_status,
                "human_review": entry.human_review,
                "human_review_note": entry.human_review_note,
                "human_reviewed_at": entry.human_reviewed_at.isoformat() if entry.human_reviewed_at else None,
                "selected_action": entry.selected_action,
                "model": entry.model,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_get_failed", trace_id=trace_id)
            return None

    async def get_conversations(
        self,
        user_id: str | None = None,
        evaluation_status: str | None = None,
        intent: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Group interactions by conversation_id for conversation-level review.

        Returns (conversations, total_conversation_count).
        Each conversation contains its turns ordered by created_at.
        """
        try:
            from sqlalchemy import distinct

            # Base query for conversation IDs
            base_stmt = select(
                InteractionLog.conversation_id,
                func.count(InteractionLog.id).label("turn_count"),
                func.min(InteractionLog.created_at).label("started_at"),
                func.max(InteractionLog.created_at).label("completed_at"),
                func.avg(InteractionLog.faithfulness).label("avg_faithfulness"),
                func.avg(InteractionLog.answer_relevancy).label("avg_answer_relevancy"),
                func.avg(InteractionLog.context_precision).label("avg_context_precision"),
                func.avg(InteractionLog.context_recall).label("avg_context_recall"),
            )

            count_stmt = select(func.count(distinct(InteractionLog.conversation_id)))

            # Apply filters
            if user_id:
                base_stmt = base_stmt.where(InteractionLog.user_id == user_id)
                count_stmt = count_stmt.where(InteractionLog.user_id == user_id)
            if evaluation_status:
                base_stmt = base_stmt.where(InteractionLog.evaluation_status == evaluation_status)
                count_stmt = count_stmt.where(InteractionLog.evaluation_status == evaluation_status)
            if intent:
                base_stmt = base_stmt.where(InteractionLog.intent == intent)
                count_stmt = count_stmt.where(InteractionLog.intent == intent)
            if search:
                search_pattern = f"%{search}%"
                base_stmt = base_stmt.where(
                    InteractionLog.question.ilike(search_pattern)
                    | InteractionLog.answer.ilike(search_pattern)
                )
                count_stmt = count_stmt.where(
                    InteractionLog.question.ilike(search_pattern)
                    | InteractionLog.answer.ilike(search_pattern)
                )

            # Group by conversation_id
            base_stmt = base_stmt.group_by(InteractionLog.conversation_id)

            # Sorting
            if sort_by == "turn_count":
                sort_col = func.count(InteractionLog.id)
            elif sort_by == "started_at":
                sort_col = func.min(InteractionLog.created_at)
            else:
                sort_col = func.max(InteractionLog.created_at)

            if sort_order == "asc":
                base_stmt = base_stmt.order_by(sort_col.asc())
            else:
                base_stmt = base_stmt.order_by(sort_col.desc())

            # Total conversation count
            total_result = await self._session.execute(count_stmt)
            total = total_result.scalar() or 0

            # Paginated results
            base_stmt = base_stmt.limit(limit).offset(offset)
            result = await self._session.execute(base_stmt)
            conv_rows = result.all()

            conversations = []
            for row in conv_rows:
                conv_id = row.conversation_id

                # Fetch all turns for this conversation, ordered by created_at
                turns_stmt = (
                    select(InteractionLog)
                    .where(InteractionLog.conversation_id == conv_id)
                    .order_by(InteractionLog.created_at.asc())
                )
                turns_result = await self._session.execute(turns_stmt)
                turns = turns_result.scalars().all()

                # Determine conversation-level evaluation status
                turn_statuses = [t.evaluation_status for t in turns]
                if any(s == "FAILED" for s in turn_statuses):
                    conv_eval_status = "FAILED"
                elif all(s in ("COMPLETED", "NOT_EVALUATED") for s in turn_statuses):
                    conv_eval_status = "COMPLETED"
                elif any(s == "RUNNING" for s in turn_statuses):
                    conv_eval_status = "RUNNING"
                elif any(s == "PENDING" for s in turn_statuses):
                    conv_eval_status = "PENDING"
                else:
                    conv_eval_status = "NOT_EVALUATED"

                # Determine conversation-level human review
                turn_reviews = [t.human_review for t in turns if t.human_review]
                if any(r in ("incorrect", "hallucination") for r in turn_reviews):
                    conv_review = "needs_review"
                elif all(r == "accepted" for r in turn_reviews) and turn_reviews:
                    conv_review = "accepted"
                elif turn_reviews:
                    conv_review = "needs_review"
                else:
                    conv_review = None

                # Count failed turns
                failed_turns = sum(
                    1 for t in turns
                    if t.faithfulness is not None and t.faithfulness < 0.7
                )

                # Get user_id from first turn
                user_id_val = turns[0].user_id if turns else None

                # Build turn summaries
                turn_summaries = []
                for idx, t in enumerate(turns):
                    turn_summaries.append({
                        "turn_index": idx,
                        "trace_id": t.trace_id,
                        "question": t.question,
                        "answer": t.answer[:500],
                        "intent": t.intent,
                        "confidence": t.confidence,
                        "entity_resolved_name": t.entity_resolved_name,
                        "entity_resolved_urn": t.entity_resolved_urn,
                        "chosen_tool": t.chosen_tool,
                        "result_count": t.result_count,
                        "citation_count": t.citation_count,
                        "processing_time_ms": t.processing_time_ms,
                        "evaluation_status": t.evaluation_status,
                        "faithfulness": t.faithfulness,
                        "answer_relevancy": t.answer_relevancy,
                        "context_precision": t.context_precision,
                        "context_recall": t.context_recall,
                        "human_review": t.human_review,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                    })

                conversations.append({
                    "conversation_id": conv_id,
                    "user_id": user_id_val,
                    "turn_count": row.turn_count,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "avg_faithfulness": round(row.avg_faithfulness, 4) if row.avg_faithfulness else None,
                    "avg_answer_relevancy": round(row.avg_answer_relevancy, 4) if row.avg_answer_relevancy else None,
                    "avg_context_precision": round(row.avg_context_precision, 4) if row.avg_context_precision else None,
                    "avg_context_recall": round(row.avg_context_recall, 4) if row.avg_context_recall else None,
                    "evaluation_status": conv_eval_status,
                    "human_review": conv_review,
                    "failed_turns": failed_turns,
                    "turns": turn_summaries,
                })

            return conversations, total
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_conversations_failed")
            return [], 0

    async def get_conversation_detail(self, conversation_id: str) -> dict[str, Any] | None:
        """Get full detail for a single conversation including all turns with context."""
        try:
            # Fetch all turns for this conversation
            stmt = (
                select(InteractionLog)
                .where(InteractionLog.conversation_id == conversation_id)
                .order_by(InteractionLog.created_at.asc())
            )
            result = await self._session.execute(stmt)
            turns = result.scalars().all()

            if not turns:
                return None

            turn_details = []
            for idx, t in enumerate(turns):
                turn_details.append({
                    "turn_index": idx,
                    "id": t.id,
                    "trace_id": t.trace_id,
                    "user_id": t.user_id,
                    "question": t.question,
                    "answer": t.answer,
                    "intent": t.intent,
                    "message_intent": t.message_intent,
                    "routing_decision": t.routing_decision,
                    "confidence": t.confidence,
                    "chosen_tool": t.chosen_tool,
                    "entity_hint": t.entity_hint,
                    "entity_resolved_name": t.entity_resolved_name,
                    "entity_resolved_urn": t.entity_resolved_urn,
                    "resolution_state": t.resolution_state,
                    "ambiguous": t.ambiguous,
                    "insufficient_context": t.insufficient_context,
                    "result_count": t.result_count,
                    "top_score": t.top_score,
                    "citation_count": t.citation_count,
                    "processing_time_ms": t.processing_time_ms,
                    "retrieved_contexts": t.retrieved_contexts,
                    "evaluation_status": t.evaluation_status,
                    "evaluation_error": t.evaluation_error,
                    "evaluation_model": t.evaluation_model,
                    "evaluated_at": t.evaluated_at.isoformat() if t.evaluated_at else None,
                    "faithfulness": t.faithfulness,
                    "faithfulness_status": t.faithfulness_status,
                    "answer_relevancy": t.answer_relevancy,
                    "answer_relevancy_status": t.answer_relevancy_status,
                    "context_precision": t.context_precision,
                    "context_precision_status": t.context_precision_status,
                    "context_recall": t.context_recall,
                    "context_recall_status": t.context_recall_status,
                    "human_review": t.human_review,
                    "human_review_note": t.human_review_note,
                    "human_reviewed_at": t.human_reviewed_at.isoformat() if t.human_reviewed_at else None,
                    "selected_action": t.selected_action,
                    "model": t.model,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                })

            # Compute conversation-level aggregates
            faith_scores = [t.faithfulness for t in turns if t.faithfulness is not None]
            ar_scores = [t.answer_relevancy for t in turns if t.answer_relevancy is not None]
            cp_scores = [t.context_precision for t in turns if t.context_precision is not None]
            cr_scores = [t.context_recall for t in turns if t.context_recall is not None]

            turn_statuses = [t.evaluation_status for t in turns]
            if any(s == "FAILED" for s in turn_statuses):
                conv_eval_status = "FAILED"
            elif all(s in ("COMPLETED", "NOT_EVALUATED") for s in turn_statuses):
                conv_eval_status = "COMPLETED"
            elif any(s == "RUNNING" for s in turn_statuses):
                conv_eval_status = "RUNNING"
            elif any(s == "PENDING" for s in turn_statuses):
                conv_eval_status = "PENDING"
            else:
                conv_eval_status = "NOT_EVALUATED"

            turn_reviews = [t.human_review for t in turns if t.human_review]
            if any(r in ("incorrect", "hallucination") for r in turn_reviews):
                conv_review = "needs_review"
            elif all(r == "accepted" for r in turn_reviews) and turn_reviews:
                conv_review = "accepted"
            elif turn_reviews:
                conv_review = "needs_review"
            else:
                conv_review = None

            failed_turns = sum(
                1 for t in turns
                if t.faithfulness is not None and t.faithfulness < 0.7
            )

            return {
                "conversation_id": conversation_id,
                "user_id": turns[0].user_id,
                "turn_count": len(turns),
                "started_at": turns[0].created_at.isoformat() if turns[0].created_at else None,
                "completed_at": turns[-1].created_at.isoformat() if turns[-1].created_at else None,
                "avg_faithfulness": round(sum(faith_scores) / len(faith_scores), 4) if faith_scores else None,
                "avg_answer_relevancy": round(sum(ar_scores) / len(ar_scores), 4) if ar_scores else None,
                "avg_context_precision": round(sum(cp_scores) / len(cp_scores), 4) if cp_scores else None,
                "avg_context_recall": round(sum(cr_scores) / len(cr_scores), 4) if cr_scores else None,
                "evaluation_status": conv_eval_status,
                "human_review": conv_review,
                "failed_turns": failed_turns,
                "turns": turn_details,
            }
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_conversation_detail_failed", conversation_id=conversation_id)
            return None

    async def get_summary(self) -> dict[str, Any]:
        """Get aggregate statistics for the admin dashboard."""
        try:
            base = select(func.count(InteractionLog.id))

            total_r = await self._session.execute(base)
            total = total_r.scalar() or 0

            evaluated_r = await self._session.execute(
                base.where(InteractionLog.evaluation_status == "COMPLETED")
            )
            evaluated = evaluated_r.scalar() or 0

            pending_r = await self._session.execute(
                base.where(InteractionLog.evaluation_status == "PENDING")
            )
            pending = pending_r.scalar() or 0

            failed_r = await self._session.execute(
                base.where(InteractionLog.evaluation_status == "FAILED")
            )
            failed = failed_r.scalar() or 0

            not_eval_r = await self._session.execute(
                base.where(InteractionLog.evaluation_status == "NOT_EVALUATED")
            )
            not_evaluated = not_eval_r.scalar() or 0

            avg_faith_r = await self._session.execute(
                select(func.avg(InteractionLog.faithfulness)).where(
                    InteractionLog.faithfulness.isnot(None)
                )
            )
            avg_faithfulness = avg_faith_r.scalar()

            avg_ar_r = await self._session.execute(
                select(func.avg(InteractionLog.answer_relevancy)).where(
                    InteractionLog.answer_relevancy.isnot(None)
                )
            )
            avg_answer_relevancy = avg_ar_r.scalar()

            avg_cp_r = await self._session.execute(
                select(func.avg(InteractionLog.context_precision)).where(
                    InteractionLog.context_precision.isnot(None)
                )
            )
            avg_context_precision = avg_cp_r.scalar()

            avg_cr_r = await self._session.execute(
                select(func.avg(InteractionLog.context_recall)).where(
                    InteractionLog.context_recall.isnot(None)
                )
            )
            avg_context_recall = avg_cr_r.scalar()

            low_quality_r = await self._session.execute(
                base.where(
                    InteractionLog.faithfulness.isnot(None),
                    InteractionLog.faithfulness < 0.7,
                )
            )
            low_quality_count = low_quality_r.scalar() or 0

            return {
                "total": total,
                "evaluated": evaluated,
                "pending": pending,
                "failed": failed,
                "not_evaluated": not_evaluated,
                "avg_faithfulness": round(avg_faithfulness, 4) if avg_faithfulness else None,
                "avg_answer_relevancy": round(avg_answer_relevancy, 4) if avg_answer_relevancy else None,
                "avg_context_precision": round(avg_context_precision, 4) if avg_context_precision else None,
                "avg_context_recall": round(avg_context_recall, 4) if avg_context_recall else None,
                "low_quality_count": low_quality_count,
            }
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_summary_failed")
            return {}
