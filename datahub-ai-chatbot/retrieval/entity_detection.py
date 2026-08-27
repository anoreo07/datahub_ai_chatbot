"""Entity name detection — detect if a query looks like an entity name reference.

Generic — works for any entity in the catalog, not hard-coded per entity/term/dataset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

log = structlog.get_logger(__name__)

# Vietnamese question markers
_QUESTION_MARKERS_VN = frozenset({
    "là gì", "la gi", "của ai", "cua ai", "thuộc về ai",
    "có bao nhiêu", "co bao nhieu", "liệt kê", "lieu ke",
    "cho tôi xem", "cho toi xem", "hiển thị", "hien thi",
    "tìm kiếm", "tim kiem", "tìm", "tim", "tìm giúp", "tim giup",
    "xem", "liệt kê", "so sánh", "sanh", "compare",
})

# English question markers
_QUESTION_MARKERS_EN = frozenset({
    "what", "which", "who", "where", "when", "why", "how",
    "list", "show", "find", "search", "get", "give me",
    "tell me", "describe", "explain", "compare",
})

# Action verbs that suggest the user wants to DO something (not just name an entity)
_ACTION_VERBS = frozenset({
    # Vietnamese
    "lấy", "lay", "trích xuất", "trich xuat", "tạo", "tao",
    "so sánh", "ss", "phân tich", "phan tich",
    "viết", "viet", "generate", "tính", "tinh",
    # English
    "get", "fetch", "retrieve", "generate", "create", "build",
    "calculate", "compute", "analyze", "analyse",
})

# Entity stopwords — words that are NOT part of an entity name
_ENTITY_STOPWORDS = frozenset({
    # Vietnamese
    "dataset", "bảng", "bang", "table", "field", "fields",
    "trường", "truong", "cột", "cot", "column", "columns",
    "schema", "metadata", "term", "glossary", "thuật ngữ",
    "report", "dashboard", "biểu đồ", "bieu do",
    # English
    "dataset", "table", "field", "column", "schema",
    "report", "dashboard", "document", "term",
})


@dataclass
class EntityNameSignal:
    """Result of entity name detection."""

    is_entity_name: bool
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    extracted_tokens: list[str] = field(default_factory=list)


class EntityNameDetector:
    """Detect if a query looks like an entity name reference.

    Generic — works for any entity in the catalog, not hard-coded
    per entity/term/dataset.

    Signals that a query is an entity name:
    1. Contains snake_case identifiers (dim_warehouse, fact_sales)
    2. Contains dotted paths (sales.orders, dms.stg.material)
    3. Contains quoted names ("Analyse Product Cost Collector")
    4. Low question-word density (few Vietnamese/English question markers)
    5. No action verbs (get, show, list, find, compare)
    6. High ratio of proper nouns / capitalized words
    """

    def detect(self, query: str) -> EntityNameSignal:
        """Detect if query looks like an entity name.

        Args:
            query: The user's query string.

        Returns:
            EntityNameSignal with is_entity_name, signals, confidence, extracted_tokens.
        """
        signals = []
        q_lower = query.lower().strip()

        # Signal 1: Snake_case identifier
        if re.search(r"[a-z0-9]{2,}_[a-z0-9_]+", query):
            signals.append("snake_case")

        # Signal 2: Dotted path
        if re.search(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", query):
            signals.append("dotted_path")

        # Signal 3: Quoted name
        if re.search(r"""['"][^'"]{2,80}['"]""", query):
            signals.append("quoted")

        # Signal 4: Low question-word density
        q_word_count = self._question_word_count(q_lower)
        if q_word_count == 0:
            signals.append("no_question_words")
        elif q_word_count == 1:
            signals.append("low_question_words")

        # Signal 5: No action verbs
        if not self._has_action_verbs(q_lower):
            signals.append("no_action_verbs")

        # Signal 6: High proper-noun ratio
        proper_ratio = self._proper_noun_ratio(query)
        if proper_ratio > 0.5:
            signals.append("high_proper_noun_ratio")

        # Signal 7: No entity stopwords
        if not self._has_entity_stopwords(q_lower):
            signals.append("no_entity_stopwords")

        # Decision: require 4+ signals for entity name detection
        # (more conservative to avoid false positives on schema/field queries)
        is_entity_name = len(signals) >= 4

        # Extract tokens (remove stopwords and question markers)
        extracted = self._extract_entity_tokens(query)

        return EntityNameSignal(
            is_entity_name=is_entity_name,
            signals=signals,
            confidence=min(1.0, len(signals) / 5.0),
            extracted_tokens=extracted,
        )

    def _question_word_count(self, q_lower: str) -> int:
        """Count question words in the query."""
        count = 0
        for marker in _QUESTION_MARKERS_VN:
            if marker in q_lower:
                count += 1
        for marker in _QUESTION_MARKERS_EN:
            if re.search(rf"\b{re.escape(marker)}\b", q_lower):
                count += 1
        return count

    def _has_action_verbs(self, q_lower: str) -> bool:
        """Check if query contains action verbs."""
        for verb in _ACTION_VERBS:
            if re.search(rf"\b{re.escape(verb)}\b", q_lower):
                return True
        return False

    def _proper_noun_ratio(self, query: str) -> float:
        """Calculate ratio of capitalized words (proper nouns)."""
        words = query.split()
        if not words:
            return 0.0
        # Skip first word (always capitalized in sentences)
        if len(words) <= 1:
            return 0.0
        proper_count = sum(1 for w in words[1:] if w[0].isupper() if len(w) > 0)
        return proper_count / max(1, len(words) - 1)

    def _has_entity_stopwords(self, q_lower: str) -> bool:
        """Check if query contains entity stopwords."""
        for stopword in _ENTITY_STOPWORDS:
            if re.search(rf"\b{re.escape(stopword)}\b", q_lower):
                return True
        return False

    def _extract_entity_tokens(self, query: str) -> list[str]:
        """Extract entity tokens from query, removing stopwords and question markers."""
        words = query.split()
        extracted = []
        for word in words:
            w_lower = word.lower().strip("?!.,;:")
            if w_lower in _ENTITY_STOPWORDS:
                continue
            if any(m in w_lower for m in _QUESTION_MARKERS_VN):
                continue
            if w_lower in _QUESTION_MARKERS_EN:
                continue
            if len(w_lower) < 2:
                continue
            extracted.append(word)
        return extracted
