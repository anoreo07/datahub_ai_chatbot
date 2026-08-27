"""Tests for H10: Evidence Boundary — structured claims with status tracking.

Covers:
  - EvidenceClaim model: status, is_answerable, is_refusable, is_incomplete
  - EvidenceStatus enum values
  - build_evidence_claims(): converts evidence records to claims
  - evaluate_evidence_boundary(): can_answer, should_refuse, coverage
"""

from __future__ import annotations

from retrieval.evidence_boundary import (
    EvidenceClaim,
    EvidenceStatus,
    build_evidence_claims,
    evaluate_evidence_boundary,
)

# ---------------------------------------------------------------------------
# EvidenceStatus enum
# ---------------------------------------------------------------------------

class TestEvidenceStatus:
    def test_all_statuses(self):
        expected = {"PRESENT", "MISSING", "UNKNOWN", "NOT_RETRIEVED", "NOT_AUTHORIZED", "NOT_AVAILABLE"}
        actual = {s.value for s in EvidenceStatus}
        assert actual == expected


# ---------------------------------------------------------------------------
# EvidenceClaim model
# ---------------------------------------------------------------------------

class TestEvidenceClaim:
    def test_present_claim(self):
        claim = EvidenceClaim(
            entity_name="dim_warehouse",
            entity_urn="urn:li:dataset:dim_warehouse",
            prop="owner",
            status=EvidenceStatus.PRESENT,
            value="admin@example.com",
            source="schema-metadata",
            citation_id="E1",
        )
        assert claim.is_answerable is True
        assert claim.is_refusable is False
        assert claim.is_incomplete is False
        assert claim.to_dict()["status"] == "PRESENT"

    def test_missing_claim(self):
        claim = EvidenceClaim(
            entity_name="dim_warehouse",
            prop="owner",
            status=EvidenceStatus.MISSING,
            is_negative=True,
        )
        assert claim.is_answerable is False
        assert claim.is_refusable is True
        assert claim.is_incomplete is False

    def test_unknown_claim(self):
        claim = EvidenceClaim(
            entity_name="dim_warehouse",
            prop="lineage",
            status=EvidenceStatus.UNKNOWN,
        )
        assert claim.is_answerable is False
        assert claim.is_refusable is False
        assert claim.is_incomplete is True

    def test_not_retrieved_claim(self):
        claim = EvidenceClaim(
            entity_name="dim_warehouse",
            prop="schema",
            status=EvidenceStatus.NOT_RETRIEVED,
        )
        assert claim.is_answerable is False
        assert claim.is_refusable is False
        assert claim.is_incomplete is True

    def test_not_authorized_claim(self):
        claim = EvidenceClaim(
            entity_name="dim_warehouse",
            prop="owners",
            status=EvidenceStatus.NOT_AUTHORIZED,
        )
        assert claim.is_answerable is False
        assert claim.is_refusable is True
        assert claim.is_incomplete is False

    def test_negative_claim(self):
        claim = EvidenceClaim(
            entity_name="dim_warehouse",
            prop="owner",
            status=EvidenceStatus.PRESENT,
            value=None,
            is_negative=True,
        )
        assert claim.is_negative is True
        assert claim.to_dict()["is_negative"] is True


# ---------------------------------------------------------------------------
# build_evidence_claims
# ---------------------------------------------------------------------------

class TestBuildEvidenceClaims:
    def test_empty_records(self):
        assert build_evidence_claims([]) == []

    def test_record_with_structured_data(self):
        records = [{
            "entity_name": "dim_warehouse",
            "entity_urn": "urn:li:dataset:dim_warehouse",
            "kind": "owner",
            "structured": {"owners": ["admin"]},
            "source": "schema-metadata",
            "evidence_id": "E1",
        }]
        claims = build_evidence_claims(records)
        assert len(claims) == 1
        assert claims[0].status == EvidenceStatus.PRESENT
        assert claims[0].prop == "owner"
        assert claims[0].citation_id == "E1"

    def test_record_without_structured_data(self):
        records = [{
            "entity_name": "dim_warehouse",
            "kind": "lineage",
            "structured": None,
        }]
        claims = build_evidence_claims(records)
        assert len(claims) == 1
        assert claims[0].status == EvidenceStatus.UNKNOWN

    def test_negative_query_spec_marks_negative(self):
        records = [{
            "entity_name": "dim_warehouse",
            "kind": "owner",
            "structured": None,
        }]
        query_spec = {"property": "owner", "operator": "MISSING"}
        claims = build_evidence_claims(records, query_spec=query_spec)
        assert len(claims) == 1
        assert claims[0].is_negative is True

    def test_skips_empty_entity_name(self):
        records = [{"entity_name": "", "kind": "owner"}]
        assert build_evidence_claims(records) == []


# ---------------------------------------------------------------------------
# evaluate_evidence_boundary
# ---------------------------------------------------------------------------

class TestEvaluateEvidenceBoundary:
    def test_all_present(self):
        claims = [
            EvidenceClaim(entity_name="X", prop="owner", status=EvidenceStatus.PRESENT, value="a"),
            EvidenceClaim(entity_name="X", prop="domain", status=EvidenceStatus.PRESENT, value="b"),
        ]
        result = evaluate_evidence_boundary(claims)
        assert result["can_answer"] is True
        assert result["should_refuse"] is False
        assert result["coverage"] == 1.0

    def test_all_missing_refuses(self):
        claims = [
            EvidenceClaim(entity_name="X", prop="owner", status=EvidenceStatus.MISSING),
            EvidenceClaim(entity_name="X", prop="domain", status=EvidenceStatus.MISSING),
        ]
        result = evaluate_evidence_boundary(claims)
        assert result["can_answer"] is False
        assert result["should_refuse"] is True

    def test_mixed_present_and_unknown(self):
        claims = [
            EvidenceClaim(entity_name="X", prop="owner", status=EvidenceStatus.PRESENT, value="a"),
            EvidenceClaim(entity_name="X", prop="lineage", status=EvidenceStatus.UNKNOWN),
        ]
        result = evaluate_evidence_boundary(claims)
        assert result["can_answer"] is True
        assert result["coverage"] == 0.5

    def test_empty_claims_refuses(self):
        result = evaluate_evidence_boundary([])
        assert result["can_answer"] is False
        assert result["should_refuse"] is True
        assert result["coverage"] == 0.0

    def test_not_authorized_refuses(self):
        claims = [
            EvidenceClaim(entity_name="X", prop="owners", status=EvidenceStatus.NOT_AUTHORIZED),
        ]
        result = evaluate_evidence_boundary(claims)
        assert result["should_refuse"] is True

    def test_missing_properties_listed(self):
        claims = [
            EvidenceClaim(entity_name="X", prop="owner", status=EvidenceStatus.MISSING),
            EvidenceClaim(entity_name="X", prop="domain", status=EvidenceStatus.PRESENT, value="SALES"),
        ]
        result = evaluate_evidence_boundary(claims)
        assert "owner" in result["missing_properties"]

    def test_negative_claim_with_missing_operator(self):
        claims = [
            EvidenceClaim(entity_name="X", prop="owner", status=EvidenceStatus.MISSING, is_negative=True),
        ]
        query_spec = {"property": "owner", "operator": "MISSING"}
        result = evaluate_evidence_boundary(claims, query_spec=query_spec)
        assert result["should_refuse"] is True
