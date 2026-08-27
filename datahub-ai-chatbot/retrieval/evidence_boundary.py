"""Evidence Boundary — structured evidence claims with status tracking.

Root causes addressed:
  RC-E1: No distinction between MISSING (data doesn't exist), UNKNOWN (not checked),
         NOT_RETRIEVED (exists but not fetched), NOT_AUTHORIZED (exists but restricted),
         and PRESENT (successfully retrieved).
  RC-E2: Negative claims ("không có owner") not explicitly handled — relying on LLM
         interpretation instead of structured evidence.
  RC-E3: Evidence is per-turn, not per-claim — can't trace which claim came from
         which retrieval step.

Usage:
  evidence_claim = EvidenceClaim(
      entity_name="dim_warehouse",
      entity_urn="urn:li:dataset:dim_warehouse",
      property="owner",
      status=EvidenceStatus.MISSING,
      source="schema-metadata",
  )
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EvidenceStatus(StrEnum):
    """Status of an evidence claim — tracks data availability."""
    PRESENT = "PRESENT"             # Successfully retrieved
    MISSING = "MISSING"             # Data doesn't exist (confirmed absent)
    UNKNOWN = "UNKNOWN"             # Not checked yet
    NOT_RETRIEVED = "NOT_RETRIEVED" # Exists but not fetched (e.g. API timeout)
    NOT_AUTHORIZED = "NOT_AUTHORIZED"  # Exists but user lacks access
    NOT_AVAILABLE = "NOT_AVAILABLE" # System-level unavailability


@dataclass
class EvidenceClaim:
    """A structured evidence claim with boundary tracking.

    Each claim represents one piece of evidence (e.g. "dim_warehouse has owner X")
    and tracks whether it was actually retrieved, confirmed absent, or unknown.
    """
    entity_name: str
    entity_urn: str | None = None
    prop: str = ""                 # "owner", "domain", "schema", "lineage", etc.
    status: EvidenceStatus = EvidenceStatus.UNKNOWN
    value: Any = None              # The actual value if PRESENT
    source: str = ""               # "schema-metadata", "lineage-api", "evidence-store"
    citation_id: str | None = None  # E1, E2, ...
    is_negative: bool = False      # True for "không có X" claims

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "entity_name": self.entity_name,
            "property": self.prop,
            "status": self.status.value,
            "is_negative": self.is_negative,
        }
        if self.entity_urn:
            d["entity_urn"] = self.entity_urn
        if self.value is not None:
            d["value"] = self.value
        if self.source:
            d["source"] = self.source
        if self.citation_id:
            d["citation_id"] = self.citation_id
        return d

    @property
    def is_answerable(self) -> bool:
        """Can we answer the question from this claim?"""
        return self.status == EvidenceStatus.PRESENT and self.value is not None

    @property
    def is_refusable(self) -> bool:
        """Should we refuse to answer based on this claim?"""
        return self.status in (
            EvidenceStatus.MISSING,
            EvidenceStatus.NOT_AUTHORIZED,
            EvidenceStatus.NOT_AVAILABLE,
        )

    @property
    def is_incomplete(self) -> bool:
        """Is the evidence incomplete (need more data)?"""
        return self.status in (
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.NOT_RETRIEVED,
        )


def build_evidence_claims(
    evidence_records: list[dict],
    query_spec: dict | None = None,
) -> list[EvidenceClaim]:
    """Convert evidence records from ConversationMemory to structured claims.

    Each evidence record becomes an EvidenceClaim with status inferred from
    the record's content and metadata.
    """
    claims: list[EvidenceClaim] = []
    for rec in evidence_records:
        entity_name = rec.get("entity_name", "")
        if not entity_name:
            continue
        structured = rec.get("structured") or {}

        # Infer status from the record content
        if structured:
            status = EvidenceStatus.PRESENT
        elif rec.get("snippet"):
            status = EvidenceStatus.PRESENT
        else:
            status = EvidenceStatus.UNKNOWN

        # Determine the property being queried
        property_name = rec.get("kind", "")

        # Check for negative claims (e.g. "không có owner")
        is_negative = False
        if query_spec:
            q_prop = query_spec.get("property", "")
            q_op = query_spec.get("operator", "GET")
            if q_prop and property_name and q_prop == property_name:
                if q_op == "MISSING" or q_op == "NOT_EQUALS":
                    is_negative = True

        claim = EvidenceClaim(
            entity_name=entity_name,
            entity_urn=rec.get("entity_urn"),
            prop=property_name,
            status=status,
            value=structured if structured else None,
            source=rec.get("source", "retrieval"),
            citation_id=rec.get("evidence_id"),
            is_negative=is_negative,
        )
        claims.append(claim)
    return claims


def evaluate_evidence_boundary(
    claims: list[EvidenceClaim],
    query_spec: dict | None = None,
) -> dict[str, Any]:
    """Evaluate evidence boundary and determine if we can answer, refuse, or need more data.

    Returns:
        {
            "can_answer": bool,
            "should_refuse": bool,
            "needs_clarification": bool,
            "coverage": float,  # fraction of required evidence that is PRESENT
            "missing_properties": list[str],
            "claims": list[dict],  # all claims as dicts
        }
    """
    if not claims:
        return {
            "can_answer": False,
            "should_refuse": True,
            "needs_clarification": False,
            "coverage": 0.0,
            "missing_properties": [],
            "claims": [],
        }

    present = [c for c in claims if c.status == EvidenceStatus.PRESENT and not c.is_negative]
    missing = [c for c in claims if c.status == EvidenceStatus.MISSING]
    unauthorized = [c for c in claims if c.status == EvidenceStatus.NOT_AUTHORIZED]
    unknown = [c for c in claims if c.status in (EvidenceStatus.UNKNOWN, EvidenceStatus.NOT_RETRIEVED)]
    negative = [c for c in claims if c.is_negative]

    total = len(claims)
    coverage = len(present) / total if total > 0 else 0.0

    # Missing properties that are required but not found
    missing_properties = [
        c.prop for c in missing if c.prop
    ]

    # Should refuse if:
    # - All claims are MISSING or NOT_AUTHORIZED
    # - The query requires specific data that is confirmed absent
    has_negative_missing = (
        query_spec is not None
        and query_spec.get("operator") == "MISSING"
        and len(negative) > 0
    )
    should_refuse = (
        (len(missing) + len(unauthorized)) == total
        or has_negative_missing
    )

    # Can answer if we have at least one PRESENT claim with a value
    can_answer = len(present) > 0 and not should_refuse

    # Needs clarification if we have unknown claims
    needs_clarification = len(unknown) > 0 and not can_answer

    return {
        "can_answer": can_answer,
        "should_refuse": should_refuse,
        "needs_clarification": needs_clarification,
        "coverage": coverage,
        "missing_properties": missing_properties,
        "claims": [c.to_dict() for c in claims],
    }
