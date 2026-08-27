"""Stateless confirmation detection — detects yes/no responses from conversation history.

No server-side state needed. Works across workers and survives restarts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import structlog

log = structlog.get_logger(__name__)


@dataclass
class ConfirmationResult:
    """Result of confirmation detection."""

    action: Literal["confirm", "deny", "new_query"]
    entity_name: str | None = None
    confidence: float = 0.0
    reason: str = ""


# Vietnamese and English confirmation words
_CONFIRM_WORDS = frozenset({
    # Vietnamese
    "vâng", "vang", "đúng", "dung", "ok", "oke", "okay",
    "chính xác", "chinh xac", "chọn", "chon", "confirm",
    "thế", "the", "vậy", "vay", "Ừ", "uh", "um",
    # English
    "yes", "yep", "yeah", "correct", "right", "sure", "confirm",
})

# Vietnamese and English denial words
_DENY_WORDS = frozenset({
    # Vietnamese
    "không", "khong", "khác", "khac", "sai", "không phải", "khong phai",
    "không đúng", "khong dung", "bỏ qua", "bo qua",
    # English
    "no", "nope", "deny", "wrong", "different", "skip", "cancel",
})

# Patterns that indicate the last assistant message was a clarification/suggestion
_CLARIFICATION_INDICATORS = [
    # Suggestion patterns
    re.compile(r"ý\s+bạn\s+là", re.I),
    re.compile(r"ban\s+muon", re.I),
    re.compile(r"ban\s+muon\s+hoi", re.I),
    # Not found patterns
    re.compile(r"kh[oơ]ng\s+t[iì]m\s+thấy", re.I),
    re.compile(r"kh[oơ]ng\s+t[oồ]n\s+t[aại]", re.I),
    re.compile(r"not\s+found", re.I),
    re.compile(r"does\s+not\s+exist", re.I),
    # Ambiguity patterns
    re.compile(r"entity\s+nao", re.I),
    re.compile(r"ban\s+muon\s+hoi\s+ve", re.I),
    re.compile(r"ch[oọ]n\s+1", re.I),
    re.compile(r"co\s+nhieu", re.I),
    re.compile(r"trùng\s+khớp", re.I),
    re.compile(r"trung\s+khop", re.I),
]


class ConfirmationDetector:
    """Detect confirmation/denial from conversation history.

    Stateless — no server-side state needed. Checks if the last assistant
    message was a clarification/suggestion, and if the current message
    confirms or denies it.

    Works across workers and survives restarts because it only reads
    conversation history (persisted in DB).
    """

    def detect(
        self,
        question: str,
        history: list[tuple[str, str]],
    ) -> ConfirmationResult:
        """Detect if question is a confirmation of the last assistant message.

        Args:
            question: The current user message.
            history: List of (question, answer) tuples from conversation history.

        Returns:
            ConfirmationResult with action, entity_name, confidence, reason.
        """
        if not history:
            return ConfirmationResult(action="new_query", reason="no_history")

        last_q, last_a = history[-1]
        q_lower = question.lower().strip()

        # Check if last assistant message was a clarification/suggestion
        if not self._was_clarification(last_a):
            return ConfirmationResult(
                action="new_query",
                reason="last_answer_not_clarification",
            )

        # Check if current message is a confirmation
        if self._is_confirmation(q_lower):
            entity = self._extract_suggested_entity(last_a)
            return ConfirmationResult(
                action="confirm",
                entity_name=entity,
                confidence=0.9,
                reason="confirmation_word_detected",
            )

        # Check if current message is a denial
        if self._is_denial(q_lower):
            return ConfirmationResult(
                action="deny",
                confidence=0.8,
                reason="denial_word_detected",
            )

        # Ambiguous — treat as new query
        return ConfirmationResult(
            action="new_query",
            reason="ambiguous_response",
        )

    def _was_clarification(self, last_answer: str) -> bool:
        """Check if the last assistant message was a clarification/suggestion."""
        if not last_answer:
            return False
        return any(p.search(last_answer) for p in _CLARIFICATION_INDICATORS)

    def _is_confirmation(self, question_lower: str) -> bool:
        """Check if the question is a confirmation."""
        # Exact match for short confirmations
        if question_lower in _CONFIRM_WORDS:
            return True
        # Check if any confirm word appears as a standalone word
        for word in _CONFIRM_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", question_lower):
                return True
        return False

    def _is_denial(self, question_lower: str) -> bool:
        """Check if the question is a denial."""
        # Exact match for short denials
        if question_lower in _DENY_WORDS:
            return True
        # Check if any deny word appears as a standalone word
        for word in _DENY_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", question_lower):
                return True
        return False

    def _extract_suggested_entity(self, last_answer: str) -> str | None:
        """Extract the suggested entity name from the last assistant message.

        Parses patterns like:
        - "Ý bạn là 'dim_warehouse'?"
        - "Bạn có muốn说的是 'Analyse Product Cost Collector'?"
        - "'X' không tồn tại. Ý bạn là 'Y'?"
        """
        # Pattern: "ý bạn là 'X'" or "ban co nghia la 'X'"
        m = re.search(
            r"ý\s+bạn\s+là\s+['\"]?([^'\"?]+?)['\"]?\s*\?",
            last_answer, re.I,
        )
        if m:
            return m.group(1).strip()

        # Pattern: "'X' không tồn tại. Ý bạn là 'Y'?"
        m = re.search(
            r"['\"]([^'\"]+)['\"]\s*kh[oơ]ng\s+t[oồ]n\s+t[aại].*?"
            r"ý\s+bạn\s+là\s+['\"]?([^'\"?]+?)['\"]?\s*\?",
            last_answer, re.I,
        )
        if m:
            return m.group(2).strip()

        # Pattern: "Bạn có muốn说的是 'X'?" or "Ban muon hoi ve 'X'?"
        m = re.search(
            r"(?:ban\s+muon|b[aạ]n\s+c[oó]\s+mu[uố]n)\s+.*?"
            r"['\"]([^'\"]+)['\"]",
            last_answer, re.I,
        )
        if m:
            return m.group(1).strip()

        return None
