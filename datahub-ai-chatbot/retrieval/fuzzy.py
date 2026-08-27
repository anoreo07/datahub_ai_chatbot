"""Fuzzy + phonetic matching helpers for entity name resolution.

Supports typo-tolerant matching and Vietnamese accent/phonetic spelling by
normalizing both sides to an ASCII, space-separated form before comparing with
token-level and subsequence similarity.
"""

import re
import unicodedata
from difflib import SequenceMatcher

_ACCENTS_RE = re.compile(r"[^a-z0-9]+")


def ascii_fold(text: str) -> str:
    """Lowercase and strip Vietnamese diacritics + fold đ -> d."""
    s = text or ""
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return s


def normalize(text: str) -> str:
    """Fold to ASCII and collapse punctuation/spaces into single spaces."""
    s = _ACCENTS_RE.sub(" ", ascii_fold(text))
    return re.sub(r"\s+", " ", s).strip()


def split_identifier_segments(text: str) -> list[str]:
    """Split identifier by camelCase, PascalCase, snake_case, and kebab-case."""
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text or "")
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)
    s = ascii_fold(s)
    parts = re.split(r'[^a-z0-9]+', s)
    return [p for p in parts if p]


def adaptive_fuzzy_threshold(query: str) -> float:
    """Return length-adaptive threshold for matching confidence.

    - Length <= 5: 0.85
    - Length 6-12: 0.80
    - Length > 12: 0.75
    """
    length = len(query.strip())
    if length <= 5:
        return 0.85
    elif length <= 12:
        return 0.80
    else:
        return 0.75


def tokenize(text: str, min_len: int = 3) -> list[str]:
    return [s for s in split_identifier_segments(text) if len(s) >= max(1, min_len)]



def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _token_alignment_score(q_tokens: list[str], n_tokens: list[str]) -> float:
    if not q_tokens or not n_tokens:
        return 0.0
    scores: list[float] = []
    for qt in q_tokens:
        best = max((_ratio(qt, nt) for nt in n_tokens), default=0.0)
        scores.append(best)
    return sum(scores) / len(scores)


def fuzzy_score(query: str, name: str, name_tokens: list[str] | None = None) -> float:
    """Return a fuzzy similarity score in [0, 1] between a query and a name.

    Combines a full-string ratio (handles pure typos) with segment/token-alignment
    ratio (handles swapped/missing words and camelCase/snake_case identifiers).
    """
    q = normalize(query)
    n = normalize(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0

    qt = tokenize(query, min_len=1)
    nt = name_tokens if name_tokens is not None else tokenize(name, min_len=1)

    full = _ratio(q, n)
    raw_full = _ratio(query.strip().lower(), name.strip().lower())

    # Token / segment level: typo and camelCase / snake_case tolerant.
    tok = _token_alignment_score(qt, nt)

    # Sub-word/prefix bonus: case where query is a real substring after folding.
    substring_bonus = 0.0
    if q in n or n in q:
        substring_bonus = 0.1

    return min(1.0, max(full, raw_full, tok) + substring_bonus)


def best_candidate(query: str, candidates: list[str]) -> tuple[str, float] | None:
    """Return the best (name, score) among candidate names for a query."""
    best_name: str | None = None
    best_score = 0.0
    for cand in candidates:
        score = fuzzy_score(query, cand)
        if score > best_score:
            best_score = score
            best_name = cand
    if best_name is None:
        return None
    return best_name, best_score

