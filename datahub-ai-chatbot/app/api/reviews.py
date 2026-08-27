"""Human quality review API endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.services.human_review_service import (
    ERROR_CATEGORIES,
    FAILURE_STAGES,
    OVERALL_LABELS,
    PERMISSION_CHOICES,
    REVIEWER_CONFIDENCE_CHOICES,
    HumanReviewService,
)
from database.session import get_session

log = structlog.get_logger(__name__)
router = APIRouter()


def _require_admin(user=Depends(get_current_user)):
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class CreateReviewRequest(BaseModel):
    interaction_id: int
    trace_id: str
    reviewer_id: str
    reviewer_name: str = ""
    overall_label: str
    correctness_score: float | None = None
    relevance_score: float | None = None
    groundedness_score: float | None = None
    retrieval_quality: float | None = None
    citation_quality: float | None = None
    intent_correctness: bool | None = None
    entity_resolution_correctness: bool | None = None
    context_usage: bool | None = None
    permission_correctness: str | None = None
    error_categories: list[str] = Field(default_factory=list)
    failure_stage: str | None = None
    reviewer_confidence: str | None = None
    comment: str | None = None
    suggested_fix: str | None = None


class UpdateReviewRequest(BaseModel):
    overall_label: str | None = None
    correctness_score: float | None = None
    relevance_score: float | None = None
    groundedness_score: float | None = None
    retrieval_quality: float | None = None
    citation_quality: float | None = None
    intent_correctness: bool | None = None
    entity_resolution_correctness: bool | None = None
    context_usage: bool | None = None
    permission_correctness: str | None = None
    error_categories: list[str] | None = None
    failure_stage: str | None = None
    reviewer_confidence: str | None = None
    comment: str | None = None
    suggested_fix: str | None = None


class AdjudicateRequest(BaseModel):
    interaction_id: int
    adjudicator_id: str
    adjudicator_name: str = ""
    final_decision: str
    comment: str | None = None


class CreateRegressionRequest(BaseModel):
    interaction_id: int
    review_id: int
    creator_id: str
    creator_name: str = ""
    expected_behavior: str
    expected_intent: str | None = None
    expected_entities: list[str] = Field(default_factory=list)
    expected_evidence: str | None = None


class UpdateRegressionRequest(BaseModel):
    status: str | None = None
    resolution_note: str | None = None


# ---------------------------------------------------------------------------
# IMPORTANT: Fixed-path routes MUST come before parameterized routes
# FastAPI matches routes in definition order.
# Router prefix: /api/v1/reviews
# So "/taxonomy" → /api/v1/reviews/taxonomy
# ---------------------------------------------------------------------------

# GET /taxonomy — error taxonomy and failure stages
@router.get("/taxonomy")
async def get_taxonomy(_user=Depends(_require_admin)):
    """Return the canonical error taxonomy, failure stages, and label semantics."""
    return {
        "error_categories": ERROR_CATEGORIES,
        "failure_stages": FAILURE_STAGES,
        "overall_labels": OVERALL_LABELS,
        "label_semantics": {
            "accepted": "Answer is correct, evidence is appropriate, no critical errors.",
            "needs_review": "Not enough certainty or needs additional reviewer inspection.",
            "incorrect": "Answer contains incorrect information or reasoning.",
            "hallucination": "Chatbot provided information not supported by DataHub/context/evidence.",
            "insufficient_evidence": "Answer may not be wrong but system lacks sufficient evidence/context to prove it.",
        },
        "permission_choices": PERMISSION_CHOICES,
        "reviewer_confidence_choices": REVIEWER_CONFIDENCE_CHOICES,
    }


# POST /submit — create a review (using /submit to avoid /reviews collision)
@router.post("/submit")
async def create_review(
    req: CreateReviewRequest,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create a new human review for an interaction."""
    svc = HumanReviewService(session)
    try:
        review = await svc.create_review(
            interaction_id=req.interaction_id,
            trace_id=req.trace_id,
            reviewer_id=req.reviewer_id,
            reviewer_name=req.reviewer_name,
            overall_label=req.overall_label,
            correctness_score=req.correctness_score,
            relevance_score=req.relevance_score,
            groundedness_score=req.groundedness_score,
            retrieval_quality=req.retrieval_quality,
            citation_quality=req.citation_quality,
            intent_correctness=req.intent_correctness,
            entity_resolution_correctness=req.entity_resolution_correctness,
            context_usage=req.context_usage,
            permission_correctness=req.permission_correctness,
            error_categories=req.error_categories,
            failure_stage=req.failure_stage,
            reviewer_confidence=req.reviewer_confidence,
            comment=req.comment,
            suggested_fix=req.suggested_fix,
        )
        await session.commit()
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# POST /adjudicate — admin adjudication
@router.post("/adjudicate")
async def adjudicate(
    req: AdjudicateRequest,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin adjudicates a disagreement between reviewers."""
    svc = HumanReviewService(session)
    try:
        result = await svc.adjudicate(
            interaction_id=req.interaction_id,
            adjudicator_id=req.adjudicator_id,
            adjudicator_name=req.adjudicator_name,
            final_decision=req.final_decision,
            comment=req.comment,
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# GET /queue — prioritized review queue
@router.get("/queue")
async def get_review_queue(
    status: str | None = Query(None),
    intent: str | None = Query(None),
    priority: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    reviewer: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get prioritized review queue with filtering."""
    svc = HumanReviewService(session)
    items, total = await svc.get_review_queue(
        status_filter=status,
        intent_filter=intent,
        priority_filter=priority,
        date_from=date_from,
        date_to=date_to,
        reviewer_filter=reviewer,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# GET /analytics — review analytics from real data
@router.get("/analytics")
async def get_analytics(
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get review analytics computed from real data."""
    svc = HumanReviewService(session)
    return await svc.get_analytics()


# GET /interaction/{interaction_id} — get reviews for interaction
@router.get("/interaction/{interaction_id}")
async def get_reviews_for_interaction(
    interaction_id: int,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get all reviews for an interaction (multiple reviewers)."""
    svc = HumanReviewService(session)
    reviews = await svc.get_reviews_for_interaction(interaction_id)
    return {"reviews": reviews, "total": len(reviews)}


# GET /regression-candidates — list regression candidates (before /{review_id})
@router.get("/regression-candidates")
async def list_regression_candidates(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List regression candidates."""
    svc = HumanReviewService(session)
    items, total = await svc.get_regression_candidates(
        status_filter=status, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# POST /regression-candidates — create regression candidate
@router.post("/regression-candidates")
async def create_regression_candidate(
    req: CreateRegressionRequest,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create a regression candidate from a reviewed interaction."""
    svc = HumanReviewService(session)
    try:
        candidate = await svc.create_regression_candidate(
            interaction_id=req.interaction_id,
            review_id=req.review_id,
            creator_id=req.creator_id,
            creator_name=req.creator_name,
            expected_behavior=req.expected_behavior,
            expected_intent=req.expected_intent,
            expected_entities=req.expected_entities,
            expected_evidence=req.expected_evidence,
        )
        await session.commit()
        return candidate
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# PATCH /regression-candidates/{candidate_id} — update regression candidate
@router.patch("/regression-candidates/{candidate_id}")
async def update_regression_candidate(
    candidate_id: int,
    req: UpdateRegressionRequest,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update a regression candidate status."""
    svc = HumanReviewService(session)
    result = await svc.update_regression_candidate(
        candidate_id, status=req.status, resolution_note=req.resolution_note,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await session.commit()
    return result


# PATCH /{review_id} — update a review (MUST be last among GET routes)
@router.patch("/{review_id}")
async def update_review(
    review_id: int,
    req: UpdateReviewRequest,
    reviewer_id: str = Query(...),
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update an existing review (only original reviewer can update)."""
    svc = HumanReviewService(session)
    try:
        update_data = req.model_dump(exclude_unset=True)
        review = await svc.update_review(review_id, reviewer_id, **update_data)
        await session.commit()
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# GET /{review_id} — get single review (MUST be last among GET routes)
@router.get("/{review_id}")
async def get_review(
    review_id: int,
    _user=Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get a single review by ID."""
    svc = HumanReviewService(session)
    review = await svc.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
