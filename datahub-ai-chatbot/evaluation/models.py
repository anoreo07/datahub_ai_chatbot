"""Evaluation data models — structured reference, pipeline trace, root-cause, system metrics.

Design principles:
  - No hard-coding of entity/term names in reference data.
  - Provenance + versioning on every reference sample.
  - Every failure gets a root-cause layer classification.
  - Deterministic system metrics are separate from LLM-based RAGAS metrics.
  - Every metric has: score (float|null), status (str), reason (str|null).
  - None score + NOT_EVALUATED status = metric was not computed.
  - 0.0 score + COMPLETED status = metric was computed and result is 0.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Metric status contract
# ---------------------------------------------------------------------------
class MetricStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NOT_EVALUATED = "NOT_EVALUATED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"


def _metric_dict(score: float | None, status: str, reason: str | None = None) -> dict[str, Any]:
    """Create a standardized metric dict with score, status, and optional reason."""
    d: dict[str, Any] = {"score": score, "status": status}
    if reason:
        d["reason"] = reason
    return d


# ---------------------------------------------------------------------------
# Root-cause classifier — what layer failed and why
# ---------------------------------------------------------------------------
class FailureLayer(str, Enum):
    QUERY_UNDERSTANDING = "QUERY_UNDERSTANDING"
    ENTITY_RESOLUTION = "ENTITY_RESOLUTION"
    RETRIEVAL = "RETRIEVAL"
    CONTEXT_BUILDING = "CONTEXT_BUILDING"
    GENERATION = "GENERATION"
    DATA_QUALITY = "DATA_QUALITY"
    EVALUATION = "EVALUATION"
    PASSED = "PASSED"
    UNKNOWN = "UNKNOWN"


class FailureReason(str, Enum):
    INTENT_MISCLASSIFIED = "intent_misclassified"
    ENTITY_NOT_FOUND = "entity_not_found"
    ENTITY_AMBIGUOUS = "entity_ambiguous"
    ENTITY_WRONG = "entity_wrong"
    NO_RESULTS = "no_results"
    LOW_RELEVANCE = "low_relevance"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    CITATION_MISSING = "citation_missing"
    CITATION_WRONG = "citation_wrong"
    FABRICATION = "fabrication"
    INCOMPLETE_ANSWER = "incomplete_answer"
    REFUSAL_INCORRECT = "refusal_incorrect"
    REFUSAL_MISSING = "refusal_missing"
    TIMEOUT = "timeout"
    MODEL_ERROR = "model_error"
    GROUND_TRUTH_MISSING = "ground_truth_missing"
    EVALUATION_ERROR = "evaluation_error"
    NONE = "none"


@dataclass
class RootCause:
    """Diagnostic classification of where/why a query failed."""
    primary_layer: FailureLayer = FailureLayer.UNKNOWN
    primary_reason: FailureReason = FailureReason.NONE
    secondary_layer: FailureLayer | None = None
    secondary_reason: FailureReason | None = None
    detail: str = ""
    confidence: float | None = None  # None = unavailable, 0.0–1.0 when computed

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_layer": self.primary_layer.value,
            "primary_reason": self.primary_reason.value,
            "secondary_layer": self.secondary_layer.value if self.secondary_layer else None,
            "secondary_reason": self.secondary_reason.value if self.secondary_reason else None,
            "detail": self.detail,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Pipeline trace — what happened at each step
# ---------------------------------------------------------------------------
@dataclass
class PipelineStep:
    """One step in the pipeline trace."""
    step_name: str
    status: str = "ok"  # ok | error | skipped | timeout
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step_name": self.step_name,
            "status": self.status,
            "duration_ms": self.duration_ms,
        }
        if self.input_summary:
            d["input_summary"] = self.input_summary
        if self.output_summary:
            d["output_summary"] = self.output_summary
        if self.error:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class PipelineTrace:
    """Full trace of how a query was processed — from input to evaluation."""
    trace_id: str
    question: str
    steps: list[PipelineStep] = field(default_factory=list)
    normalized_query: str = ""
    intent_detected: str = ""
    entity_candidates: list[str] = field(default_factory=list)
    entity_resolved_urn: str | None = None
    entity_resolved_name: str | None = None
    retrieval_query: str = ""
    retrieval_results_count: int = 0
    retrieval_top_scores: list[float] = field(default_factory=list)
    context_documents_count: int = 0
    citation_ids: list[str] = field(default_factory=list)
    citation_urns: list[str] = field(default_factory=list)
    answer_text: str = ""
    confidence: str = ""
    processing_time_ms: float = 0.0

    def add_step(self, step: PipelineStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "question": self.question,
            "steps": [s.to_dict() for s in self.steps],
            "normalized_query": self.normalized_query,
            "intent_detected": self.intent_detected,
            "entity_candidates": self.entity_candidates,
            "entity_resolved_urn": self.entity_resolved_urn,
            "entity_resolved_name": self.entity_resolved_name,
            "retrieval_query": self.retrieval_query,
            "retrieval_results_count": self.retrieval_results_count,
            "retrieval_top_scores": self.retrieval_top_scores,
            "context_documents_count": self.context_documents_count,
            "citation_ids": self.citation_ids,
            "citation_urns": self.citation_urns,
            "answer_text": self.answer_text,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
        }


# ---------------------------------------------------------------------------
# Reference model — structured ground truth with provenance
# ---------------------------------------------------------------------------
@dataclass
class ReferenceExpected:
    """What we expect the system to produce for a reference question."""
    answer_contains: list[str] = field(default_factory=list)
    answer_not_contains: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    intent: str = ""
    is_no_answer: bool = False
    fields: list[str] = field(default_factory=list)
    domain: str = ""
    owner: str = ""
    lineage_upstreams: list[str] = field(default_factory=list)
    lineage_downstreams: list[str] = field(default_factory=list)
    glossary_terms: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    metadata_fields: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class ReferenceProvenance:
    """Where the ground truth came from and when it was last verified."""
    source: str = "manual"
    datahub_snapshot_at: str | None = None
    verified_by: str | None = None
    verified_at: str | None = None
    confidence: float = 1.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class ReferenceSample:
    """A single evaluation sample with structured reference and provenance."""
    id: str
    question: str
    expected: ReferenceExpected = field(default_factory=ReferenceExpected)
    provenance: ReferenceProvenance = field(default_factory=ReferenceProvenance)
    tags: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    category: str = ""
    notes: str = ""
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "expected": self.expected.to_dict(),
            "provenance": self.provenance.to_dict(),
            "tags": self.tags,
            "difficulty": self.difficulty,
            "category": self.category,
            "notes": self.notes,
            "schema_version": self.schema_version,
        }


@dataclass
class ReferenceDataset:
    """Collection of reference samples with versioning."""
    name: str
    version: str
    description: str = ""
    samples: list[ReferenceSample] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sample_count": len(self.samples),
            "samples": [s.to_dict() for s in self.samples],
        }


# ---------------------------------------------------------------------------
# System metrics — deterministic, no LLM needed
#
# Every metric field is float | None:
#   None  = NOT_EVALUATED (metric was not computed, missing required input)
#   0.0   = COMPLETED with score 0 (metric was computed, result is zero)
#   0.0–1 = COMPLETED with score (metric was computed successfully)
#
# Boolean metrics (retrieval_hit) use None | True | False with the same semantics.
# ---------------------------------------------------------------------------
@dataclass
class SystemMetrics:
    """Deterministic metrics computed from pipeline trace vs reference.

    Per-metric status is tracked in _statuses dict.  The to_dict() method
    returns each metric as {score, status, reason?} so the API and frontend
    can distinguish "not evaluated" from "evaluated as zero."
    """
    entity_accuracy: float | None = None
    entity_precision: float | None = None
    entity_recall: float | None = None
    retrieval_hit: bool | None = None
    retrieval_top_k_recall: float | None = None
    context_coverage: float | None = None
    citation_correctness: float | None = None
    citation_completeness: float | None = None
    intent_accuracy: float | None = None
    no_answer_accuracy: float | None = None
    metadata_field_accuracy: float | None = None
    processing_time_ms: float = 0.0

    # Per-metric status tracking: metric_name -> (status, reason)
    _statuses: dict[str, tuple[str, str | None]] = field(default_factory=dict)

    def set_metric(
        self, name: str, score: float | None, status: str, reason: str | None = None,
    ) -> None:
        """Set a metric value and its status together."""
        setattr(self, name, score)
        self._statuses[name] = (status, reason)

    def get_metric_status(self, name: str) -> str:
        """Get the status of a metric. Defaults to NOT_EVALUATED."""
        if name in self._statuses:
            return self._statuses[name][0]
        # If metric has a value, assume COMPLETED (backward compat)
        val = getattr(self, name, None)
        if val is not None:
            return MetricStatus.COMPLETED
        return MetricStatus.NOT_EVALUATED

    def get_metric_reason(self, name: str) -> str | None:
        """Get the reason for a metric's status."""
        if name in self._statuses:
            return self._statuses[name][1]
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return metrics as {metric_name: {score, status, reason?}} dict.

        Also includes processing_time_ms as a plain number (not a metric).
        """
        metric_names = [
            "entity_accuracy", "entity_precision", "entity_recall",
            "retrieval_hit", "retrieval_top_k_recall", "context_coverage",
            "citation_correctness", "citation_completeness",
            "intent_accuracy", "no_answer_accuracy", "metadata_field_accuracy",
        ]
        result: dict[str, Any] = {"processing_time_ms": self.processing_time_ms}
        for name in metric_names:
            score = getattr(self, name)
            status = self.get_metric_status(name)
            reason = self.get_metric_reason(name)
            result[name] = _metric_dict(score, status, reason)
        return result

    def overall_score(self) -> float | None:
        """Weighted average of COMPLETED metrics only.

        Returns None if no metrics were evaluated.
        A metric with score 0.0 and status COMPLETED IS included.
        """
        scores = []
        weights = []

        # Entity metrics (combined)
        if self.entity_accuracy is not None and self.entity_recall is not None:
            scores.append((self.entity_accuracy + self.entity_recall) / 2)
            weights.append(1.0)
        elif self.entity_accuracy is not None:
            scores.append(self.entity_accuracy)
            weights.append(0.8)
        elif self.entity_recall is not None:
            scores.append(self.entity_recall)
            weights.append(0.8)

        # Retrieval
        if self.retrieval_hit is not None:
            scores.append(1.0 if self.retrieval_hit else 0.0)
            weights.append(1.0)
        elif self.retrieval_top_k_recall is not None:
            scores.append(self.retrieval_top_k_recall)
            weights.append(0.5)

        # Context
        if self.context_coverage is not None:
            scores.append(self.context_coverage)
            weights.append(1.0)

        # Citation
        if self.citation_correctness is not None:
            scores.append(self.citation_correctness)
            weights.append(0.8)

        # Intent
        if self.intent_accuracy is not None:
            scores.append(self.intent_accuracy)
            weights.append(1.0)

        # No-answer
        if self.no_answer_accuracy is not None:
            scores.append(self.no_answer_accuracy)
            weights.append(0.5)

        if not weights:
            return None
        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)


# ---------------------------------------------------------------------------
# Combined evaluation result
# ---------------------------------------------------------------------------
@dataclass
class PipelineDiagnostic:
    """Per-step diagnostic trace — tracks what happened at each pipeline stage.

    Each step records: what was expected (from golden QuerySpec), what actually
    happened, and whether it matched. This enables intermediate state comparison
    for evaluation depth.
    """
    step_name: str                  # "query_understanding", "entity_resolution", etc.
    expected: dict[str, Any] = field(default_factory=dict)  # from golden QuerySpec
    actual: dict[str, Any] = field(default_factory=dict)    # from actual pipeline
    matched: bool = False           # did expected match actual?
    detail: str = ""
    duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step_name": self.step_name,
            "matched": self.matched,
        }
        if self.expected:
            d["expected"] = self.expected
        if self.actual:
            d["actual"] = self.actual
        if self.detail:
            d["detail"] = self.detail
        if self.duration_ms:
            d["duration_ms"] = self.duration_ms
        if self.error:
            d["error"] = self.error
        return d


def compare_query_specs(expected: dict | None, actual: dict | None) -> list[PipelineDiagnostic]:
    """Compare expected (golden) QuerySpec against actual QuerySpec from pipeline.

    Returns a list of PipelineDiagnostic objects, one per compared field.
    """
    diagnostics: list[PipelineDiagnostic] = []
    if not expected or not actual:
        return diagnostics

    field_comparisons = [
        ("operation", "operation"),
        ("scope", "scope"),
        ("entity_type", "entity_type"),
        ("entity_name", "entity_name"),
        ("property", "property"),
        ("operator", "operator"),
    ]

    for golden_key, actual_key in field_comparisons:
        expected_val = expected.get(golden_key)
        actual_val = actual.get(actual_key)
        matched = expected_val == actual_val
        diagnostics.append(PipelineDiagnostic(
            step_name=f"query_spec_{golden_key}",
            expected={golden_key: expected_val},
            actual={actual_key: actual_val},
            matched=matched,
            detail="" if matched else f"Expected {golden_key}={expected_val}, got {actual_val}",
        ))

    return diagnostics


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single sample — system + RAGAS + diagnostics."""
    sample_id: str
    question: str
    # System metrics (deterministic)
    system_metrics: SystemMetrics = field(default_factory=SystemMetrics)
    # RAGAS metrics (LLM-based)
    ragas_faithfulness: float | None = None
    ragas_faithfulness_status: str = "NOT_EVALUATED"
    ragas_answer_relevancy: float | None = None
    ragas_answer_relevancy_status: str = "NOT_EVALUATED"
    ragas_context_precision: float | None = None
    ragas_context_precision_status: str = "NOT_EVALUATED"
    ragas_context_recall: float | None = None
    ragas_context_recall_status: str = "NOT_EVALUATED"
    # Diagnostics
    root_cause: RootCause = field(default_factory=RootCause)
    pipeline_trace: PipelineTrace | None = None
    # H12: Per-step diagnostics from QuerySpec comparison
    pipeline_diagnostics: list[PipelineDiagnostic] = field(default_factory=list)
    # Metadata
    evaluation_model: str = ""
    evaluation_error: str | None = None
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "question": self.question,
            "system_metrics": self.system_metrics.to_dict(),
            "system_overall_score": self.system_metrics.overall_score(),
            "ragas": {
                "faithfulness": self.ragas_faithfulness,
                "faithfulness_status": self.ragas_faithfulness_status,
                "answer_relevancy": self.ragas_answer_relevancy,
                "answer_relevancy_status": self.ragas_answer_relevancy_status,
                "context_precision": self.ragas_context_precision,
                "context_precision_status": self.ragas_context_precision_status,
                "context_recall": self.ragas_context_recall,
                "context_recall_status": self.ragas_context_recall_status,
            },
            "root_cause": self.root_cause.to_dict(),
            "pipeline_trace": self.pipeline_trace.to_dict() if self.pipeline_trace else None,
            "pipeline_diagnostics": [d.to_dict() for d in self.pipeline_diagnostics],
            "evaluation_model": self.evaluation_model,
            "evaluation_error": self.evaluation_error,
            "timestamp": self.timestamp,
        }


@dataclass
class EvaluationReport:
    """Aggregate report across multiple evaluation samples."""
    name: str
    timestamp: str
    dataset_name: str
    dataset_version: str
    total_samples: int
    results: list[EvaluationResult] = field(default_factory=list)

    def aggregate_system_metrics(self) -> SystemMetrics:
        """Average system metrics across all results (only COMPLETED metrics)."""
        if not self.results:
            return SystemMetrics()
        n = len(self.results)
        agg = SystemMetrics()
        metric_names = [
            "entity_accuracy", "entity_precision", "entity_recall",
            "retrieval_top_k_recall", "context_coverage",
            "citation_correctness", "citation_completeness",
            "intent_accuracy", "no_answer_accuracy", "metadata_field_accuracy",
        ]
        for name in metric_names:
            values = [
                getattr(r.system_metrics, name)
                for r in self.results
                if getattr(r.system_metrics, name) is not None
            ]
            if values:
                agg.set_metric(name, sum(values) / len(values), MetricStatus.COMPLETED)
        # Boolean metric: retrieval_hit
        hit_values = [
            r.system_metrics.retrieval_hit
            for r in self.results
            if r.system_metrics.retrieval_hit is not None
        ]
        if hit_values:
            agg.set_metric("retrieval_hit", sum(1 for v in hit_values if v) / len(hit_values), MetricStatus.COMPLETED)
        return agg

    def aggregate_ragas(self) -> dict[str, float | None]:
        """Average RAGAS metrics across results that have scores."""
        metrics: dict[str, list[float]] = {
            "faithfulness": [], "answer_relevancy": [],
            "context_precision": [], "context_recall": [],
        }
        for r in self.results:
            if r.ragas_faithfulness is not None:
                metrics["faithfulness"].append(r.ragas_faithfulness)
            if r.ragas_answer_relevancy is not None:
                metrics["answer_relevancy"].append(r.ragas_answer_relevancy)
            if r.ragas_context_precision is not None:
                metrics["context_precision"].append(r.ragas_context_precision)
            if r.ragas_context_recall is not None:
                metrics["context_recall"].append(r.ragas_context_recall)
        return {
            k: sum(v) / len(v) if v else None
            for k, v in metrics.items()
        }

    def failure_distribution(self) -> dict[str, int]:
        """Count failures by layer."""
        dist: dict[str, int] = {}
        for r in self.results:
            layer = r.root_cause.primary_layer.value
            dist[layer] = dist.get(layer, 0) + 1
        return dist

    def to_dict(self) -> dict[str, Any]:
        agg_sys = self.aggregate_system_metrics()
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "total_samples": self.total_samples,
            "aggregate_system_metrics": agg_sys.to_dict(),
            "aggregate_ragas": self.aggregate_ragas(),
            "failure_distribution": self.failure_distribution(),
            "system_overall_score": agg_sys.overall_score(),
            "results": [r.to_dict() for r in self.results],
        }
