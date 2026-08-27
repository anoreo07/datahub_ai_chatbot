"""Deterministic system metrics — no LLM needed, computed from pipeline trace vs reference.

Every metric uses set_metric() to track both score AND status:
  - None score + NOT_EVALUATED = metric was not computed (missing required input)
  - 0.0 score + COMPLETED = metric was computed, result is zero
  - 0.0–1.0 score + COMPLETED = metric computed successfully

Capability requirements per metric:
  - entity_accuracy: needs reference.entities
  - entity_precision: needs reference.entities
  - entity_recall: needs reference.entities
  - retrieval_hit: needs reference.entities or citation_urns
  - retrieval_top_k_recall: needs reference.entities
  - context_coverage: needs reference.answer_contains or reference.fields + contexts
  - citation_correctness: needs reference.citations or reference.entities
  - citation_completeness: needs reference.citations or reference.entities
  - intent_accuracy: needs reference.intent
  - no_answer_accuracy: needs reference.is_no_answer
  - metadata_field_accuracy: needs reference.metadata_fields
"""

from __future__ import annotations

from typing import Any

from evaluation.models import MetricStatus, PipelineTrace, ReferenceExpected, SystemMetrics


def compute_system_metrics(
    trace: PipelineTrace,
    reference: ReferenceExpected | None,
    answer_text: str,
    confidence: str,
    retrieved_contexts: list[str] | None = None,
    citation_urns: list[str] | None = None,
) -> SystemMetrics:
    """Compute deterministic system metrics from pipeline trace vs reference.

    Metrics without required input are set to None + NOT_EVALUATED.
    Metrics with required input are computed and set to score + COMPLETED.
    """
    metrics = SystemMetrics(processing_time_ms=trace.processing_time_ms)

    if reference is None:
        # No reference data — all metrics are NOT_EVALUATED
        _set_all_not_evaluated(metrics, "No reference data available")
        # Only processing_time_ms is meaningful
        return metrics

    # --- Entity metrics ---
    if reference.entities:
        expected_set = set(reference.entities)
        resolved = trace.entity_resolved_urn
        candidates = trace.entity_candidates

        # Accuracy
        if resolved:
            score = 1.0 if resolved in expected_set else 0.0
            reason = None if score == 1.0 else f"Resolved {resolved}, expected one of {reference.entities}"
        else:
            score = 0.0
            reason = "No entity resolved"
        metrics.set_metric("entity_accuracy", score, MetricStatus.COMPLETED, reason)

        # Precision
        all_detected = set(candidates)
        if resolved:
            all_detected.add(resolved)
        if all_detected:
            correct = all_detected.intersection(expected_set)
            precision = len(correct) / len(all_detected)
            reason = None if precision == 1.0 else f"{len(correct)}/{len(all_detected)} detected are correct"
        else:
            precision = 0.0
            reason = "No entities detected"
        metrics.set_metric("entity_precision", precision, MetricStatus.COMPLETED, reason)

        # Recall
        if all_detected:
            recall = len(all_detected.intersection(expected_set)) / len(expected_set)
            reason = None if recall == 1.0 else f"Found {len(all_detected.intersection(expected_set))}/{len(expected_set)} expected"
        else:
            recall = 0.0
            reason = "No entities detected"
        metrics.set_metric("entity_recall", recall, MetricStatus.COMPLETED, reason)
    else:
        # No expected entities — mark entity metrics as NOT_EVALUATED
        metrics.set_metric("entity_accuracy", None, MetricStatus.NOT_EVALUATED, "No expected entity in reference")
        metrics.set_metric("entity_precision", None, MetricStatus.NOT_EVALUATED, "No expected entity in reference")
        metrics.set_metric("entity_recall", None, MetricStatus.NOT_EVALUATED, "No expected entity in reference")

    # --- Retrieval metrics ---
    if reference.entities:
        expected_urns = set(reference.entities)
        retrieval_urns = set(citation_urns) if citation_urns else set()
        if trace.entity_resolved_urn:
            retrieval_urns.add(trace.entity_resolved_urn)

        hit = bool(retrieval_urns.intersection(expected_urns))
        reason = None if hit else f"No overlap between retrieved {len(retrieval_urns)} and expected {len(expected_urns)} entities"
        metrics.set_metric("retrieval_hit", hit, MetricStatus.COMPLETED, reason)

        top_k_recall = (
            len(retrieval_urns.intersection(expected_urns)) / len(expected_urns)
            if expected_urns else 0.0
        )
        reason = None if top_k_recall == 1.0 else f"Found {len(retrieval_urns.intersection(expected_urns))}/{len(expected_urns)} in top-k"
        metrics.set_metric("retrieval_top_k_recall", top_k_recall, MetricStatus.COMPLETED, reason)
    elif citation_urns:
        # Has citations but no expected entities — can't evaluate retrieval precision
        metrics.set_metric("retrieval_hit", None, MetricStatus.NOT_EVALUATED, "No expected entity to verify against")
        metrics.set_metric("retrieval_top_k_recall", None, MetricStatus.NOT_EVALUATED, "No expected entity to verify against")
    else:
        # No expected entities AND no citations
        hit = trace.retrieval_results_count > 0
        metrics.set_metric("retrieval_hit", hit, MetricStatus.COMPLETED,
                           None if hit else "No retrieval results")
        metrics.set_metric("retrieval_top_k_recall", None, MetricStatus.NOT_EVALUATED,
                           "No expected entity for recall calculation")

    # --- Context coverage ---
    if reference.answer_contains and retrieved_contexts:
        context_text = " ".join(retrieved_contexts).lower()
        covered = sum(1 for kw in reference.answer_contains if kw.lower() in context_text)
        coverage = covered / len(reference.answer_contains)
        reason = None if coverage == 1.0 else f"{covered}/{len(reference.answer_contains)} expected facts found in context"
        metrics.set_metric("context_coverage", coverage, MetricStatus.COMPLETED, reason)
    elif reference.fields and retrieved_contexts:
        context_text = " ".join(retrieved_contexts).lower()
        covered = sum(1 for f in reference.fields if f.lower() in context_text)
        coverage = covered / len(reference.fields) if reference.fields else 1.0
        reason = None if coverage == 1.0 else f"{covered}/{len(reference.fields)} expected fields found in context"
        metrics.set_metric("context_coverage", coverage, MetricStatus.COMPLETED, reason)
    else:
        # No expected facts/fields to check against
        metrics.set_metric("context_coverage", None, MetricStatus.NOT_EVALUATED,
                           "No expected facts or fields in reference")

    # --- Citation correctness ---
    if citation_urns and (reference.citations or reference.entities):
        expected_citation_urns = set(reference.citations or reference.entities)
        actual_urns = set(citation_urns)
        if actual_urns:
            correct = actual_urns.intersection(expected_citation_urns)
            correctness = len(correct) / len(actual_urns)
            reason = None if correctness == 1.0 else f"{len(correct)}/{len(actual_urns)} citations point to expected entities"
        else:
            correctness = 0.0
            reason = "No citations produced"
        metrics.set_metric("citation_correctness", correctness, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("citation_correctness", None, MetricStatus.NOT_EVALUATED,
                           "No citation reference to verify against")

    # --- Citation completeness ---
    if (reference.citations or reference.entities) and citation_urns:
        expected_urns = set(reference.citations or reference.entities)
        actual_urns = set(citation_urns)
        completeness = len(expected_urns.intersection(actual_urns)) / len(expected_urns) if expected_urns else 1.0
        reason = None if completeness == 1.0 else f"{len(expected_urns.intersection(actual_urns))}/{len(expected_urns)} expected citations present"
        metrics.set_metric("citation_completeness", completeness, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("citation_completeness", None, MetricStatus.NOT_EVALUATED,
                           "No citation expectation to verify against")

    # --- Intent accuracy ---
    if reference.intent:
        match = trace.intent_detected == reference.intent
        reason = None if match else f"Expected {reference.intent}, got {trace.intent_detected}"
        metrics.set_metric("intent_accuracy", 1.0 if match else 0.0, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("intent_accuracy", None, MetricStatus.NOT_EVALUATED,
                           "No expected intent in reference")

    # --- No-answer accuracy ---
    if reference.is_no_answer is not None:
        refusal_phrases = [
            "khong tim thay", "khong co", "khong the", "xin loi",
            "khong biet", "khong du", "i don't know", "cannot",
            "not enough", "not found", "no information",
        ]
        is_refusal = any(p in answer_text.lower() for p in refusal_phrases) or confidence == "low"
        if reference.is_no_answer:
            score = 1.0 if is_refusal else 0.0
            reason = None if score == 1.0 else "Should refuse but gave an answer"
        else:
            score = 1.0 if (answer_text and confidence != "low") else 0.5
            reason = None if score == 1.0 else "Empty answer or low confidence for answerable question"
        metrics.set_metric("no_answer_accuracy", score, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("no_answer_accuracy", None, MetricStatus.NOT_EVALUATED,
                           "No is_no_answer expectation in reference")

    # --- Metadata field accuracy ---
    if reference.metadata_fields:
        if answer_text:
            answer_lower = answer_text.lower()
            matched = sum(1 for k, v in reference.metadata_fields.items()
                          if v.lower() in answer_lower or k.lower() in answer_lower)
            accuracy = matched / len(reference.metadata_fields)
            reason = None if accuracy == 1.0 else f"{matched}/{len(reference.metadata_fields)} metadata fields found"
        else:
            accuracy = 0.0
            reason = "Empty answer"
        metrics.set_metric("metadata_field_accuracy", accuracy, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("metadata_field_accuracy", None, MetricStatus.NOT_EVALUATED,
                           "No metadata fields in reference")

    return metrics


def compute_metrics_from_answer_only(
    answer_text: str,
    confidence: str,
    reference: ReferenceExpected | None,
) -> SystemMetrics:
    """Compute limited metrics when we only have the answer text (no pipeline trace).

    Used for retrospective evaluation of existing interaction logs.
    Most metrics are NOT_EVALUATED because we lack pipeline trace data.
    """
    metrics = SystemMetrics()

    if reference is None:
        _set_all_not_evaluated(metrics, "No reference data available")
        return metrics

    # Only no_answer_accuracy and metadata_field_accuracy can be computed from answer alone
    if reference.is_no_answer is not None:
        refusal_phrases = [
            "khong tim thay", "khong co", "khong the", "xin loi",
            "khong biet", "khong du", "i don't know", "cannot",
            "not enough", "not found", "no information",
        ]
        is_refusal = any(p in answer_text.lower() for p in refusal_phrases) or confidence == "low"
        if reference.is_no_answer:
            score = 1.0 if is_refusal else 0.0
            reason = None if score == 1.0 else "Should refuse but gave an answer"
        else:
            score = 1.0 if (answer_text and confidence != "low") else 0.5
            reason = None if score == 1.0 else "Empty answer or low confidence"
        metrics.set_metric("no_answer_accuracy", score, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("no_answer_accuracy", None, MetricStatus.NOT_EVALUATED,
                           "No is_no_answer expectation in reference")

    if reference.metadata_fields:
        if answer_text:
            answer_lower = answer_text.lower()
            matched = sum(1 for k, v in reference.metadata_fields.items()
                          if v.lower() in answer_lower or k.lower() in answer_lower)
            accuracy = matched / len(reference.metadata_fields)
            reason = None if accuracy == 1.0 else f"{matched}/{len(reference.metadata_fields)} metadata fields found"
        else:
            accuracy = 0.0
            reason = "Empty answer"
        metrics.set_metric("metadata_field_accuracy", accuracy, MetricStatus.COMPLETED, reason)
    else:
        metrics.set_metric("metadata_field_accuracy", None, MetricStatus.NOT_EVALUATED,
                           "No metadata fields in reference")

    # All other metrics are NOT_EVALUATED (no pipeline trace)
    for name in ["entity_accuracy", "entity_precision", "entity_recall",
                 "retrieval_hit", "retrieval_top_k_recall", "context_coverage",
                 "citation_correctness", "citation_completeness", "intent_accuracy"]:
        if metrics.get_metric_status(name) == MetricStatus.NOT_EVALUATED:
            metrics.set_metric(name, None, MetricStatus.NOT_EVALUATED,
                               "No pipeline trace available for retrospective evaluation")

    return metrics


def _set_all_not_evaluated(metrics: SystemMetrics, reason: str) -> None:
    """Set all metrics to NOT_EVALUATED with a common reason."""
    for name in ["entity_accuracy", "entity_precision", "entity_recall",
                 "retrieval_hit", "retrieval_top_k_recall", "context_coverage",
                 "citation_correctness", "citation_completeness",
                 "intent_accuracy", "no_answer_accuracy", "metadata_field_accuracy"]:
        metrics.set_metric(name, None, MetricStatus.NOT_EVALUATED, reason)
