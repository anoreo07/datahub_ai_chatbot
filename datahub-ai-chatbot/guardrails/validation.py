"""Output validation guardrails.

Verifies that generated answers are grounded in the retrieved metadata before
they are returned to the user. Strips unbacked URNs, masks leaked secrets, and
downgrades confidence when the answer is not supported by evidence.
"""

import re
from collections.abc import Sequence

import structlog

from retrieval.context_builder import ContextDocument
from retrieval.hybrid_search import SearchResult

log = structlog.get_logger()

NO_EVIDENCE_RESPONSE = "I couldn't find this information in the available DataHub metadata."

# DataHub URNs look like:
#   urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)
#   urn:li:glossaryTerm:NetRevenue
#   urn:li:dashboard:MonthlyRevenue
_URN_RE = re.compile(r"urn:li:[A-Za-z0-9:_()\-,\.]+")


class ValidationResult:
    """Result of the output validation pass."""

    def __init__(self, answer: str, confidence: str) -> None:
        self.answer = answer
        self.confidence = confidence


def has_evidence(results: Sequence[SearchResult]) -> bool:
    """True when retrieval returned usable evidence."""
    return bool(results)


def no_evidence_response() -> str:
    """The standardized response used when no metadata evidence exists."""
    return NO_EVIDENCE_RESPONSE


def _grounded_urns(docs: Sequence[ContextDocument]) -> set[str]:
    urns: set[str] = set()
    for doc in docs:
        if doc.entity_urn:
            urns.add(doc.entity_urn)
    return urns


def _find_ungrounded_urns(answer: str, docs: Sequence[ContextDocument]) -> list[str]:
    """URN references in the answer that are not backed by retrieved evidence."""
    if not answer or not docs:
        return []
    known = _grounded_urns(docs)
    ungrounded: list[str] = []
    for match in _URN_RE.finditer(answer):
        urn = match.group(0).rstrip(".,;)")
        if not urn:
            continue
        if urn in known:
            continue
        if any(urn in k for k in known):
            continue
        if urn not in ungrounded:
            ungrounded.append(urn)
    return ungrounded


def validate_generation(
    answer: str,
    docs: Sequence[ContextDocument],
    confidence: str,
) -> ValidationResult:
    """Sanity-check a generated answer against the retrieved evidence.

    - strips any URN that is not backed by retrieved metadata
    - masks secrets that leaked into the answer
    - downgrades confidence when there is no supporting evidence
    """
    if not answer:
        return ValidationResult(NO_EVIDENCE_RESPONSE, "low")

    from guardrails.sanitizer import contains_secrets, mask_secrets

    cleaned = mask_secrets(answer)

    ungrounded = _find_ungrounded_urns(cleaned, docs)
    for urn in ungrounded:
        cleaned = cleaned.replace(urn, "[entity]")
        log.info("guardrail_ungrounded_urn_removed", urn=urn)

    if ungrounded:
        log.info("guardrail_ungrounded_downgrade", count=len(ungrounded))
        confidence = "low"

    if not docs or contains_secrets(cleaned):
        log.info("guardrail_insufficient_evidence", has_docs=bool(docs))
        confidence = "low"

    return ValidationResult(cleaned, confidence)
