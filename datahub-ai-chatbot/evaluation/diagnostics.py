"""Root-cause diagnostic classifier — identifies WHERE in the pipeline failures occur and WHY.

Diagnostic layers:
  1. QUERY_UNDERSTANDING — intent misclassified, anaphora failed
  2. ENTITY_RESOLUTION — entity not found, ambiguous, wrong
  3. RETRIEVAL — no results, low relevance
  4. CONTEXT_BUILDING — insufficient context, wrong context
  5. GENERATION — fabrication, incomplete, refusal wrong
  6. DATA_QUALITY — ground truth outdated or missing
  7. EVALUATION — evaluation pipeline itself failed
"""

from __future__ import annotations

import re
from typing import Any

from evaluation.models import (
    FailureLayer,
    FailureReason,
    PipelineTrace,
    ReferenceExpected,
    RootCause,
    SystemMetrics,
)


def classify_root_cause(
    trace: PipelineTrace,
    reference: ReferenceExpected | None,
    system_metrics: SystemMetrics,
    answer_text: str,
    confidence: str,
    retrieved_contexts: list[str],
    ragas_faithfulness: float | None = None,
) -> RootCause:
    """Classify the root cause of a query's failure based on pipeline trace and metrics.

    Priority order: check from upstream to downstream. The first failure layer
    detected is the primary cause. If multiple failures exist, secondary is set.
    """
    primary: FailureLayer = FailureLayer.PASSED
    primary_reason: FailureReason = FailureReason.NONE
    secondary: FailureLayer | None = None
    secondary_reason: FailureReason | None = None
    detail = ""
    confidence_score = 1.0

    # --- Layer 1: Query Understanding ---
    if not trace.intent_detected:
        primary = FailureLayer.QUERY_UNDERSTANDING
        primary_reason = FailureReason.INTENT_MISCLASSIFIED
        detail = "No intent detected"
        confidence_score = 0.8
    elif reference and reference.intent and trace.intent_detected != reference.intent:
        # Check if it's a critical mismatch (e.g. NO_ANSWER vs ANSWER)
        if reference.is_no_answer and trace.intent_detected not in ("ENTITY_EXISTS", "GENERAL"):
            primary = FailureLayer.QUERY_UNDERSTANDING
            primary_reason = FailureReason.INTENT_MISCLASSIFIED
            detail = f"Expected {reference.intent}, got {trace.intent_detected}"
            confidence_score = 0.9

    # --- Layer 2: Entity Resolution ---
    if reference and reference.entities:
        expected_set = set(reference.entities)
        resolved = trace.entity_resolved_urn
        candidates = set(trace.entity_candidates)

        if resolved and resolved not in expected_set:
            if not candidates.intersection(expected_set):
                primary = FailureLayer.ENTITY_RESOLUTION
                primary_reason = FailureReason.ENTITY_WRONG
                detail = f"Resolved {resolved}, expected one of {reference.entities}"
                confidence_score = 0.85
            else:
                # Candidates had the right entity but resolver picked wrong
                secondary = FailureLayer.ENTITY_RESOLUTION
                secondary_reason = FailureReason.ENTITY_WRONG
                detail = f"Correct entity in candidates but resolver chose {resolved}"
        elif not resolved and not candidates.intersection(expected_set):
            primary = FailureLayer.ENTITY_RESOLUTION
            primary_reason = FailureReason.ENTITY_NOT_FOUND
            detail = f"No entity resolved, expected one of {reference.entities}"
            confidence_score = 0.9

    # --- Layer 3: Retrieval ---
    is_no_answer = reference.is_no_answer if reference else False
    has_reference = reference is not None
    if has_reference and trace.retrieval_results_count == 0 and not is_no_answer:
        if primary == FailureLayer.PASSED:
            primary = FailureLayer.RETRIEVAL
            primary_reason = FailureReason.NO_RESULTS
            detail = "Zero retrieval results for answerable question"
            confidence_score = 0.85
        else:
            secondary = FailureLayer.RETRIEVAL
            secondary_reason = FailureReason.NO_RESULTS
    elif (system_metrics.retrieval_top_k_recall is not None
          and system_metrics.retrieval_top_k_recall < 0.3
          and reference and reference.entities):
        if primary == FailureLayer.PASSED:
            primary = FailureLayer.RETRIEVAL
            primary_reason = FailureReason.LOW_RELEVANCE
            detail = f"Top-k recall {system_metrics.retrieval_top_k_recall:.2f}"
            confidence_score = 0.7

    # --- Layer 4: Context Building ---
    if has_reference and not retrieved_contexts and not is_no_answer:
        if primary == FailureLayer.PASSED:
            primary = FailureLayer.CONTEXT_BUILDING
            primary_reason = FailureReason.INSUFFICIENT_CONTEXT
            detail = "No contexts passed to generator"
            confidence_score = 0.9
    elif (system_metrics.context_coverage is not None
          and system_metrics.context_coverage < 0.3
          and reference):
        if primary == FailureLayer.PASSED:
            primary = FailureLayer.CONTEXT_BUILDING
            primary_reason = FailureReason.INSUFFICIENT_CONTEXT
            detail = f"Context coverage {system_metrics.context_coverage:.2f}"
            confidence_score = 0.7

    # --- Layer 5: Generation ---
    if answer_text and reference:
        # Check for fabrication — answer claims something not in context
        if ragas_faithfulness is not None and ragas_faithfulness < 0.3:
            if primary == FailureLayer.PASSED:
                primary = FailureLayer.GENERATION
                primary_reason = FailureReason.FABRICATION
                detail = f"Faithfulness {ragas_faithfulness:.2f} indicates fabrication"
                confidence_score = 0.75

        # Check for incorrect refusal
        if reference.is_no_answer:
            refusal_phrases = [
                "không tìm thấy", "không có", "không thể", "xin lỗi",
                "không biết", "không đủ", "i don't know", "cannot",
                "not enough", "not found", "no information",
            ]
            is_refusal = any(p in answer_text.lower() for p in refusal_phrases) or confidence == "low"
            if not is_refusal:
                primary = FailureLayer.GENERATION
                primary_reason = FailureReason.REFUSAL_INCORRECT
                detail = "Should refuse but gave an answer"
                confidence_score = 0.8

        # Check for incomplete answer (expected keywords missing)
        if reference.answer_contains:
            answer_lower = answer_text.lower()
            missing = [kw for kw in reference.answer_contains if kw.lower() not in answer_lower]
            if len(missing) > len(reference.answer_contains) * 0.5:
                if primary == FailureLayer.PASSED:
                    primary = FailureLayer.GENERATION
                    primary_reason = FailureReason.INCOMPLETE_ANSWER
                    detail = f"Missing keywords: {missing[:3]}"
                    confidence_score = 0.6

    # --- Layer 6: Data Quality ---
    if reference and not reference.entities and not reference.answer_contains and not reference.is_no_answer:
        if primary == FailureLayer.PASSED:
            primary = FailureLayer.DATA_QUALITY
            primary_reason = FailureReason.GROUND_TRUTH_MISSING
            detail = "Reference has no verifiable expectations"
            confidence_score = 0.5

    # --- Special case: correct no-answer ---
    if reference and reference.is_no_answer:
        refusal_phrases = [
            "không tìm thấy", "không có", "không thể", "xin lỗi",
            "không biết", "không đủ", "i don't know", "cannot",
            "not enough", "not found", "no information",
        ]
        is_refusal = any(p in answer_text.lower() for p in refusal_phrases) or confidence == "low"
        if is_refusal:
            primary = FailureLayer.PASSED
            primary_reason = FailureReason.NONE
            detail = "Correctly refused unanswerable question"
            confidence_score = 1.0

    return RootCause(
        primary_layer=primary,
        primary_reason=primary_reason,
        secondary_layer=secondary,
        secondary_reason=secondary_reason,
        detail=detail,
        confidence=confidence_score,
    )


def classify_from_ragas(
    faithfulness: float | None,
    answer_relevancy: float | None,
    context_precision: float | None,
    context_recall: float | None,
    has_reference: bool,
) -> RootCause:
    """Quick root-cause classification from RAGAS scores alone (no pipeline trace).

    Used when we only have RAGAS results, not full pipeline data.
    """
    issues: list[tuple[FailureLayer, FailureReason, str, float]] = []

    if faithfulness is not None and faithfulness < 0.3:
        issues.append((FailureLayer.GENERATION, FailureReason.FABRICATION,
                       f"Low faithfulness: {faithfulness:.2f}", 0.7))

    if answer_relevancy is not None and answer_relevancy < 0.3:
        issues.append((FailureLayer.GENERATION, FailureReason.INCOMPLETE_ANSWER,
                       f"Low answer relevancy: {answer_relevancy:.2f}", 0.6))

    if context_precision is not None and context_precision < 0.3 and has_reference:
        issues.append((FailureLayer.RETRIEVAL, FailureReason.LOW_RELEVANCE,
                       f"Low context precision: {context_precision:.2f}", 0.65))

    if context_recall is not None and context_recall < 0.3 and has_reference:
        issues.append((FailureLayer.CONTEXT_BUILDING, FailureReason.INSUFFICIENT_CONTEXT,
                       f"Low context recall: {context_recall:.2f}", 0.7))

    if not issues:
        # No RAGAS data to diagnose from — confidence is unavailable
        has_any_data = any(v is not None for v in [faithfulness, answer_relevancy, context_precision, context_recall])
        if has_any_data:
            # All RAGAS scores are above thresholds — likely PASSED
            return RootCause(primary_layer=FailureLayer.PASSED,
                             primary_reason=FailureReason.NONE, confidence=0.5)
        else:
            # No RAGAS data at all — cannot diagnose
            return RootCause(primary_layer=FailureLayer.UNKNOWN,
                             primary_reason=FailureReason.NONE, confidence=None,
                             detail="No RAGAS data available for diagnosis")

    # Sort by confidence descending, pick primary + secondary
    issues.sort(key=lambda x: x[3], reverse=True)
    primary_layer, primary_reason, detail, conf = issues[0]
    secondary_layer = issues[1][0] if len(issues) > 1 else None
    secondary_reason = issues[1][1] if len(issues) > 1 else None

    return RootCause(
        primary_layer=primary_layer,
        primary_reason=primary_reason,
        secondary_layer=secondary_layer,
        secondary_reason=secondary_reason,
        detail=detail,
        confidence=conf,
    )
