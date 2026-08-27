"""Tests for H12: Evaluation Depth — PipelineDiagnostic and QuerySpec comparison.

Covers:
  - PipelineDiagnostic: dataclass fields, to_dict()
  - compare_query_specs(): field-by-field comparison
  - EvaluationResult: pipeline_diagnostics field
"""

from __future__ import annotations

from evaluation.models import (
    EvaluationResult,
    PipelineDiagnostic,
    compare_query_specs,
)

# ---------------------------------------------------------------------------
# PipelineDiagnostic
# ---------------------------------------------------------------------------

class TestPipelineDiagnostic:
    def test_basic_creation(self):
        diag = PipelineDiagnostic(
            step_name="query_understanding",
            expected={"operation": "GET", "scope": "ENTITY"},
            actual={"operation": "GET", "scope": "ENTITY"},
            matched=True,
        )
        assert diag.step_name == "query_understanding"
        assert diag.matched is True

    def test_to_dict_matched(self):
        diag = PipelineDiagnostic(
            step_name="entity_resolution",
            expected={"entity_name": "dim_warehouse"},
            actual={"entity_name": "dim_warehouse"},
            matched=True,
        )
        d = diag.to_dict()
        assert d["step_name"] == "entity_resolution"
        assert d["matched"] is True
        assert d["expected"] == {"entity_name": "dim_warehouse"}

    def test_to_dict_mismatched(self):
        diag = PipelineDiagnostic(
            step_name="query_spec_operation",
            expected={"operation": "LIST"},
            actual={"operation": "GET"},
            matched=False,
            detail="Expected operation=LIST, got GET",
        )
        d = diag.to_dict()
        assert d["matched"] is False
        assert "detail" in d
        assert "error" not in d

    def test_to_dict_with_error(self):
        diag = PipelineDiagnostic(
            step_name="retrieval",
            error="timeout",
        )
        d = diag.to_dict()
        assert d["error"] == "timeout"

    def test_to_dict_minimal(self):
        diag = PipelineDiagnostic(step_name="generation")
        d = diag.to_dict()
        assert d["step_name"] == "generation"
        assert "expected" not in d
        assert "actual" not in d


# ---------------------------------------------------------------------------
# compare_query_specs
# ---------------------------------------------------------------------------

class TestCompareQuerySpecs:
    def test_identical_specs(self):
        expected = {"operation": "GET", "scope": "ENTITY", "entity_name": "X", "property": "domain"}
        actual = {"operation": "GET", "scope": "ENTITY", "entity_name": "X", "property": "domain"}
        diags = compare_query_specs(expected, actual)
        assert len(diags) == 6  # one per field
        assert all(d.matched for d in diags)

    def test_operation_mismatch(self):
        expected = {"operation": "LIST", "scope": "GLOBAL"}
        actual = {"operation": "GET", "scope": "GLOBAL"}
        diags = compare_query_specs(expected, actual)
        op_diag = [d for d in diags if d.step_name == "query_spec_operation"][0]
        assert op_diag.matched is False
        assert "Expected" in op_diag.detail

    def test_entity_name_mismatch(self):
        expected = {"operation": "GET", "scope": "ENTITY", "entity_name": "dim_warehouse"}
        actual = {"operation": "GET", "scope": "ENTITY", "entity_name": "dim_inventory"}
        diags = compare_query_specs(expected, actual)
        entity_diag = [d for d in diags if d.step_name == "query_spec_entity_name"][0]
        assert entity_diag.matched is False

    def test_property_mismatch(self):
        expected = {"operation": "GET", "property": "owner"}
        actual = {"operation": "GET", "property": "domain"}
        diags = compare_query_specs(expected, actual)
        prop_diag = [d for d in diags if d.step_name == "query_spec_property"][0]
        assert prop_diag.matched is False

    def test_none_expected(self):
        assert compare_query_specs(None, {"operation": "GET"}) == []

    def test_none_actual(self):
        assert compare_query_specs({"operation": "GET"}, None) == []

    def test_both_none(self):
        assert compare_query_specs(None, None) == []

    def test_partial_fields(self):
        expected = {"operation": "GET"}
        actual = {"operation": "GET", "scope": "ENTITY", "entity_name": "X"}
        diags = compare_query_specs(expected, actual)
        # Only operation is compared (the only common key in field_comparisons)
        assert len(diags) >= 1
        op_diag = [d for d in diags if d.step_name == "query_spec_operation"][0]
        assert op_diag.matched is True


# ---------------------------------------------------------------------------
# EvaluationResult with pipeline_diagnostics
# ---------------------------------------------------------------------------

class TestEvaluationResultDiagnostics:
    def test_default_empty_diagnostics(self):
        result = EvaluationResult(sample_id="S1", question="test?")
        assert result.pipeline_diagnostics == []

    def test_diagnostics_in_to_dict(self):
        diag = PipelineDiagnostic(
            step_name="query_spec_operation",
            expected={"operation": "GET"},
            actual={"operation": "LIST"},
            matched=False,
        )
        result = EvaluationResult(
            sample_id="S1",
            question="test?",
            pipeline_diagnostics=[diag],
        )
        d = result.to_dict()
        assert len(d["pipeline_diagnostics"]) == 1
        assert d["pipeline_diagnostics"][0]["matched"] is False

    def test_empty_diagnostics_in_to_dict(self):
        result = EvaluationResult(sample_id="S1", question="test?")
        d = result.to_dict()
        assert d["pipeline_diagnostics"] == []
