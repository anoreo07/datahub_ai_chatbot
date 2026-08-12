"""Semantic expansion of a user question into synonymous vocabulary.

Users may ask about a business concept with a word that does not literally match
an entity name (e.g. "doanh thu" vs. dataset ``fact_revenue``, or "gross revenue"
vs ``fact_revenue_gross``). This module maps a normalized question through a
synonym table to produce additional candidate terms the entity resolver /
search can use, plus the shared expansion terms emitted for retrieval.

This is deterministic and cheap: it never calls an LLM, so it slots into the
fast path and is safe for both mock and real runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from retrieval.fuzzy import normalize

log = structlog.get_logger()

# Vietnamese <-> English domain synonyms. Keys and values are ASCII-folded.
SYNONYMS: dict[str, list[str]] = {
    "doanh thu": ["revenue", "gross revenue", "net revenue", "fact_revenue"],
    "revenue": ["doanh thu", "gross revenue", "net revenue", "fact_revenue"],
    "loi nhuan": ["profit", "fact_profit", "margin"],
    "profit": ["loi nhuan", "fact_profit", "margin"],
    "gia von": ["cogs", "cost of goods sold", "fact_cogs"],
    "ton kho": ["inventory", "fact_inventory", "stock"],
    "dat hang": ["order", "fact_order", "sales order"],
    "order": ["dat hang", "fact_order", "sales order"],
    "hoa don": ["invoice", "fact_invoice", "billing"],
    "invoice": ["hoa don", "fact_invoice", "billing"],
    "san xuat": ["production", "assembly", "manufacturing", "fact_production"],
    "production": ["san xuat", "assembly", "manufacturing", "fact_production"],
    "chat luong": ["quality", "fact_quality", "oee", "quality control"],
    "quality": ["chat luong", "fact_quality", "oee"],
    "nhan su": ["employee", "hr", "fact_employee", "fact_hr"],
    "employee": ["nhan su", "hr", "fact_employee", "fact_hr"],
    "tat ca": ["all"],
    "nguoi dung": ["customer", "fact_customer"],
    "customer": ["nguoi dung", "fact_customer"],
}

# Longer, more specific keys must be tried first so "doanh thu" is not split.


@dataclass
class ExpansionResult:
    terms: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"terms": self.terms, "matched": self.matched}


def expand(question: str) -> ExpansionResult:
    """Expand ``question`` into candidate search terms using the synonym table.

    For each synonym key appearing verbatim in the (normalized) question, all its
    target terms are added. The question itself is always included first.
    """
    q = normalize(question)
    result = ExpansionResult()
    result.terms.append(question)
    if not q:
        return result

    for key in sorted(SYNONYMS, key=lambda k: -len(k.split())):
        keys = SYNONYMS[key]
        if key in q:
            result.matched.append(key)
            for term in keys:
                if term not in result.terms:
                    result.terms.append(term)
        # Any synonym alias present in the question pulls in the whole cluster.
        for alias in keys:
            if alias != key and alias in q:
                result.matched.append(alias)
                for term in keys:
                    if term not in result.terms:
                        result.terms.append(term)
                break

    log.debug("semantic_expansion", question=question[:80], terms=result.terms[:8])
    return result


class SemanticExpander:
    """Wrapper used by the retrieval layer to get additional resolver queries."""

    def __init__(self) -> None:
        pass

    def expand(self, question: str) -> ExpansionResult:
        return expand(question)
