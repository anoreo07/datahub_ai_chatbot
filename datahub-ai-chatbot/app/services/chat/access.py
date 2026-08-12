import re
from collections.abc import Sequence
from typing import Any

import structlog

from app.auth.models import UserContext
from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import _extract_filter_value
from retrieval.intent import QueryIntent, _norm_vn

log = structlog.get_logger()


class DomainAccessService:
    """DomainAccessService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def collect_domain_names(self) -> list[str]:
        """Distinct domain names present in entity payloads."""
        import unicodedata

        entities = await self._ctx.entity_repo.list_all(limit=2000)
        seen: dict[str, str] = {}
        for e in entities:
            domain = (e.domain or (e.payload or {}).get("domain") or "").strip()
            if not domain:
                continue
            key = (
                unicodedata.normalize("NFKD", domain.lower())
                .encode("ascii", "ignore").decode("ascii")
            )
            seen.setdefault(key, domain)
        return list(seen.values())


    async def detect_requested_domains(self, question: str) -> list[str]:
        """Domain names explicitly requested in ``question``.

        Detects domains mentioned in the question text (normalized match) plus
        the value of a "thuộc domain X" / "domain X có..." filter. Returns the
        canonical domain label(s); empty list when the question names no domain.
        """
        import unicodedata

        q = _norm_vn(question)
        domain_names = await self.collect_domain_names()
        found: dict[str, str] = {}
        for name in domain_names:
            key = (
                unicodedata.normalize("NFKD", name.lower())
                .encode("ascii", "ignore").decode("ascii")
            )
            if key and key in q:
                found[key] = name
        # Explicit filter value ("thuộc domain X", "trong lĩnh vực X").
        value = _extract_filter_value(question, QueryIntent.DOMAIN_QUERY)
        if value:
            vkey = _norm_vn(value)
            if vkey:
                # Prefer a canonical domain label already matched in the text;
                # only fall back to the raw value when no canonical name exists.
                matched = next((n for k, n in found.items() if vkey in k or k in vkey), None)
                found[vkey] = matched if matched else (value if value else vkey)
        return list(found.values()) if found else ([value] if value else [])


    async def gate_domain_access(
        self, question: str, user_ctx: UserContext,
        entity_hint: str | None = None, history: Sequence[Any] | None = None,
    ) -> str | None:
        """Pre-retrieval domain gate.

        Before any GraphQL / metadata / vector / RAG / semantic / aggregation /
        LLM call, verify the user's roles grant access to the domain(s) the
        question asks about. The domain can be named explicitly in the text or
        implied by a catalog entity referenced in the question (e.g. a dataset
        that belongs to an off-limits domain). Returns a localized authorization
        message when the target domain is off-limits, otherwise ``None``.
        """
        if user_ctx.is_admin:
            return None
        auth = self._ctx.auth_service
        if auth is None:
            return None
        domains = await self.detect_requested_domains(question)
        if not domains:
            domains = await self.domains_of_requested_entities(
                question, entity_hint=entity_hint, history=history,
            )
        if not domains:
            return None
        for domain in domains:
            message = await auth.access_message(user_ctx, domain)
            if message:
                log.info("chat_domain_denied", trace_id=None,
                         user=user_ctx.user_id, domain=domain)
                return message
        return None


    async def domains_of_requested_entities(
        self, question: str, entity_hint: str | None = None,
        history: Sequence[Any] | None = None,
    ) -> list[str]:
        """Canonical domains of catalog entities referenced in ``question``.

        Used by the pre-retrieval gate so entity-level queries about an
        unauthorized domain (e.g. "sales_order có bao nhiêu cột?" where
        sales_order belongs to Logistics) are denied instead of silently
        returning "0 datasets" / "Không tìm thấy" after post-retrieval
        filtering drops every result.
        """
        domains: dict[str, str] = {}

        def _add(entity: Any) -> None:
            if entity is None:
                return
            domain = (entity.domain or (entity.payload or {}).get("domain") or "").strip()
            if domain:
                domains[domain] = domain

        try:
            matches = await self._ctx.entity_extractor.extract(question, top_k=8)
        except Exception:  # noqa: BLE001
            matches = []
        # Only entities the user literally names may trigger a pre-retrieval
        # denial. The extractor also returns strong fuzzy/"implied" matches (e.g.
        # unrelated assembly tables for a question naming only "dim_warehouse"),
        # which would falsely deny domain access by dragging in their domains.
        q_blob = _norm_vn(question)
        for m in matches:
            nm = _norm_vn(m.name or "")
            disp = _norm_vn(m.display_name or "")
            if not (nm and (nm in q_blob or disp in q_blob)):
                continue
            entity = await self._ctx.entity_repo.get_by_urn(m.urn)
            _add(entity)

        if entity_hint:
            try:
                for entity in await self._ctx.entity_repo.search_by_name(entity_hint):
                    _add(entity)
            except Exception:  # noqa: BLE001
                pass

        # Anaphoric follow-up ("nó", "dataset này", "nó bị ảnh hưởng gì", ...)
        # with no entity in the current message: the entity lives in the most
        # recent history turn. A conservative pronoun set avoids false positives
        # from common single-syllable words ("ở", "đi", "o", ...).
        if not domains and history:
            anaphora_pronouns = {"no", "do", "day", "nay", "kia", "ay"}
            q_tokens = {_norm_vn(t) for t in re.split(r"\W+", question) if t}
            if q_tokens.intersection(anaphora_pronouns):
                last_question = history[-1][0] if history else None
                if last_question:
                    try:
                        matches = await self._ctx.entity_extractor.extract(last_question, top_k=3)
                    except Exception:  # noqa: BLE001
                        matches = []
                    last_blob = _norm_vn(last_question)
                    for m in matches:
                        nm = _norm_vn(m.name or "")
                        disp = _norm_vn(m.display_name or "")
                        if not (nm and (nm in last_blob or disp in last_blob)):
                            continue
                        entity = await self._ctx.entity_repo.get_by_urn(m.urn)
                        _add(entity)

        return list(domains.values())
