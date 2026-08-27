"""Human quality review service — manages reviews, analytics, regression candidates, and review queue."""

from __future__ import annotations

import datetime as _dt
from typing import Any

import structlog
from sqlalchemy import func, select, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import HumanReview, InteractionLog, RegressionCandidate

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Error taxonomy — canonical set shared across backend and frontend
# ---------------------------------------------------------------------------
ERROR_CATEGORIES = [
    "WRONG_INTENT",
    "WRONG_ENTITY",
    "ENTITY_RESOLUTION_FAILURE",
    "WRONG_DATASET",
    "WRONG_SCHEMA",
    "WRONG_OWNER",
    "WRONG_DOMAIN",
    "WRONG_GLOSSARY_TERM",
    "WRONG_TERM_DEFINITION",
    "WRONG_LINEAGE",
    "WRONG_IMPACT_ANALYSIS",
    "WRONG_DATA_QUALITY",
    "WRONG_CITATION",
    "MISSING_CITATION",
    "RETRIEVAL_FAILURE",
    "CONTEXT_MISSING",
    "CONTEXT_IRRELEVANT",
    "CONTEXT_MEMORY_FAILURE",
    "MULTI_TURN_FAILURE",
    "HALLUCINATION",
    "PERMISSION_VIOLATION",
    "TOOL_FAILURE",
    "API_FAILURE",
    "GENERATION_FAILURE",
    "FORMATTING_FAILURE",
    "UI_RENDERING_FAILURE",
    "INSUFFICIENT_EVIDENCE",
    "OTHER",
]

FAILURE_STAGES = [
    "INTENT",
    "ENTITY_RESOLUTION",
    "RETRIEVAL",
    "TOOL",
    "CONTEXT",
    "GENERATION",
    "CITATION",
    "PERMISSION",
    "UI",
    "UNKNOWN",
]

OVERALL_LABELS = [
    "accepted",
    "needs_review",
    "incorrect",
    "hallucination",
    "insufficient_evidence",
]

LABEL_SEMANTICS = {
    "accepted": "Answer is correct, evidence is appropriate, no critical errors.",
    "needs_review": "Not enough certainty or needs additional reviewer inspection.",
    "incorrect": "Answer contains incorrect information or reasoning.",
    "hallucination": "Chatbot provided information not supported by DataHub/context/evidence.",
    "insufficient_evidence": "Answer may not be wrong but system lacks sufficient evidence/context to prove it.",
}

PERMISSION_CHOICES = ["PASS", "FAIL", "N/A"]

REVIEWER_CONFIDENCE_CHOICES = ["high", "medium", "low"]


class HumanReviewService:
    """Backend service for human quality reviews."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # CRUD: create review
    # -------------------------------------------------------------------
    async def create_review(
        self,
        interaction_id: int,
        trace_id: str,
        reviewer_id: str,
        reviewer_name: str,
        overall_label: str,
        *,
        correctness_score: float | None = None,
        relevance_score: float | None = None,
        groundedness_score: float | None = None,
        retrieval_quality: float | None = None,
        citation_quality: float | None = None,
        intent_correctness: bool | None = None,
        entity_resolution_correctness: bool | None = None,
        context_usage: bool | None = None,
        permission_correctness: str | None = None,
        error_categories: list[str] | None = None,
        failure_stage: str | None = None,
        reviewer_confidence: str | None = None,
        comment: str | None = None,
        suggested_fix: str | None = None,
    ) -> dict[str, Any]:
        """Create a new review and update consensus/disagreement flags."""
        if overall_label not in OVERALL_LABELS:
            raise ValueError(f"Invalid overall_label: {overall_label}")
        if error_categories:
            invalid = [c for c in error_categories if c not in ERROR_CATEGORIES]
            if invalid:
                raise ValueError(f"Invalid error categories: {invalid}")
        if failure_stage and failure_stage not in FAILURE_STAGES:
            raise ValueError(f"Invalid failure_stage: {failure_stage}")
        if permission_correctness and permission_correctness not in PERMISSION_CHOICES:
            raise ValueError(f"Invalid permission_correctness: {permission_correctness}")

        # Fetch interaction for snapshot
        ilog = await self._get_interaction_log(interaction_id)
        if ilog is None:
            raise ValueError(f"Interaction {interaction_id} not found")

        # Check for duplicate review by same reviewer
        existing = await self._find_existing_review(interaction_id, reviewer_id)
        if existing:
            raise ValueError(f"Review already exists by {reviewer_id}. Use update instead.")

        review = HumanReview(
            interaction_id=interaction_id,
            trace_id=trace_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            overall_label=overall_label,
            correctness_score=correctness_score,
            relevance_score=relevance_score,
            groundedness_score=groundedness_score,
            retrieval_quality=retrieval_quality,
            citation_quality=citation_quality,
            intent_correctness=intent_correctness,
            entity_resolution_correctness=entity_resolution_correctness,
            context_usage=context_usage,
            permission_correctness=permission_correctness,
            error_categories=error_categories or [],
            failure_stage=failure_stage,
            reviewer_confidence=reviewer_confidence,
            comment=comment,
            suggested_fix=suggested_fix,
            reviewed_question_snapshot=ilog.question or "",
            reviewed_answer_snapshot=ilog.answer or "",
            ragas_snapshot={
                "faithfulness": ilog.faithfulness,
                "answer_relevancy": ilog.answer_relevancy,
                "context_precision": ilog.context_precision,
                "context_recall": ilog.context_recall,
                "evaluation_status": ilog.evaluation_status,
            },
        )
        self._session.add(review)

        # Update interaction_logs.human_review to latest review label
        ilog_fresh = await self._get_interaction_log(interaction_id)
        if ilog_fresh:
            ilog_fresh.human_review = overall_label
            ilog_fresh.human_review_note = comment
            ilog_fresh.human_reviewed_at = _dt.datetime.now(_dt.UTC)

        await self._session.flush()

        # Update consensus/disagreement flags (after flush so queries work)
        await self._update_consensus_flags(interaction_id)

        return self._review_to_dict(review)

    # -------------------------------------------------------------------
    # CRUD: update review
    # -------------------------------------------------------------------
    async def update_review(
        self,
        review_id: int,
        reviewer_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update an existing review. Only the original reviewer can update."""
        review = await self._get_review(review_id)
        if review is None:
            raise ValueError(f"Review {review_id} not found")
        if review.reviewer_id != reviewer_id:
            raise PermissionError("Only the original reviewer can update their review")

        allowed_fields = {
            "overall_label", "correctness_score", "relevance_score", "groundedness_score",
            "retrieval_quality", "citation_quality", "intent_correctness",
            "entity_resolution_correctness", "context_usage", "permission_correctness",
            "error_categories", "failure_stage", "reviewer_confidence",
            "comment", "suggested_fix",
        }
        for key, val in kwargs.items():
            if key in allowed_fields and val is not None:
                setattr(review, key, val)

        if "overall_label" in kwargs and kwargs["overall_label"]:
            if kwargs["overall_label"] not in OVERALL_LABELS:
                raise ValueError(f"Invalid overall_label: {kwargs['overall_label']}")
        if "error_categories" in kwargs and kwargs["error_categories"]:
            invalid = [c for c in kwargs["error_categories"] if c not in ERROR_CATEGORIES]
            if invalid:
                raise ValueError(f"Invalid error categories: {invalid}")
        if "failure_stage" in kwargs and kwargs["failure_stage"]:
            if kwargs["failure_stage"] not in FAILURE_STAGES:
                raise ValueError(f"Invalid failure_stage: {kwargs['failure_stage']}")

        review.review_version += 1

        # Update interaction_logs.human_review
        ilog = await self._get_interaction_log(review.interaction_id)
        if ilog:
            ilog.human_review = review.overall_label
            ilog.human_review_note = review.comment
            ilog.human_reviewed_at = _dt.datetime.now(_dt.UTC)

        await self._session.flush()

        # Update consensus flags after flush
        await self._update_consensus_flags(review.interaction_id)

        return self._review_to_dict(review)

    # -------------------------------------------------------------------
    # CRUD: get reviews for interaction
    # -------------------------------------------------------------------
    async def get_reviews_for_interaction(self, interaction_id: int) -> list[dict[str, Any]]:
        """Get all reviews for an interaction (multiple reviewers)."""
        result = await self._session.execute(
            select(HumanReview)
            .where(HumanReview.interaction_id == interaction_id)
            .order_by(HumanReview.created_at.asc())
        )
        return [self._review_to_dict(r) for r in result.scalars().all()]

    # -------------------------------------------------------------------
    # CRUD: get single review
    # -------------------------------------------------------------------
    async def get_review(self, review_id: int) -> dict[str, Any] | None:
        review = await self._get_review(review_id)
        return self._review_to_dict(review) if review else None

    # -------------------------------------------------------------------
    # Adjudication
    # -------------------------------------------------------------------
    async def adjudicate(
        self,
        interaction_id: int,
        adjudicator_id: str,
        adjudicator_name: str,
        final_decision: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Admin adjudicates a disagreement between reviewers."""
        if final_decision not in OVERALL_LABELS:
            raise ValueError(f"Invalid final_decision: {final_decision}")

        reviews = await self._get_all_reviews_for_interaction(interaction_id)
        if not reviews:
            raise ValueError(f"No reviews found for interaction {interaction_id}")

        # Create adjudication record
        adjudication = HumanReview(
            interaction_id=interaction_id,
            trace_id=reviews[0].trace_id,
            reviewer_id=adjudicator_id,
            reviewer_name=adjudicator_name,
            overall_label=final_decision,
            comment=comment,
            is_adjudication=True,
            adjudicator_id=adjudicator_id,
            adjudicator_name=adjudicator_name,
            adjudicated_at=_dt.datetime.now(_dt.UTC),
            final_decision=final_decision,
            reviewed_question_snapshot=reviews[0].reviewed_question_snapshot,
            reviewed_answer_snapshot=reviews[0].reviewed_answer_snapshot,
            ragas_snapshot=reviews[0].ragas_snapshot,
        )
        self._session.add(adjudication)

        # Update all non-adjudication reviews
        for r in reviews:
            if not r.is_adjudication:
                r.has_disagreement = True

        await self._session.flush()

        # Update interaction_logs
        ilog = await self._get_interaction_log(interaction_id)
        if ilog:
            ilog.human_review = final_decision
            ilog.human_review_note = comment
            ilog.human_reviewed_at = _dt.datetime.now(_dt.UTC)
            await self._session.flush()

        return self._review_to_dict(adjudication)

    # -------------------------------------------------------------------
    # Review queue
    # -------------------------------------------------------------------
    async def get_review_queue(
        self,
        *,
        status_filter: str | None = None,
        intent_filter: str | None = None,
        priority_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        reviewer_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get prioritized review queue from real interaction data."""
        stmt = select(InteractionLog)
        count_stmt = select(func.count(InteractionLog.id))

        # Status filter
        if status_filter == "unreviewed":
            stmt = stmt.where(InteractionLog.human_review.is_(None))
            count_stmt = count_stmt.where(InteractionLog.human_review.is_(None))
        elif status_filter == "accepted":
            stmt = stmt.where(InteractionLog.human_review == "accepted")
            count_stmt = count_stmt.where(InteractionLog.human_review == "accepted")
        elif status_filter == "needs_review":
            stmt = stmt.where(InteractionLog.human_review == "needs_review")
            count_stmt = count_stmt.where(InteractionLog.human_review == "needs_review")
        elif status_filter == "incorrect":
            stmt = stmt.where(InteractionLog.human_review == "incorrect")
            count_stmt = count_stmt.where(InteractionLog.human_review == "incorrect")
        elif status_filter == "hallucination":
            stmt = stmt.where(InteractionLog.human_review == "hallucination")
            count_stmt = count_stmt.where(InteractionLog.human_review == "hallucination")
        elif status_filter == "insufficient_evidence":
            stmt = stmt.where(InteractionLog.human_review == "insufficient_evidence")
            count_stmt = count_stmt.where(InteractionLog.human_review == "insufficient_evidence")
        elif status_filter == "ragas_failed":
            stmt = stmt.where(InteractionLog.evaluation_status == "FAILED")
            count_stmt = count_stmt.where(InteractionLog.evaluation_status == "FAILED")

        if intent_filter:
            stmt = stmt.where(InteractionLog.intent == intent_filter)
            count_stmt = count_stmt.where(InteractionLog.intent == intent_filter)

        if date_from:
            stmt = stmt.where(InteractionLog.created_at >= date_from)
            count_stmt = count_stmt.where(InteractionLog.created_at >= date_from)
        if date_to:
            stmt = stmt.where(InteractionLog.created_at <= date_to)
            count_stmt = count_stmt.where(InteractionLog.created_at <= date_to)

        if reviewer_filter:
            stmt = stmt.join(
                HumanReview, HumanReview.interaction_id == InteractionLog.id
            ).where(HumanReview.reviewer_id == reviewer_filter)
            count_stmt = count_stmt.join(
                HumanReview, HumanReview.interaction_id == InteractionLog.id
            ).where(HumanReview.reviewer_id == reviewer_filter)

        # Compute priority score for sorting
        priority_expr = self._build_priority_expression()
        stmt = stmt.order_by(priority_expr.desc(), InteractionLog.created_at.desc())

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        entries = result.scalars().all()

        items = []
        for e in entries:
            priority = self._compute_priority_for_entry(e)
            items.append({
                "trace_id": e.trace_id,
                "question": e.question[:300],
                "answer": e.answer[:200],
                "intent": e.intent,
                "human_review": e.human_review,
                "evaluation_status": e.evaluation_status,
                "faithfulness": e.faithfulness,
                "result_count": e.result_count,
                "citation_count": e.citation_count,
                "processing_time_ms": e.processing_time_ms,
                "priority": priority,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            })

        return items, total

    # -------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------
    async def get_analytics(self) -> dict[str, Any]:
        """Get review analytics from real data."""
        base = select(func.count(HumanReview.id))

        total_r = await self._session.execute(base)
        total_reviews = total_r.scalar() or 0

        # Label counts
        label_counts: dict[str, int] = {}
        for label in OVERALL_LABELS:
            r = await self._session.execute(
                base.where(HumanReview.overall_label == label).where(HumanReview.is_adjudication == False)
            )
            label_counts[label] = r.scalar() or 0

        # Agreement/disagreement with RAGAS
        agreement = await self._compute_ragas_agreement()

        # Top error categories
        top_errors = await self._get_top_error_categories()

        # Top failure stages
        top_stages = await self._get_top_failure_stages()

        # Top failed intents
        top_intents = await self._get_top_failed_intents()

        # Top failed entities
        top_entities = await self._get_top_failed_entities()

        # Review throughput
        throughput = await self._compute_throughput()

        # Human vs RAGAS comparison
        comparison = await self._get_human_ragas_comparison()

        return {
            "total_reviews": total_reviews,
            "label_counts": label_counts,
            "ragas_agreement": agreement,
            "top_error_categories": top_errors,
            "top_failure_stages": top_stages,
            "top_failed_intents": top_intents,
            "top_failed_entities": top_entities,
            "throughput": throughput,
            "human_ragas_comparison": comparison,
        }

    # -------------------------------------------------------------------
    # Regression candidates
    # -------------------------------------------------------------------
    async def create_regression_candidate(
        self,
        interaction_id: int,
        review_id: int,
        creator_id: str,
        creator_name: str,
        *,
        expected_behavior: str,
        expected_intent: str | None = None,
        expected_entities: list[str] | None = None,
        expected_evidence: str | None = None,
    ) -> dict[str, Any]:
        """Create a regression candidate from a reviewed interaction."""
        ilog = await self._get_interaction_log(interaction_id)
        if ilog is None:
            raise ValueError(f"Interaction {interaction_id} not found")

        review = await self._get_review(review_id)
        if review is None:
            raise ValueError(f"Review {review_id} not found")

        # Determine failure category and stage from review
        failure_category = review.error_categories[0] if review.error_categories else "OTHER"
        failure_stage = review.failure_stage or "UNKNOWN"

        candidate = RegressionCandidate(
            interaction_id=interaction_id,
            trace_id=ilog.trace_id,
            review_id=review_id,
            original_question=ilog.question or "",
            actual_answer=ilog.answer or "",
            expected_behavior=expected_behavior,
            expected_intent=expected_intent,
            expected_entities=expected_entities or [],
            expected_evidence=expected_evidence,
            failure_category=failure_category,
            failure_stage=failure_stage,
            creator_id=creator_id,
            creator_name=creator_name,
            review_comment=review.comment,
        )
        self._session.add(candidate)
        await self._session.flush()

        return self._candidate_to_dict(candidate)

    async def get_regression_candidates(
        self,
        *,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List regression candidates."""
        stmt = select(RegressionCandidate)
        count_stmt = select(func.count(RegressionCandidate.id))

        if status_filter:
            stmt = stmt.where(RegressionCandidate.status == status_filter)
            count_stmt = count_stmt.where(RegressionCandidate.status == status_filter)

        stmt = stmt.order_by(RegressionCandidate.created_at.desc())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)

        return [self._candidate_to_dict(c) for c in result.scalars().all()], total

    async def update_regression_candidate(
        self,
        candidate_id: int,
        *,
        status: str | None = None,
        resolution_note: str | None = None,
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(RegressionCandidate).where(RegressionCandidate.id == candidate_id)
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            return None

        if status:
            candidate.status = status
        if resolution_note:
            candidate.resolution_note = resolution_note
        if status == "resolved":
            candidate.resolved_at = _dt.datetime.now(_dt.UTC)

        await self._session.flush()
        return self._candidate_to_dict(candidate)

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------
    async def _get_interaction_log(self, interaction_id: int) -> InteractionLog | None:
        result = await self._session.execute(
            select(InteractionLog).where(InteractionLog.id == interaction_id)
        )
        return result.scalar_one_or_none()

    async def _get_review(self, review_id: int) -> HumanReview | None:
        result = await self._session.execute(
            select(HumanReview).where(HumanReview.id == review_id)
        )
        return result.scalar_one_or_none()

    async def _get_all_reviews_for_interaction(self, interaction_id: int) -> list[HumanReview]:
        result = await self._session.execute(
            select(HumanReview)
            .where(HumanReview.interaction_id == interaction_id)
            .order_by(HumanReview.created_at.asc())
        )
        return list(result.scalars().all())

    async def _find_existing_review(
        self, interaction_id: int, reviewer_id: str
    ) -> HumanReview | None:
        result = await self._session.execute(
            select(HumanReview).where(
                HumanReview.interaction_id == interaction_id,
                HumanReview.reviewer_id == reviewer_id,
                HumanReview.is_adjudication == False,
            )
        )
        return result.scalar_one_or_none()

    async def _update_consensus_flags(self, interaction_id: int) -> None:
        """Update consensus/disagreement flags based on current reviews."""
        reviews = await self._get_all_reviews_for_interaction(interaction_id)
        non_adj = [r for r in reviews if not r.is_adjudication]
        if len(non_adj) < 2:
            return

        labels = {r.overall_label for r in non_adj}
        is_consensus = len(labels) == 1
        has_disagreement = len(labels) > 1

        for r in non_adj:
            r.is_consensus = is_consensus
            r.has_disagreement = has_disagreement

    def _build_priority_expression(self):
        """Build SQLAlchemy CASE expression for priority scoring."""
        # HIGH priority conditions
        high_conditions = [
            InteractionLog.evaluation_status == "FAILED",
            InteractionLog.human_review == "hallucination",
            InteractionLog.result_count == 0,
        ]
        # MEDIUM priority conditions
        medium_conditions = [
            InteractionLog.faithfulness.isnot(None),
            InteractionLog.citation_count == 0,
        ]

        return case(
            (and_(*high_conditions), 100),
            (and_(*medium_conditions), 50),
            else_=10,
        )

    def _compute_priority_for_entry(self, entry: InteractionLog) -> str:
        """Compute priority label for a single entry."""
        if (entry.evaluation_status == "FAILED"
                or entry.human_review == "hallucination"
                or entry.result_count == 0):
            return "HIGH"
        if (entry.faithfulness is not None and entry.faithfulness < 0.3
                or entry.citation_count == 0):
            return "MEDIUM"
        return "LOW"

    async def _compute_ragas_agreement(self) -> dict[str, Any]:
        """Compute Human vs RAGAS agreement/disagreement from real data."""
        # Join reviews with interaction logs to compare
        result = await self._session.execute(
            select(
                HumanReview.overall_label,
                InteractionLog.faithfulness,
                InteractionLog.evaluation_status,
            )
            .join(InteractionLog, HumanReview.interaction_id == InteractionLog.id)
            .where(HumanReview.is_adjudication == False)
        )
        rows = result.all()

        agreement_count = 0
        disagreement_count = 0
        ragas_false_negatives = 0
        ragas_false_positives = 0
        evaluator_weakness = 0

        for label, faithfulness, eval_status in rows:
            if eval_status != "COMPLETED" or faithfulness is None:
                continue

            ragas_high = faithfulness >= 0.7
            human_ok = label in ("accepted",)

            if human_ok and ragas_high:
                agreement_count += 1
            elif not human_ok and not ragas_high:
                agreement_count += 1
            elif human_ok and not ragas_high:
                ragas_false_negatives += 1
                disagreement_count += 1
            elif not human_ok and ragas_high:
                if label == "hallucination":
                    evaluator_weakness += 1
                else:
                    ragas_false_positives += 1
                disagreement_count += 1

        return {
            "agreement": agreement_count,
            "disagreement": disagreement_count,
            "ragas_false_negatives": ragas_false_negatives,
            "ragas_false_positives": ragas_false_positives,
            "evaluator_weakness_candidates": evaluator_weakness,
        }

    async def _get_top_error_categories(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top error categories from reviews."""
        result = await self._session.execute(
            select(
                func.unnest(HumanReview.error_categories).label("cat"),
                func.count().label("cnt"),
            )
            .where(HumanReview.is_adjudication == False)
            .group_by(func.unnest(HumanReview.error_categories))
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"category": row.cat, "count": row.cnt} for row in result.all()]

    async def _get_top_failure_stages(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top failure stages from reviews."""
        result = await self._session.execute(
            select(
                HumanReview.failure_stage,
                func.count().label("cnt"),
            )
            .where(HumanReview.failure_stage.isnot(None))
            .where(HumanReview.is_adjudication == False)
            .group_by(HumanReview.failure_stage)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"stage": row.failure_stage, "count": row.cnt} for row in result.all()]

    async def _get_top_failed_intents(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top intents that had failures."""
        result = await self._session.execute(
            select(
                InteractionLog.intent,
                func.count().label("cnt"),
            )
            .join(HumanReview, HumanReview.interaction_id == InteractionLog.id)
            .where(HumanReview.overall_label.in_(["incorrect", "hallucination"]))
            .where(HumanReview.is_adjudication == False)
            .group_by(InteractionLog.intent)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"intent": row.intent, "count": row.cnt} for row in result.all()]

    async def _get_top_failed_entities(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top entities that had failures."""
        result = await self._session.execute(
            select(
                InteractionLog.entity_resolved_name,
                func.count().label("cnt"),
            )
            .join(HumanReview, HumanReview.interaction_id == InteractionLog.id)
            .where(HumanReview.overall_label.in_(["incorrect", "hallucination"]))
            .where(HumanReview.is_adjudication == False)
            .where(InteractionLog.entity_resolved_name.isnot(None))
            .group_by(InteractionLog.entity_resolved_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"entity": row.entity_resolved_name, "count": row.cnt} for row in result.all()]

    async def _compute_throughput(self) -> dict[str, Any]:
        """Compute review throughput metrics."""
        # Reviews in last 7 days
        seven_days_ago = _dt.datetime.now(_dt.UTC) - _dt.timedelta(days=7)
        r = await self._session.execute(
            select(func.count(HumanReview.id))
            .where(HumanReview.created_at >= seven_days_ago)
            .where(HumanReview.is_adjudication == False)
        )
        last_7_days = r.scalar() or 0

        # Average reviews per day (last 7)
        avg_per_day = last_7_days / 7 if last_7_days else 0

        # Total interactions without review
        unreviewed_r = await self._session.execute(
            select(func.count(InteractionLog.id))
            .where(InteractionLog.human_review.is_(None))
        )
        unreviewed = unreviewed_r.scalar() or 0

        return {
            "reviews_last_7_days": last_7_days,
            "avg_per_day": round(avg_per_day, 1),
            "unreviewed_interactions": unreviewed,
        }

    async def _get_human_ragas_comparison(self) -> dict[str, Any]:
        """Get detailed Human vs RAGAS comparison breakdown."""
        result = await self._session.execute(
            select(
                HumanReview.overall_label,
                InteractionLog.faithfulness,
                InteractionLog.answer_relevancy,
                InteractionLog.context_precision,
                InteractionLog.context_recall,
                InteractionLog.evaluation_status,
            )
            .join(InteractionLog, HumanReview.interaction_id == InteractionLog.id)
            .where(HumanReview.is_adjudication == False)
        )
        rows = result.all()

        comparison = {
            "accepted_high_ragas": 0,
            "accepted_low_ragas": 0,
            "incorrect_high_ragas": 0,
            "incorrect_low_ragas": 0,
            "hallucination_high_ragas": 0,
            "hallucination_low_ragas": 0,
            "needs_review": 0,
            "insufficient_evidence": 0,
            "no_ragas_data": 0,
        }

        for label, faith, ar, cp, cr, eval_status in rows:
            if eval_status != "COMPLETED" or faith is None:
                comparison["no_ragas_data"] += 1
                continue

            ragas_high = faith >= 0.7

            if label == "accepted":
                if ragas_high:
                    comparison["accepted_high_ragas"] += 1
                else:
                    comparison["accepted_low_ragas"] += 1
            elif label == "incorrect":
                if ragas_high:
                    comparison["incorrect_high_ragas"] += 1
                else:
                    comparison["incorrect_low_ragas"] += 1
            elif label == "hallucination":
                if ragas_high:
                    comparison["hallucination_high_ragas"] += 1
                else:
                    comparison["hallucination_low_ragas"] += 1
            elif label == "needs_review":
                comparison["needs_review"] += 1
            elif label == "insufficient_evidence":
                comparison["insufficient_evidence"] += 1

        return comparison

    def _review_to_dict(self, review: HumanReview) -> dict[str, Any]:
        return {
            "id": review.id,
            "interaction_id": review.interaction_id,
            "trace_id": review.trace_id,
            "reviewer_id": review.reviewer_id,
            "reviewer_name": review.reviewer_name,
            "overall_label": review.overall_label,
            "correctness_score": review.correctness_score,
            "relevance_score": review.relevance_score,
            "groundedness_score": review.groundedness_score,
            "retrieval_quality": review.retrieval_quality,
            "citation_quality": review.citation_quality,
            "intent_correctness": review.intent_correctness,
            "entity_resolution_correctness": review.entity_resolution_correctness,
            "context_usage": review.context_usage,
            "permission_correctness": review.permission_correctness,
            "error_categories": review.error_categories or [],
            "failure_stage": review.failure_stage,
            "reviewer_confidence": review.reviewer_confidence,
            "comment": review.comment,
            "suggested_fix": review.suggested_fix,
            "reviewed_question_snapshot": review.reviewed_question_snapshot,
            "reviewed_answer_snapshot": review.reviewed_answer_snapshot,
            "ragas_snapshot": review.ragas_snapshot,
            "is_adjudication": review.is_adjudication,
            "adjudicator_id": review.adjudicator_id,
            "adjudicator_name": review.adjudicator_name,
            "adjudicated_at": review.adjudicated_at.isoformat() if review.adjudicated_at else None,
            "final_decision": review.final_decision,
            "is_consensus": review.is_consensus,
            "has_disagreement": review.has_disagreement,
            "review_version": review.review_version,
            "created_at": review.created_at.isoformat() if review.created_at else None,
            "updated_at": review.updated_at.isoformat() if review.updated_at else None,
        }

    def _candidate_to_dict(self, c: RegressionCandidate) -> dict[str, Any]:
        return {
            "id": c.id,
            "interaction_id": c.interaction_id,
            "trace_id": c.trace_id,
            "review_id": c.review_id,
            "original_question": c.original_question,
            "actual_answer": c.actual_answer,
            "expected_behavior": c.expected_behavior,
            "expected_intent": c.expected_intent,
            "expected_entities": c.expected_entities or [],
            "expected_evidence": c.expected_evidence,
            "failure_category": c.failure_category,
            "failure_stage": c.failure_stage,
            "creator_id": c.creator_id,
            "creator_name": c.creator_name,
            "review_comment": c.review_comment,
            "status": c.status,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            "resolution_note": c.resolution_note,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
