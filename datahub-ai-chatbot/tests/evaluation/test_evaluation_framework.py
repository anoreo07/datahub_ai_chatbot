"""Tests for the comprehensive evaluation framework."""

from __future__ import annotations

import os
import tempfile

from evaluation.diagnostics import classify_from_ragas, classify_root_cause
from evaluation.models import (
    EvaluationReport,
    EvaluationResult,
    FailureLayer,
    FailureReason,
    PipelineStep,
    PipelineTrace,
    ReferenceDataset,
    ReferenceExpected,
    RootCause,
    SystemMetrics,
)
from evaluation.multi_turn import (
    ConversationScenario,
    ConversationTurn,
    MultiTurnResult,
)
from evaluation.reference_model import (
    create_reference_sample,
    load_reference_dataset,
    save_reference_dataset,
)
from evaluation.regression import compare_reports
from evaluation.system_metrics import compute_metrics_from_answer_only, compute_system_metrics


def _make_sys_metrics(values: dict) -> SystemMetrics:
    """Helper to create SystemMetrics with proper status tracking."""
    from evaluation.models import MetricStatus
    m = SystemMetrics()
    for name, val in values.items():
        if isinstance(val, bool):
            m.set_metric(name, val, MetricStatus.COMPLETED)
        else:
            m.set_metric(name, val, MetricStatus.COMPLETED)
    return m


# ---------------------------------------------------------------------------
# models.py tests
# ---------------------------------------------------------------------------

class TestRootCause:
    def test_to_dict(self):
        rc = RootCause(
            primary_layer=FailureLayer.ENTITY_RESOLUTION,
            primary_reason=FailureReason.ENTITY_NOT_FOUND,
            detail="test",
            confidence=0.9,
        )
        d = rc.to_dict()
        assert d["primary_layer"] == "ENTITY_RESOLUTION"
        assert d["primary_reason"] == "entity_not_found"
        assert d["confidence"] == 0.9

    def test_default(self):
        rc = RootCause()
        assert rc.primary_layer == FailureLayer.UNKNOWN
        assert rc.primary_reason == FailureReason.NONE


class TestPipelineTrace:
    def test_add_step(self):
        trace = PipelineTrace(trace_id="t1", question="test")
        step = PipelineStep(step_name="chat_pipeline", status="ok")
        trace.add_step(step)
        assert len(trace.steps) == 1
        assert trace.steps[0].step_name == "chat_pipeline"

    def test_to_dict(self):
        trace = PipelineTrace(trace_id="t1", question="test", intent_detected="SCHEMA_LOOKUP")
        d = trace.to_dict()
        assert d["trace_id"] == "t1"
        assert d["intent_detected"] == "SCHEMA_LOOKUP"


class TestSystemMetrics:
    def test_overall_score_empty(self):
        m = SystemMetrics()
        assert m.overall_score() is None  # No metrics evaluated = None

    def test_overall_score_with_values(self):
        m = SystemMetrics(
            entity_accuracy=1.0,
            retrieval_hit=True,
            context_coverage=0.8,
            citation_correctness=0.9,
            intent_accuracy=1.0,
        )
        score = m.overall_score()
        assert score is not None
        assert 0.5 < score <= 1.0

    def test_overall_score_includes_zero(self):
        """A metric with score=0 and status=COMPLETED IS included in overall score."""
        m = SystemMetrics(entity_accuracy=0.0, retrieval_hit=False)
        # entity_accuracy=0 is included, retrieval_hit=False counts as 0.0
        score = m.overall_score()
        assert score is not None
        assert score == 0.0  # Both metrics are 0

    def test_to_dict(self):
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", 0.5, MetricStatus.COMPLETED)
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] == 0.5
        assert d["entity_accuracy"]["status"] == "COMPLETED"

    def test_to_dict_not_evaluated(self):
        m = SystemMetrics()
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] is None
        assert d["entity_accuracy"]["status"] == "NOT_EVALUATED"

    def test_to_dict_with_reason(self):
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", 0.0, MetricStatus.COMPLETED, "Wrong entity resolved")
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] == 0.0
        assert d["entity_accuracy"]["status"] == "COMPLETED"
        assert d["entity_accuracy"]["reason"] == "Wrong entity resolved"


class TestReferenceSample:
    def test_create(self):
        sample = create_reference_sample(
            sample_id="S1",
            question="test question",
            entities=["urn:li:dataset:test"],
            intent="SCHEMA_LOOKUP",
        )
        assert sample.id == "S1"
        assert sample.expected.entities == ["urn:li:dataset:test"]

    def test_to_dict(self):
        sample = create_reference_sample(
            sample_id="S1",
            question="test",
            entities=["urn:li:dataset:test"],
        )
        d = sample.to_dict()
        assert d["id"] == "S1"
        assert "expected" in d
        assert "provenance" in d


class TestReferenceDataset:
    def test_to_dict(self):
        ds = ReferenceDataset(
            name="test",
            version="1.0",
            samples=[create_reference_sample("S1", "q1")],
        )
        d = ds.to_dict()
        assert d["sample_count"] == 1


# ---------------------------------------------------------------------------
# diagnostics.py tests
# ---------------------------------------------------------------------------

class TestDiagnostics:
    def _make_trace(self, **kwargs) -> PipelineTrace:
        defaults = {"trace_id": "t1", "question": "test"}
        defaults.update(kwargs)
        return PipelineTrace(**defaults)

    def test_passed_when_no_reference(self):
        trace = self._make_trace(intent_detected="SCHEMA_LOOKUP")
        rc = classify_root_cause(trace, None, SystemMetrics(), "answer", "high", ["ctx"])
        assert rc.primary_layer == FailureLayer.PASSED

    def test_entity_not_found(self):
        trace = self._make_trace(
            intent_detected="SCHEMA_LOOKUP",
            entity_candidates=[],
        )
        ref = ReferenceExpected(entities=["urn:li:dataset:missing"])
        rc = classify_root_cause(trace, ref, SystemMetrics(), "answer", "high", ["ctx"])
        assert rc.primary_layer == FailureLayer.ENTITY_RESOLUTION
        assert rc.primary_reason == FailureReason.ENTITY_NOT_FOUND

    def test_entity_wrong(self):
        trace = self._make_trace(
            intent_detected="SCHEMA_LOOKUP",
            entity_resolved_urn="urn:li:dataset:wrong",
            entity_candidates=["urn:li:dataset:wrong"],
        )
        ref = ReferenceExpected(entities=["urn:li:dataset:correct"])
        rc = classify_root_cause(trace, ref, SystemMetrics(), "answer", "high", ["ctx"])
        assert rc.primary_layer == FailureLayer.ENTITY_RESOLUTION
        assert rc.primary_reason == FailureReason.ENTITY_WRONG

    def test_no_results(self):
        trace = self._make_trace(
            intent_detected="SCHEMA_LOOKUP",
            retrieval_results_count=0,
        )
        ref = ReferenceExpected()  # No entity expectation, so retrieval layer fires
        rc = classify_root_cause(trace, ref, SystemMetrics(), "answer", "high", [])
        assert rc.primary_layer == FailureLayer.RETRIEVAL
        assert rc.primary_reason == FailureReason.NO_RESULTS

    def test_entity_not_found_plus_no_results(self):
        trace = self._make_trace(
            intent_detected="SCHEMA_LOOKUP",
            retrieval_results_count=0,
        )
        ref = ReferenceExpected(entities=["urn:li:dataset:test"])
        rc = classify_root_cause(trace, ref, SystemMetrics(), "answer", "high", [])
        # Entity resolution fires first (more fundamental), retrieval is secondary
        assert rc.primary_layer == FailureLayer.ENTITY_RESOLUTION
        assert rc.secondary_layer == FailureLayer.RETRIEVAL

    def test_incorrect_refusal(self):
        trace = self._make_trace(intent_detected="SCHEMA_LOOKUP")
        ref = ReferenceExpected(is_no_answer=True)
        rc = classify_root_cause(trace, ref, SystemMetrics(), "The answer is 42", "high", ["ctx"])
        assert rc.primary_layer == FailureLayer.GENERATION
        assert rc.primary_reason == FailureReason.REFUSAL_INCORRECT

    def test_correct_no_answer(self):
        trace = self._make_trace(intent_detected="ENTITY_EXISTS")
        ref = ReferenceExpected(is_no_answer=True)
        rc = classify_root_cause(
            trace, ref, SystemMetrics(),
            "Xin loi, khong tim thay entity nay", "low", [],
        )
        assert rc.primary_layer == FailureLayer.PASSED

    def test_classify_from_ragas_low_faithfulness(self):
        rc = classify_from_ragas(0.2, 0.8, 0.8, 0.8, False)
        assert rc.primary_layer == FailureLayer.GENERATION
        assert rc.primary_reason == FailureReason.FABRICATION

    def test_classify_from_ragas_all_good(self):
        rc = classify_from_ragas(0.9, 0.9, 0.9, 0.9, True)
        assert rc.primary_layer == FailureLayer.PASSED


# ---------------------------------------------------------------------------
# system_metrics.py tests
# ---------------------------------------------------------------------------

class TestSystemMetricsComputation:
    def test_entity_accuracy_match(self):
        trace = PipelineTrace(
            trace_id="t1", question="test",
            entity_resolved_urn="urn:li:dataset:correct",
            entity_candidates=["urn:li:dataset:correct"],
        )
        ref = ReferenceExpected(entities=["urn:li:dataset:correct"])
        m = compute_system_metrics(trace, ref, "answer", "high", ["ctx"], [])
        assert m.entity_accuracy == 1.0

    def test_entity_accuracy_mismatch(self):
        trace = PipelineTrace(
            trace_id="t1", question="test",
            entity_resolved_urn="urn:li:dataset:wrong",
            entity_candidates=["urn:li:dataset:wrong"],
        )
        ref = ReferenceExpected(entities=["urn:li:dataset:correct"])
        m = compute_system_metrics(trace, ref, "answer", "high", ["ctx"], [])
        assert m.entity_accuracy == 0.0

    def test_no_reference(self):
        trace = PipelineTrace(trace_id="t1", question="test")
        m = compute_system_metrics(trace, None, "answer", "high", [], [])
        # No reference = all metrics NOT_EVALUATED
        assert m.entity_accuracy is None
        assert m.get_metric_status("entity_accuracy") == "NOT_EVALUATED"

    def test_retrieval_hit(self):
        trace = PipelineTrace(
            trace_id="t1", question="test",
            retrieval_results_count=5,
        )
        ref = ReferenceExpected(entities=["urn:li:dataset:test"])
        m = compute_system_metrics(
            trace, ref, "answer", "high", ["ctx"],
            citation_urns=["urn:li:dataset:test"],
        )
        assert m.retrieval_hit is True

    def test_intent_accuracy(self):
        trace = PipelineTrace(
            trace_id="t1", question="test",
            intent_detected="SCHEMA_LOOKUP",
        )
        ref = ReferenceExpected(intent="SCHEMA_LOOKUP")
        m = compute_system_metrics(trace, ref, "answer", "high", ["ctx"], [])
        assert m.intent_accuracy == 1.0

    def test_no_answer_correct(self):
        trace = PipelineTrace(trace_id="t1", question="test")
        ref = ReferenceExpected(is_no_answer=True)
        m = compute_system_metrics(
            trace, ref, "Xin loi, khong tim thay", "low", [], [],
        )
        assert m.no_answer_accuracy == 1.0

    def test_answer_only_metrics(self):
        ref = ReferenceExpected(
            answer_contains=["revenue", "sales"],
            metadata_fields={"owner": "team_a"},
        )
        m = compute_metrics_from_answer_only(
            "The revenue and sales data shows team_a owns it",
            "high",
            ref,
        )
        # context_coverage is NOT_EVALUATED (no pipeline trace for keyword matching)
        assert m.context_coverage is None
        assert m.get_metric_status("context_coverage") == "NOT_EVALUATED"
        # metadata_field_accuracy IS computed from answer text
        assert m.metadata_field_accuracy is not None
        assert m.metadata_field_accuracy > 0.0


# ---------------------------------------------------------------------------
# reference_model.py tests
# ---------------------------------------------------------------------------

class TestReferenceModel:
    def test_save_and_load(self):
        ds = ReferenceDataset(
            name="test_ds",
            version="1.0",
            samples=[
                create_reference_sample("S1", "question 1", entities=["urn:li:dataset:x"]),
                create_reference_sample("S2", "question 2", is_no_answer=True),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "ref.json")
            save_reference_dataset(ds, path)
            loaded = load_reference_dataset(path)
            assert loaded.name == "test_ds"
            assert len(loaded.samples) == 2
            assert loaded.samples[0].expected.entities == ["urn:li:dataset:x"]
            assert loaded.samples[1].expected.is_no_answer is True


# ---------------------------------------------------------------------------
# regression.py tests
# ---------------------------------------------------------------------------

class TestRegression:
    def test_compare_reports_pass(self):
        r1 = EvaluationReport(
            name="baseline", timestamp="2026-01-01",
            dataset_name="test", dataset_version="1.0", total_samples=2,
            results=[
                EvaluationResult(
                    sample_id="S1", question="q1",
                    system_metrics=_make_sys_metrics({"entity_accuracy": 0.8, "retrieval_hit": True}),
                    ragas_faithfulness=0.9,
                ),
                EvaluationResult(
                    sample_id="S2", question="q2",
                    system_metrics=_make_sys_metrics({"entity_accuracy": 0.7, "retrieval_hit": True}),
                    ragas_faithfulness=0.85,
                ),
            ],
        )
        r2 = EvaluationReport(
            name="current", timestamp="2026-01-02",
            dataset_name="test", dataset_version="1.0", total_samples=2,
            results=[
                EvaluationResult(
                    sample_id="S1", question="q1",
                    system_metrics=_make_sys_metrics({"entity_accuracy": 0.85, "retrieval_hit": True}),
                    ragas_faithfulness=0.92,
                ),
                EvaluationResult(
                    sample_id="S2", question="q2",
                    system_metrics=_make_sys_metrics({"entity_accuracy": 0.75, "retrieval_hit": True}),
                    ragas_faithfulness=0.88,
                ),
            ],
        )
        comparison = compare_reports(r1, r2)
        assert comparison["verdict"] == "PASS"
        assert len(comparison["regressions"]) == 0

    def test_compare_reports_fail(self):
        r1 = EvaluationReport(
            name="baseline", timestamp="2026-01-01",
            dataset_name="test", dataset_version="1.0", total_samples=1,
            results=[
                EvaluationResult(
                    sample_id="S1", question="q1",
                    system_metrics=_make_sys_metrics({"entity_accuracy": 0.9, "retrieval_hit": True}),
                    ragas_faithfulness=0.9,
                ),
            ],
        )
        r2 = EvaluationReport(
            name="current", timestamp="2026-01-02",
            dataset_name="test", dataset_version="1.0", total_samples=1,
            results=[
                EvaluationResult(
                    sample_id="S1", question="q1",
                    system_metrics=_make_sys_metrics({"entity_accuracy": 0.4, "retrieval_hit": False}),
                    ragas_faithfulness=0.3,
                ),
            ],
        )
        comparison = compare_reports(r1, r2)
        assert comparison["verdict"] == "FAIL"
        assert len(comparison["regressions"]) > 0


# ---------------------------------------------------------------------------
# multi_turn.py tests
# ---------------------------------------------------------------------------

class TestMultiTurn:
    def test_conversation_scenario(self):
        scenario = ConversationScenario(
            scenario_id="SC1",
            name="Basic follow-up",
            turns=[
                ConversationTurn(
                    turn_id="T1",
                    question="Revenue dataset co nhung field gi?",
                    expected=ReferenceExpected(entities=["urn:li:dataset:revenue"]),
                ),
                ConversationTurn(
                    turn_id="T2",
                    question="No co bao nhieu field?",
                    expected=ReferenceExpected(),
                    expected_active_entity="urn:li:dataset:revenue",
                    depends_on_turn="T1",
                ),
            ],
        )
        assert len(scenario.turns) == 2
        assert scenario.turns[1].depends_on_turn == "T1"

    def test_turn_result_to_dict(self):
        tr = MultiTurnResult(
            scenario_id="SC1",
            scenario_name="Test",
            overall_success=True,
            conversation_flow_score=0.85,
            entity_tracking_accuracy=0.9,
            context_propagation_score=0.8,
        )
        d = tr.to_dict()
        assert d["overall_success"] is True
        assert d["entity_tracking_accuracy"] == 0.9


# ---------------------------------------------------------------------------
# Metric status contract tests (Tests A-H)
# ---------------------------------------------------------------------------

class TestMetricStatusContract:
    """Tests for the metric status contract: COMPLETED + score=0 vs NOT_EVALUATED vs FAILED."""

    def test_A_completed_score_zero(self):
        """TEST A: Metric evaluated, score = 0 -> UI/backend shows 0%."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", 0.0, MetricStatus.COMPLETED, "Wrong entity")
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] == 0.0
        assert d["entity_accuracy"]["status"] == "COMPLETED"
        assert d["entity_accuracy"]["reason"] == "Wrong entity"

    def test_B_completed_score_positive(self):
        """TEST B: Metric evaluated, score = 0.8 -> 80%."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", 0.8, MetricStatus.COMPLETED)
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] == 0.8
        assert d["entity_accuracy"]["status"] == "COMPLETED"

    def test_C_not_evaluated(self):
        """TEST C: Metric not evaluated -> N/A."""
        m = SystemMetrics()
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] is None
        assert d["entity_accuracy"]["status"] == "NOT_EVALUATED"

    def test_D_failed(self):
        """TEST D: Metric failed -> FAILED."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", None, MetricStatus.FAILED, "Embedding provider unavailable")
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] is None
        assert d["entity_accuracy"]["status"] == "FAILED"
        assert d["entity_accuracy"]["reason"] == "Embedding provider unavailable"

    def test_E_running(self):
        """TEST E: Metric running -> RUNNING."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", None, MetricStatus.RUNNING)
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] is None
        assert d["entity_accuracy"]["status"] == "RUNNING"

    def test_F_missing_from_old_record(self):
        """TEST F: Metric missing from old database record -> NOT_EVALUATED, not 0."""
        # Simulate old record: SystemMetrics() with defaults (all None)
        m = SystemMetrics()
        d = m.to_dict()
        for metric_name in ["entity_accuracy", "entity_precision", "entity_recall",
                            "retrieval_top_k_recall", "context_coverage",
                            "citation_correctness", "citation_completeness",
                            "intent_accuracy", "no_answer_accuracy", "metadata_field_accuracy"]:
            assert d[metric_name]["score"] is None, f"{metric_name} should be None, not 0"
            assert d[metric_name]["status"] == "NOT_EVALUATED", f"{metric_name} should be NOT_EVALUATED"

    def test_G_backend_returns_null(self):
        """TEST G: Backend returns null -> frontend should not coerce to 0."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", None, MetricStatus.NOT_EVALUATED)
        d = m.to_dict()
        # Verify null is preserved in JSON serialization
        import json
        serialized = json.dumps(d["entity_accuracy"])
        parsed = json.loads(serialized)
        assert parsed["score"] is None
        assert parsed["status"] == "NOT_EVALUATED"

    def test_H_status_with_null_score(self):
        """TEST H: Backend returns status + null score -> UI must keep N/A."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", None, MetricStatus.NOT_EVALUATED, "No reference data")
        d = m.to_dict()
        assert d["entity_accuracy"]["score"] is None
        assert d["entity_accuracy"]["status"] == "NOT_EVALUATED"
        # The reason is present
        assert d["entity_accuracy"]["reason"] == "No reference data"

    def test_overall_score_excludes_not_evaluated(self):
        """overall_score() only includes COMPLETED metrics."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", 0.8, MetricStatus.COMPLETED)
        m.set_metric("intent_accuracy", None, MetricStatus.NOT_EVALUATED)
        m.set_metric("context_coverage", 0.6, MetricStatus.COMPLETED)
        score = m.overall_score()
        assert score is not None
        # Only entity_accuracy (0.8) and context_coverage (0.6) are included
        assert 0.5 < score < 1.0

    def test_overall_score_includes_zero_completed(self):
        """overall_score() includes metrics with score=0 and status=COMPLETED."""
        from evaluation.models import MetricStatus
        m = SystemMetrics()
        m.set_metric("entity_accuracy", 0.0, MetricStatus.COMPLETED)
        m.set_metric("intent_accuracy", 1.0, MetricStatus.COMPLETED)
        score = m.overall_score()
        assert score is not None
        # entity_accuracy=0 and intent_accuracy=1 are both included
        assert score < 1.0  # The 0 pulls the average down
