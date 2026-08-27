"""Regression framework — before/after comparison for evaluation runs.

Tracks evaluation results over time, detects regressions, and generates
comparison reports between baseline and current runs.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

import structlog

from evaluation.models import EvaluationReport, EvaluationResult, SystemMetrics

log = structlog.get_logger(__name__)


def compare_reports(
    baseline: EvaluationReport,
    current: EvaluationReport,
    threshold: float = 0.05,
) -> dict[str, Any]:
    """Compare two evaluation reports and identify regressions/improvements.

    Args:
        baseline: The reference baseline report.
        current: The current evaluation report.
        threshold: Minimum change to flag as regression/improvement.

    Returns:
        Comparison dict with metrics, regressions, improvements, and verdict.
    """
    base_sys = baseline.aggregate_system_metrics()
    curr_sys = current.aggregate_system_metrics()
    base_ragas = baseline.aggregate_ragas()
    curr_ragas = current.aggregate_ragas()

    # System metric deltas
    sys_metrics = {}
    for metric_name in [
        "entity_accuracy", "entity_precision", "entity_recall",
        "retrieval_hit", "retrieval_top_k_recall", "context_coverage",
        "citation_correctness", "citation_completeness",
        "intent_accuracy", "no_answer_accuracy", "metadata_field_accuracy",
    ]:
        base_val = getattr(base_sys, metric_name, None)
        curr_val = getattr(curr_sys, metric_name, None)
        # Convert bool to float for comparison
        if isinstance(base_val, bool):
            base_val = 1.0 if base_val else 0.0
        if isinstance(curr_val, bool):
            curr_val = 1.0 if curr_val else 0.0
        if base_val is not None and curr_val is not None:
            delta = curr_val - base_val
            sys_metrics[metric_name] = {
                "baseline": round(base_val, 4),
                "current": round(curr_val, 4),
                "delta": round(delta, 4),
                "regression": delta < -threshold,
                "improvement": delta > threshold,
            }
        else:
            # One or both not evaluated — cannot compare
            sys_metrics[metric_name] = {
                "baseline": base_val,
                "current": curr_val,
                "delta": None,
                "regression": False,
                "improvement": False,
                "note": "Cannot compare: one or both metrics not evaluated",
            }

    # RAGAS deltas
    ragas_metrics = {}
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        base_val = base_ragas.get(metric_name)
        curr_val = curr_ragas.get(metric_name)
        if base_val is not None and curr_val is not None:
            delta = curr_val - base_val
            ragas_metrics[metric_name] = {
                "baseline": round(base_val, 4),
                "current": round(curr_val, 4),
                "delta": round(delta, 4),
                "regression": delta < -threshold,
                "improvement": delta > threshold,
            }

    # Overall score
    base_overall = base_sys.overall_score()
    curr_overall = curr_sys.overall_score()
    if base_overall is not None and curr_overall is not None:
        overall_delta = curr_overall - base_overall
    else:
        overall_delta = None

    # Failure distribution comparison
    base_failures = baseline.failure_distribution()
    curr_failures = current.failure_distribution()

    # Identify regressions
    regressions = [
        name for name, info in sys_metrics.items() if info["regression"]
    ] + [
        name for name, info in ragas_metrics.items() if info["regression"]
    ]

    improvements = [
        name for name, info in sys_metrics.items() if info["improvement"]
    ] + [
        name for name, info in ragas_metrics.items() if info["improvement"]
    ]

    # Verdict
    if not regressions:
        verdict = "PASS"
    elif len(regressions) <= 2 and all(
        (sys_metrics.get(r, {}).get("delta") or 0) > -0.1 for r in regressions
    ):
        verdict = "PASS_WITH_MINOR_REGRESSIONS"
    else:
        verdict = "FAIL"

    return {
        "baseline_name": baseline.name,
        "baseline_timestamp": baseline.timestamp,
        "current_name": current.name,
        "current_timestamp": current.timestamp,
        "system_metrics": sys_metrics,
        "ragas_metrics": ragas_metrics,
        "overall_score": {
            "baseline": round(base_overall, 4) if base_overall is not None else None,
            "current": round(curr_overall, 4) if curr_overall is not None else None,
            "delta": round(overall_delta, 4) if overall_delta is not None else None,
        },
        "failure_distribution": {
            "baseline": base_failures,
            "current": curr_failures,
        },
        "regressions": regressions,
        "improvements": improvements,
        "verdict": verdict,
    }


def save_evaluation_run(report: EvaluationReport, path: str | Path) -> None:
    """Save an evaluation report to disk for future comparison."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    log.info("evaluation_run_saved", path=str(path), samples=report.total_samples)


def load_evaluation_run(path: str | Path) -> EvaluationReport:
    """Load a saved evaluation report from disk."""
    from evaluation.models import FailureLayer, FailureReason, RootCause
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for r in data.get("results", []):
        sys_data = r.get("system_metrics", {})
        rc_data = r.get("root_cause", {})
        results.append(EvaluationResult(
            sample_id=r.get("sample_id", ""),
            question=r.get("question", ""),
            system_metrics=SystemMetrics(**sys_data),
            ragas_faithfulness=r.get("ragas", {}).get("faithfulness"),
            ragas_faithfulness_status=r.get("ragas", {}).get("faithfulness_status", "NOT_EVALUATED"),
            ragas_answer_relevancy=r.get("ragas", {}).get("answer_relevancy"),
            ragas_answer_relevancy_status=r.get("ragas", {}).get("answer_relevancy_status", "NOT_EVALUATED"),
            ragas_context_precision=r.get("ragas", {}).get("context_precision"),
            ragas_context_precision_status=r.get("ragas", {}).get("context_precision_status", "NOT_EVALUATED"),
            ragas_context_recall=r.get("ragas", {}).get("context_recall"),
            ragas_context_recall_status=r.get("ragas", {}).get("context_recall_status", "NOT_EVALUATED"),
            root_cause=RootCause(
                primary_layer=FailureLayer(rc_data.get("primary_layer", "UNKNOWN")),
                primary_reason=FailureReason(rc_data.get("primary_reason", "none")),
                secondary_layer=FailureLayer(rc_data["secondary_layer"]) if rc_data.get("secondary_layer") else None,
                secondary_reason=FailureReason(rc_data["secondary_reason"]) if rc_data.get("secondary_reason") else None,
                detail=rc_data.get("detail", ""),
                confidence=rc_data.get("confidence", 0.0),
            ),
            evaluation_model=r.get("evaluation_model", ""),
            evaluation_error=r.get("evaluation_error"),
            timestamp=r.get("timestamp", ""),
        ))

    return EvaluationReport(
        name=data.get("name", ""),
        timestamp=data.get("timestamp", ""),
        dataset_name=data.get("dataset_name", ""),
        dataset_version=data.get("dataset_version", ""),
        total_samples=data.get("total_samples", 0),
        results=results,
    )


def find_regressions_across_runs(
    runs_dir: str | Path,
) -> list[dict[str, Any]]:
    """Scan a directory of evaluation run files and find regressions between consecutive runs."""
    runs_dir = Path(runs_dir)
    run_files = sorted(runs_dir.glob("eval_run_*.json"))

    if len(run_files) < 2:
        return []

    regressions = []
    for i in range(1, len(run_files)):
        baseline = load_evaluation_run(run_files[i - 1])
        current = load_evaluation_run(run_files[i])
        comparison = compare_reports(baseline, current)
        if comparison["regressions"]:
            regressions.append({
                "baseline_file": str(run_files[i - 1]),
                "current_file": str(run_files[i]),
                "comparison": comparison,
            })

    return regressions
