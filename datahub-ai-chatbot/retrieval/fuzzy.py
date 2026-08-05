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


def tokenize(text: str, min_len: int = 3) -> list[str]:
    return [t for t in normalize(text).split() if len(t) >= max(1, min_len)]


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

    Combines a full-string ratio (handles pure typos) with a token-alignment
    ratio (handles swapped/missing words and differently-separated identifiers).
    """
    q = normalize(query)
    n = normalize(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0

    qt = tokenize(q)
    nt = name_tokens if name_tokens is not None else tokenize(n)

    full = _ratio(q, n)

    # Token-level: typo / word-order tolerant.
    tok = _token_alignment_score(qt, nt)

    # Sub-word/prefix bonus: case where query is a real substring after folding.
    substring_bonus = 0.0
    if q in n or n in q:
        substring_bonus = 0.1

    return min(1.0, max(full, tok) + substring_bonus)


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
