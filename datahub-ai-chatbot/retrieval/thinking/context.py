"""Context resolver for Thinking Mode.

Resolves the conversational + domain context a complex question runs in:
active entities (from the latest turn / conversation history), all entities
named in the question, related glossary terms and domains, and flags for
multi-goal / cross-domain / is-multihop intent. Independent of the LLM.
"""

from __future__ import annotations

import re

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.entity_repository import EntityRepository
from retrieval.entity_extraction import EntityExtractor
from retrieval.thinking.models import ThinkingContext

log = structlog.get_logger()

_TOKEN_RE = re.compile(r"[a-z0-9_\.]+", re.I)

# Connector words that can join two distinct entities in one question.
_CONNECTOR_RE = re.compile(r"\b(?:\bvà\b|\bva\b|\band\b|\bor\b|\bhoặc\b|,)\b", re.I)


class ContextResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EntityRepository(session)
        self._extractor = EntityExtractor(session)

    async def resolve(
        self,
        question: str,
        history: list[tuple[str, str]] | None = None,
    ) -> ThinkingContext:
        # Entities mentioned directly in the question.
        extracted = await self._extractor.extract(question, top_k=6)
        question_entities = [e.name for e in extracted] or []

        # Active entity: the one named inline, else the last entity in history.
        active = question_entities[:1]
        has_history = bool(history)
        if not active and has_history:
            from_hist = await self._extractor.extract(
                " ".join(q for q, _ in (history or [])), top_k=2
            )
            if from_hist:
                active = [from_hist[0].name]

        # Try to detect multi-goal via multiple "verb+noun-table" fragments.
        multi_goal = self._detect_multi_goal(question, question_entities)

        related_terms = [t.name for t in extracted if t.entity_type == "glossary_term"]
        related_domains = self._extract_domains(question)

        ctx = ThinkingContext(
            question=question,
            active_entities=active or [],
            all_entities=question_entities,
            conversation_summary="context from history" if has_history else "",
            related_terms=related_terms,
            related_domains=related_domains,
            multi_goal=multi_goal,
            cross_domain=self._detect_cross_domain(question, related_domains),
        )
        log.info("thinking_context", entities=ctx.all_entities,
                 active=ctx.active_entities, multi_goal=ctx.multi_goal,
                 cross_domain=ctx.cross_domain, question=question[:100])
        return ctx

    def _detect_multi_goal(self, question: str, entities: list[str] | None = None) -> bool:
        if not question:
            return False
        # Count distinct "verb phrases" ending phrase separators.
        lower = question.lower()
        separators = len(re.findall(r"(?:rồi|sau đó|và|còn|rồi|,|and|then)", lower))
        return separators >= 1 and len(_TOKEN_RE.findall(lower)) >= 6

    def _extract_domains(self, question: str) -> list[str]:
        m = re.search(r"domain[s]?[\s:]*([A-Za-z0-9_\ ]+)", question, re.I)
        if m:
            name = m.group(1).strip().split()[0] if m.group(1).strip() else ""
            return [name] if name else []
        # Vietnamese "thuộc/thuong domain X"
        m2 = re.search(r"(?:domain|lĩnh vực)\s+([A-Za-z0-9_]+)", question, re.I)
        return [m2.group(1)] if m2 else []

    def _detect_cross_domain(self, question: str, domains: list[str]) -> bool:
        if len(domains) >= 2:
            return True
        return bool(re.search(r"cross[- ]?domain|chéo|lien (?:cac|den) domain", question, re.I))
