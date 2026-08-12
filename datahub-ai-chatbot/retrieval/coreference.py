"""Coreference resolution for multi-turn conversations (nó/đó/ấy/this/that…).

A follow-up like ``"Nó thuộc lĩnh vực nào?"`` or ``"schema của nó là gì?"``
refers back to an entity introduced in an earlier turn. The naive approach —
returning the last identifier token in the most recent question — is wrong
when a turn mentions a *field* ("warehouse_id là gì?") while the conversation's
subject is still the *dataset* ("dim_warehouse"). Because domain / ownership /
lineage / impact questions are almost always about the dataset, we resolve an
anaphor to the most recent **subject-context** entity (a token introduced in a
"dataset / schema của / lineage của / impact của ..." clause) and fall back to
the last mention only when no subject was ever established.

Both entry points used by the routing layer:

- ``resolve_anaphora_entity(history)``: the full-history resolver used by
  ``ChatService`` and the token heuristics (pure, no I/O) shared by the intent
  resolver and the domain gate.
- ``extract_candidates(question)``: low-level helper exposing the per-turn
  candidate tokens and whether each is a subject candidate.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

# A token is a *dataset subject* when it directly follows:
#   - a possessive clause whose last word is the preposition  "của/cua/of"
#     (optionally preceded by a capability word: "schema của X", "impact của X"),
#   - or a direct entity word ("dataset X", "bảng X", "table X", "schema X").
# Requiring the preposition / entity word to be the *last* token before the
# identifier prevents action words ("impact analysis") from being misread as
# subjects because "impact" happens to appear earlier in the window.
_SUBJECT_POSSESSIVE = re.compile(
    r"(?:schema|lineage|linage|impact|owner|domain|definition|định nghĩa|dinh nghia|"
    r"nguồn|nguon|upstream|downstream|dataflow)?\s*(?:của|cua|of)\s*$",
    re.I,
)
_SUBJECT_DIRECT = re.compile(
    r"(?:dataset|bảng|bang|table|schema|entity|term)\s+$",
    re.I,
)

_IDENT_RE = re.compile(
    r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+"
    r"|[A-Za-z]{2,}_[A-Za-z0-9_]+"
    # Hyphenated / multi-word glossary term names ("3-Way Matching", "BOM").
    r"|[A-Za-z0-9]+-[A-Za-z0-9]+(?:\s+[A-Za-z0-9][A-Za-z0-9.-]*)*"
)

# Stopwords that never refer to a metadata entity.
_STOP = {
    "dataset", "dashboard", "table", "schema", "field", "column", "owner",
    "domain", "lineage", "linage", "impact", "glossary", "term", "datahub",
    "report", "list", "link", "url", "sql", "query", "report", "metadata",
    "report", "the", "to", "a", "an", "and", "or", "of", "for", "in", "on",
    "this", "that", "these", "those", "with", "from", "upstream", "downstream",
    # Vietnamese noise
    "cho", "toi", "cua", "va", "co", "la", "gi", "nao", "cac", "duoc", "ban",
    "khong", "nhung", "nay", "do", "no", "ay", "kia", "thong", "tin", "ve",
    "voi", "tu", "con", "cua", "mot", "hoac", "hay", "lai", "len", "xuong",
    "vua", "ra", "em", "anh", "chi", "bai",
}


def _clean(token: str) -> bool:
    t = token.lower()
    return len(t) > 2 and t not in _STOP and not t.isdigit()


def _candidates_in(question: str) -> list[tuple[str, bool]]:
    """Return (token, is_subject) for every identifier in ``question``.

    A token is a subject candidate when it directly follows a license or
    entity clause (e.g. "schema của X", "dataset X"). Otherwise it's a token
    mention (a field/column).
    """
    out: list[tuple[str, bool]] = []
    for m in _IDENT_RE.finditer(question):
        token = m.group(0)
        if not _clean(token):
            continue
        start = max(0, m.start() - 16)
        before = question[start : m.start()]
        is_subject = bool(
            _SUBJECT_POSSESSIVE.search(before) or _SUBJECT_DIRECT.search(before)
        )
        out.append((token, is_subject))
    return out


def extract_candidates(history: Sequence[tuple[str, str]] | None) -> list[tuple[str, str]]:
    """Flatten per-turn mentions into (token, "subject" | "mention") in history order.

    The oldest turn comes first so callers can pick the most recent subject by
    reversing. Useful for debugging / tests and for the ACL/domain gate.
    """
    rows: list[tuple[str, str]] = []
    for question, _answer in history or []:
        for token, is_subject in _candidates_in(question):
            rows.append((token, "subject" if is_subject else "mention"))
    return rows


def resolve_entity_reference(history: Sequence[tuple[str, str]] | None) -> str | None:
    """Resolve what an anaphore / ellipsis follow-up refers to.

    Preference order (scanning from the most recent turn backwards):

    1. The most recent **subject** entity (the dataset of the conversation).
    2. The most recent token mention (a field/column) only if no subject exists.

    Returns ``None`` when the history carries no identifier worth using.
    """
    if not history:
        return None
    fallback: str | None = None
    for question, _answer in reversed(history):
        for token, is_subject in _candidates_in(question):
            if fallback is None:
                fallback = token
            if is_subject:
                # First subject found scanning backwards = the most recent.
                return token
    return fallback


def has_anaphora(question: str) -> bool:
    """True when ``question`` references an earlier turn (hence needs resolution)."""
    low = question.lower()
    if re.search(r"\b(?:nó|đó|ấy|này|đây|kia)\b", low):
        return True
    n = re.sub(r"[đĐ]", "d", low)
    n = re.sub(r"[áàảãạâấầẩẫậăắằẳẵặ]", "a", n)
    n = re.sub(r"[éèẻẽẹêếềểễệ]", "e", n)
    n = re.sub(r"[íìỉĩị]", "i", n)
    n = re.sub(r"[óòỏõọôốồổỗộơớờởỡợ]", "o", n)
    n = re.sub(r"[úùủũụưứừửữự]", "u", n)
    n = re.sub(r"[ýỳỷỹỵ]", "y", n)
    return bool(re.search(r"\b(?:no|do|ay|nay|day|kia)\b", n)) or bool(
        re.search(r"\b(?:this|that|these|those|the\s+one)\b", low)
    )
