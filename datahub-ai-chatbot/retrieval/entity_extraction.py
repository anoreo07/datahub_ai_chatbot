"""Deterministic, resolver-backed entity extraction.

The root cause of several pipeline bugs is that entity names are guessed with
ad-hoc regex phrase-stripping (``chat_service._extract_name`` / regex fallback
in ``classifier``), which on questions like "Nếu xóa dataset dim_warehouse thì
ai bị ảnh hưởng?" grabs the whole sentence as an entity name.

This module inverts that: instead of guessing a name and hoping the resolver
matches, it scans the (normalized) question against the *actual* entity names
present in the catalog and returns the longest contiguous token-run that maps to
a real entity. This is O(names) with a cheap normalized-token index and needs no
LLM, so it is deterministic and fast.

Matches are scored by:
- exact normalized subsequence in the question (highest),
- prefix tokens of the entity present in the question,
- fuzzy/token-alignment score as a fallback for typos.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.repositories.entity_repository import EntityRepository
from retrieval.fuzzy import tokenize

log = structlog.get_logger()


@dataclass
class ExtractedEntity:
    """A real catalog entity whose name appears (or is strongly implied) in a question."""

    name: str
    display_name: str
    entity_type: str
    urn: str
    score: float = 0.0
    start: int = 0
    end: int = 0
    source: str = "extraction"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "entity_type": self.entity_type,
            "urn": self.urn,
            "score": self.score,
            "start": self.start,
            "end": self.end,
            "source": self.source,
        }


class EntityExtractor:
    """Extract catalog entity names from a natural-language question.

    The extractor pre-loads a bounded set of entities (per entity type) once,
    normalizes their names to ASCII tokens, and looks for those tokens as a
    contiguous subsequence inside the normalized question. Matching is
    accent/underscore/punctuation-insensitive, so ``dim_warehouse``,
    ``DIM WAREHOUSE`` and ``dim warehouse`` all resolve the same way.

    A module-level TTL cache shares the token index across request-scoped
    instances so we do not re-query the repository on every request.
    """

    _TYPES = ("dataset", "dashboard", "glossary_term", "document")
    _SHARED_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
    _SHARED_TTL = 300.0  # seconds; matches CACHE_DEFAULT_TTL_SECONDS

    def __init__(self, session: AsyncSession, limit: int = 4000) -> None:
        self._repo = EntityRepository(session)
        self._limit = limit
        self._index: list[dict[str, Any]] | None = None

    async def _build_index(self) -> list[dict[str, Any]]:
        if self._index is not None:
            return self._index
        cache_key = f"{self._limit}"
        cached = EntityExtractor._SHARED_CACHE.get(cache_key)
        now = time.time()
        if (settings.APP_ENV != "test" and cached
                and now - cached[0] < EntityExtractor._SHARED_TTL):
            self._index = cached[1]
            return self._index

        index: list[dict[str, Any]] = []
        for etype in self._TYPES:
            try:
                entities = await self._repo.list_by_type(etype, limit=self._limit)
            except Exception:  # noqa: BLE001
                entities = []
            for e in entities:
                if getattr(e, "deleted", False):
                    continue
                name = e.name
                display = e.display_name or e.name
                tokens = tokenize(name, min_len=1)
                if not tokens:
                    continue
                index.append({
                    "norm": " ".join(tokens),
                    "tokens": tokens,
                    "name": name,
                    "display_name": display,
                    "entity_type": e.entity_type or etype,
                    "urn": e.urn,
                })
        # Longest (most specific) matches first so subsuming names win.
        index.sort(key=lambda r: -len(r["tokens"]))
        self._index = index
        if settings.APP_ENV != "test":
            EntityExtractor._SHARED_CACHE[cache_key] = (now, index)
        log.info("extractor_index_built", types=self._TYPES, entries=len(index),
                 cached=False)
        return index

    async def extract(self, question: str, top_k: int = 5) -> list[ExtractedEntity]:
        """Return up to ``top_k`` entities matched in ``question``, best first."""
        q_tokens = tokenize(question, min_len=1)
        if not q_tokens:
            return []
        index = await self._build_index()

        matches: list[ExtractedEntity] = []
        seen_names: set[str] = set()
        for rec in index:
            ent_tokens = rec["tokens"]
            if len(ent_tokens) > len(q_tokens):
                continue
            # Contiguous-subsequence match (the decisive signal).
            pos = self._find_subsequence(q_tokens, ent_tokens)
            if pos is not None:
                score = 1.0
                source = "subsequence"
            else:
                # Fallback: all entity tokens individually present in the query.
                score, pos = self._token_overlap(q_tokens, ent_tokens)
                source = "overlap" if score > 0 else ""
            if score <= 0:
                continue
            key = rec["urn"]
            if key in seen_names:
                continue
            seen_names.add(key)
            matches.append(
                ExtractedEntity(
                    name=rec["name"],
                    display_name=rec["display_name"],
                    entity_type=rec["entity_type"],
                    urn=rec["urn"],
                    score=score,
                    start=pos if pos is not None else 0,
                    end=(pos + len(ent_tokens)) if pos is not None else 0,
                    source=source,
                )
            )

        if not matches:
            return await self._fuzzy_fallback(question)

        # Sort: subsequence matches first, then longer runs, then higher score.
        matches.sort(key=lambda m: (m.source != "subsequence", -(m.end - m.start), -m.score))
        out: list[ExtractedEntity] = []
        seen: set[str] = set()
        for m in matches:
            if m.urn in seen:
                continue
            seen.add(m.urn)
            out.append(m)
            if len(out) >= top_k:
                break
        return out

    @staticmethod
    def _find_subsequence(q_tokens: list[str], sub: list[str]) -> int | None:
        """Index of the first occurrence of ``sub`` as a contiguous run in ``q_tokens``."""
        if not sub:
            return None
        for i in range(len(q_tokens) - len(sub) + 1):
            if q_tokens[i : i + len(sub)] == sub:
                return i
        return None

    @staticmethod
    def _token_overlap(q_tokens: list[str], ent_tokens: list[str]) -> tuple[float, int | None]:
        """Fraction of entity tokens present anywhere in the query plus first-hit index."""
        qset = set(q_tokens)
        found = [t for t in ent_tokens if t in qset]
        if not found:
            return 0.0, None
        first = next((i for i, q in enumerate(q_tokens) if q in ent_tokens), None)
        return len(found) / len(ent_tokens), first

    async def _fuzzy_fallback(self, question: str) -> list[ExtractedEntity]:
        """Last-resort: fuzzy-token alignment over the catalog (typo tolerance)."""
        q_tokens = tokenize(question, min_len=1)
        if not q_tokens:
            return []
        index = await self._build_index()
        scored: list[tuple[float, dict[str, Any]]] = []
        for rec in index:
            from retrieval.fuzzy import _token_alignment_score

            alignment = _token_alignment_score(q_tokens, rec["tokens"])
            if alignment >= 0.55:
                scored.append((alignment, rec))
        if not scored:
            return []
        scored.sort(key=lambda t: -t[0])
        seen: set[str] = set()
        out: list[ExtractedEntity] = []
        for score, rec in scored:
            if rec["urn"] in seen:
                continue
            seen.add(rec["urn"])
            out.append(
                ExtractedEntity(
                    name=rec["name"],
                    display_name=rec["display_name"],
                    entity_type=rec["entity_type"],
                    urn=rec["urn"],
                    score=round(score, 3),
                    source="fuzzy",
                )
            )
        return out

    async def resolve_primary_dataset(self, question: str) -> ExtractedEntity | None:
        """Best dataset entity for the question, or None."""
        extracted = await self.extract(question)
        for e in extracted:
            if e.entity_type == "dataset":
                return e
        return None

    async def resolve_primary(self, question: str) -> ExtractedEntity | None:
        """Best entity of any type, or None."""
        extracted = await self.extract(question)
        return extracted[0] if extracted else None
