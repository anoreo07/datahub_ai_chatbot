"""GuardrailService - orchestrates guardrail checks for the chat flow.

Reusable, stateless guardrails applied around retrieval and generation:
- scope restriction (metadata-only assistant)
- prompt-injection detection on user input
- retrieval / evidence validation
- recommendation-question detection (Facts vs Recommendation)
"""

import re

import structlog

from guardrails.sanitizer import detect_prompt_injection
from guardrails.scope import is_out_of_scope, out_of_scope_response
from guardrails.validation import has_evidence, no_evidence_response
from retrieval.hybrid_search import SearchResult

log = structlog.get_logger()

# "Which dataset should I use?" style questions must be answered with separate
# Facts and Recommendation sections.
_RECOMMENDATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"which\s+(?:dataset|table|dashboard|entity|dataset\s*\(s\))\s+should\s+(?:i|we)\s+(?:use|choose|pick|select)\b",
        re.I,
    ),
    re.compile(r"which\s+one\s+should\s+(?:i|we)\s+(?:use|choose|pick|select)\b", re.I),
    re.compile(r"should\s+(?:i|we)\s+use\s+(?:which|this|that|the)\s+dataset\b", re.I),
    re.compile(r"nên\s+dùng\s+(?:dataset|bảng|bảng\s+dữ\s+liệu|dashboard)\s+nào\b", re.I),
    re.compile(r"dataset\s+nào\s+nên\s+dùng\b", re.I),
    re.compile(r"nên\s+chọn\s+(?:dataset|bảng|dashboard)\s+nào\b", re.I),
]

_INJECTION_RESPONSE = (
    "Tôi là trợ lý DataHub và không thể thực hiện yêu cầu này. Hệ thống từ chối các "
    "yêu cầu vi phạm chính sách bảo mật, trích xuất cấu hình bí mật hoặc can thiệp dữ liệu."
)


class GuardrailService:
    """Enforces guardrails around the chat flow without owning the pipeline."""

    def enforce_scope(self, query: str) -> str | None:
        """Return an out-of-scope response, or ``None`` when in scope."""
        if is_out_of_scope(query):
            return out_of_scope_response(query)
        return None

    def check_prompt_injection(self, query: str) -> str | None:
        """Return a policy response when user input tries to override the system."""
        detected, _ = detect_prompt_injection(query)
        if detected:
            log.info("guardrail_injection_blocked", query=query[:120])
            return _INJECTION_RESPONSE
        return None

    def is_recommendation(self, query: str) -> bool:
        """True for 'which dataset should I use' style recommendation questions."""
        return any(p.search(query) for p in _RECOMMENDATION_PATTERNS)

    def validate_evidence(self, results: list[SearchResult]) -> tuple[bool, str | None]:
        """Return ``(has_evidence, response)``; response is set when empty."""
        if not has_evidence(results):
            return False, no_evidence_response()
        return True, None
