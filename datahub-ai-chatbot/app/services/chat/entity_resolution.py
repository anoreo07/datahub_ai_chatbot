import re
from collections.abc import Sequence

import structlog

from app.auth.models import UserContext
from app.schemas.chat import Suggestion
from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import (
    _entity_payload_to_text,
    _extract_name,
    _infer_entity_from_history,
    _is_noisy_entity,
    _trusted_resolution,
)
from retrieval.entity_resolver import ResolutionResult
from retrieval.fuzzy import fuzzy_score
from retrieval.hybrid_search import SearchResult
from retrieval.intent import _norm_vn

log = structlog.get_logger()


class EntityResolutionService:
    """EntityResolutionService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def entity_name_for(
        self, question: str, remove_words: list[str],
        prefer_type: str | None = None, trace_id: str | None = None,
    ) -> str:
        """Extract a clean entity name, canonicalised against the real catalog.

        The keyword extractor may output a whole-sentence phrase for composite
        questions ("dim_warehouse ... trường ... giải thích"). When that happens
        we scan the question against real DataHub entity names (resolver-backed)
        and return the canonical match — entity resolution independent of intent.
        """
        raw = _extract_name(question, remove_words)
        if not raw or not _is_noisy_entity(raw):
            return raw
        try:
            extracted = await self._ctx.entity_extractor.extract(question)
        except Exception:  # noqa: BLE001
            return raw
        if prefer_type:
            hit = next((e for e in extracted if e.entity_type == prefer_type), None)
        else:
            hit = extracted[0] if extracted else None
        if hit:
            log.info("entity_canonicalised", trace_id=trace_id,
                     raw=raw[:80], canonical=hit.name, etype=hit.entity_type)
            return hit.name
        return raw


    async def try_explicit_entity_lookup(
        self, question: str, user_ctx: UserContext,
        trace_id: str | None = None,
    ) -> list:
        """Resolve a catalog entity that the question names EXACTLY.

        Candidates are dataset-style identifiers (``dim_warehouse``,
        ``sales.orders``, ``finance.monthly_revenue``) present verbatim in the
        question. The first identifier that resolves against the catalog wins;
        the caller grounds the whole answer on it instead of fuzzy hybrid search.
        """
        from app.services.action_service import ActionService
        from retrieval.hybrid_search import SearchResult

        tokens = set(re.findall(
            r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+|[A-Za-z0-9_]+_[A-Za-z0-9_]+",
            question,
        ))
        if not tokens:
            return []
        svc = ActionService(self._ctx.session, auth_service=self._ctx.auth_service)
        for tok in sorted(tokens, key=len, reverse=True):
            entity = await svc.resolve_dataset(tok, user=user_ctx)
            if entity is None:
                continue
            payload = entity.payload or {}
            content = _entity_payload_to_text("dataset", payload)
            log.info("explicit_entity_lookup", trace_id=trace_id, token=tok,
                     resolved=entity.display_name or entity.name)
            return [SearchResult(
                urn=entity.urn, entity_type="dataset",
                name=entity.display_name or entity.name, score=1.0,
                datahub_url=entity.datahub_url,
                payload={**payload, "content": content},
            )]
        return []


    async def resolve_with_expansion(
        self, term_name: str, question: str, entity_type: str | None = None,
        trace_id: str | None = None,
    ) -> ResolutionResult | None:
        """Resolve ``term_name``, falling back to semantically expanded synonyms.

        Returns the best trusted result, or None when nothing resolves even after
        expansion (caller then runs the suggestion / not-found flow).
        """
        if term_name:
            resolution = await self._ctx.entity_resolver.resolve(
                term_name, entity_type=entity_type, trace_id=trace_id)
            if _trusted_resolution(resolution):
                return resolution

        expansion = self._ctx.semantic.expand(question)
        for term in expansion.terms[1:]:
            resolution = await self._ctx.entity_resolver.resolve(
                term, entity_type=entity_type, trace_id=trace_id)
            if _trusted_resolution(resolution):
                log.info("resolve_via_semantic_expansion", trace_id=trace_id,
                         original=term_name, expanded=term,
                         resolved=resolution.resolved.name,
                         matched=expansion.matched)
                return resolution
        return None


    def entities_to_results(self, entities: Sequence) -> list[SearchResult]:
        results: list[SearchResult] = []
        for e in entities:
            payload = e.payload or {}
            content = _entity_payload_to_text(e.entity_type, payload)
            results.append(SearchResult(
                urn=e.urn, entity_type=e.entity_type,
                name=e.display_name or e.name,
                score=0.9, datahub_url=e.datahub_url,
                payload={**payload, "content": content},
            ))
        return results


    async def suggest_entity(self, original: str, entity_type: str | None,
                              question: str, trace_id: str) -> Suggestion | None:
        """Find a likely intended entity name for a misspelled one, using the LLM."""
        if not original:
            return None
        if entity_type == "glossary_term":
            entities = await self._ctx.entity_repo.list_all(entity_type="glossary_term", limit=2000)
            candidates = sorted({(e.display_name or e.name) for e in entities})
        elif entity_type == "dataset":
            entities = await self._ctx.entity_repo.list_all(entity_type="dataset", limit=2000)
            candidates = sorted({(e.display_name or e.name) for e in entities})
        else:
            candidates = sorted(await self._ctx.access.collect_domain_names())

        if not candidates:
            return None

        scored: list[tuple[float, str]] = []
        for c in candidates:
            sc = fuzzy_score(original, c)
            if sc >= 0.45:
                scored.append((sc, c))
        scored.sort(key=lambda t: -t[0])
        shortlist = [c for _, c in scored[:10]]
        if not shortlist:
            return None
        log.info("suggestion_shortlist", trace_id=trace_id, original=original,
                 entity_type=entity_type, shortlist=shortlist)

        if len(shortlist) == 1 and scored[0][0] >= 0.65:
            chosen: str | None = scored[0][1]
        # Top candidate clearly dominates the runner-up -> pick it without the LLM.
        elif (len(scored) >= 2
              and scored[0][0] >= 0.65
              and (scored[0][0] - scored[1][0]) >= 0.15):
            chosen = scored[0][1]
        else:
            chosen = await self.llm_pick_suggestion(original, shortlist, question)
        if not chosen:
            return None
        return Suggestion(original=original, suggested=chosen)


    async def llm_pick_suggestion(self, original: str, shortlist: list[str],
                                   question: str) -> str | None:
        """Ask the LLM which candidate is the intended (corrected) name."""
        prompt = (
            "Người dùng đang hỏi về một glossary term hoặc domain trong hệ thống data catalog "
            "nhưng có thể đã gõ sai. Dựa vào ngữ cảnh câu hỏi, hãy chọn tên ĐÚNG NHẤT mà "
            "người dùng muốn hỏi.\n\n"
            f"Câu hỏi: {question}\n"
            f"Tên người dùng đã gõ: '{original}'\n\n"
            "Danh sách ứng viên có sẵn trong hệ thống:\n"
            + "\n".join(f"- {c}" for c in shortlist)
            + "\n\nChỉ trả về đúng một tên ứng viên được chọn. "
              "Nếu không có ứng viên nào khớp ý người dùng, trả về: NONE. "
              "Không thêm giải thích hay dấu câu."
        )
        try:
            raw = (await self._ctx.llm.generate(prompt) or "").strip()
        except Exception:
            log.exception("llm_suggestion_failed")
            return None
        if not raw or raw.upper() == "NONE":
            return None
        best = max(shortlist, key=lambda c: fuzzy_score(raw, c))
        if fuzzy_score(raw, best) >= 0.55:
            return best
        return None


    async def resolve_to_results(self, resolution: ResolutionResult,
                                  trace_id: str | None = None) -> list[SearchResult]:
        from retrieval.hybrid_search import SearchResult
        if resolution.resolved:
            entity_db = await self._ctx.entity_repo.get_by_urn(resolution.resolved.urn)
            if entity_db:
                payload = entity_db.payload or {}
                content = _entity_payload_to_text(entity_db.entity_type, payload)
                log.info("resolve_to_results", trace_id=trace_id,
                         resolved=entity_db.display_name or entity_db.name,
                         urn=entity_db.urn, candidates=len(resolution.candidates))
                return [SearchResult(
                    urn=entity_db.urn, entity_type=entity_db.entity_type,
                    name=entity_db.display_name or entity_db.name,
                    score=1.0, datahub_url=entity_db.datahub_url,
                    payload={**payload, "content": content},
                )]
        log.info("resolve_to_results", trace_id=trace_id,
                 resolved=None, candidates=len(resolution.candidates))
        return []


    async def display_name(self, urn: str) -> str | None:
        entity_db = await self._ctx.entity_repo.get_by_urn(urn)
        return (entity_db.display_name or entity_db.name) if entity_db else None


    async def resolve_followup_entity(
        self, uid: str, cid: str, question: str, history: list[tuple[str, str]],
        active_entities: list[dict],
    ) -> tuple[str | None, str | None]:
        """Resolve what an anaphoric follow-up ("nó", "đó", "...") refers to.

        Priority is: (1) the image-derived dataset while it is still the
        conversation's subject (it is the anaphora target even across a topic
        switch like a document listing, as long as no newer entity superseded
        it); (2) canonical active entities (glossary/dashboard over datasets,
        most recent dataset); (3) the image focus as a final fallback;
        (4) the token heuristic rebuilt from DB history, canonicalised through
        the EntityResolver so "3-Way Matching"-style names resolve even when
        no identifier regex can see them in free text.
        """
        focus = self._ctx.memory.get_image_focus(uid, cid)
        candidates = active_entities or []
        if focus:
            fname = (focus.get("name") or "").lower()
            # The image subject wins while it is still one of the active
            # entities; once a newer explicit subject replaced it in the active
            # list, the conversation has moved on and candidates take over.
            for a in candidates:
                if (a.get("name") or "").lower() == fname:
                    return focus.get("name"), focus.get("entity_type")
        if candidates:
            # A non-dataset active referent (glossary term/document/dashboard) is
            # always the intended subject for "nó". Among datasets, the most
            # recent one wins.
            non_dataset = next(
                (a for a in candidates
                 if (a.get("entity_type") or "dataset") not in ("dataset",)),
                None,
            )
            chosen = non_dataset or candidates[-1]
            return chosen.get("name"), chosen.get("entity_type")
        if focus:
            return focus.get("name"), focus.get("entity_type")
        token = _infer_entity_from_history(history)
        if not token:
            return None, None
        try:
            resolution = await self._ctx.entity_resolver.resolve(token)
        except Exception:  # noqa: BLE001
            return token, None
        if resolution and resolution.resolved:
            return resolution.resolved.name, (
                resolution.resolved.entity_type
                if resolution.resolved.entity_type in ("dataset", "dashboard",
                                                       "glossary_term", "document")
                else None
            )
        return token, None


    async def classify_term_kind(self, question: str, term: str,
                                  has_field_hit: bool,
                                  trace_id: str | None = None) -> str:
        """Use the LLM to decide what kind of entity the user is asking about.

        Returns one of: ``glossary``, ``dataset``, ``field``, or ``unknown``.
        This disambiguates cases like "uom_name là gì?" where the name is a
        column of a dataset (dim_uom) rather than a glossary term.
        """
        if not term:
            return "unknown"
        q_norm = _norm_vn(question)
        mentions_field = bool(
            re.search(
                r"(trường|truong|field|fields|cột|cot|column|columns|"
                r"schema|thuộc tính|thuoc tinh)",
                q_norm, re.I,
            )
        )
        mentions_dataset = bool(
            re.search(r"(dataset|data set|bảng|bang|table|dim_|fact_)", q_norm, re.I)
        )
        # Strong local signals override the LLM call.
        if mentions_field and has_field_hit and not mentions_dataset:
            return "field"
        if mentions_dataset and not mentions_field:
            return "dataset"
        if mentions_field and not has_field_hit:
            return "glossary"

        glossary_hint = await self.fuzzy_name_match(term, "glossary_term")
        dataset_hint = await self.fuzzy_name_match(term, "dataset")
        prompt = (
            "Bạn là trợ lý metadata DataHub. Người dùng đang hỏi về một thuật ngữ dữ liệu.\n"
            f"Câu hỏi: {question}\n"
            f"Tên cần phân loại: '{term}'\n"
            f"Glossary term khớp nhất trong hệ thống: {glossary_hint or 'không có'}\n"
            f"Dataset khớp nhất trong hệ thống: {dataset_hint or 'không có'}\n"
            f"Tên này có xuất hiện như một field (cột) trong dataset không: "
            f"{'CÓ' if has_field_hit else 'KHÔNG'}\n\n"
            "Hãy xác định người dùng đang hỏi về loại thực thể nào:\n"
            "- 'glossary': một glossary term (khái niệm/định nghĩa nghiệp vụ)\n"
            "- 'dataset': một dataset/bảng dữ liệu\n"
            "- 'field': một cột/trường bên trong dataset\n\n"
            "Chỉ trả về ĐÚNG MỘT từ trong ba từ: glossary, dataset, hoặc field. "
            "Không thêm giải thích hay dấu câu."
        )
        try:
            raw = (await self._ctx.llm.generate(prompt) or "").strip().lower()
        except Exception:
            log.exception("llm_term_kind_failed", trace_id=trace_id, term=term)
            return "unknown"
        for kind in ("glossary", "dataset", "field"):
            if kind in raw:
                return kind
        log.warning("llm_term_kind_unparsed", trace_id=trace_id, term=term, raw=raw[:80])
        return "unknown"


    async def fuzzy_name_match(self, term: str, entity_type: str) -> str | None:
        """Best fuzzy match for ``term`` among entities of ``entity_type``."""
        entities = await self._ctx.entity_repo.list_all(entity_type=entity_type, limit=2000)
        best, best_score = None, 0.0
        for e in entities:
            sc = fuzzy_score(term, e.display_name or e.name)
            if sc > best_score:
                best, best_score = (e.display_name or e.name), sc
        return best if best_score >= 0.3 else None


    async def entity_to_result(self, urn: str) -> SearchResult | None:
        entity = await self._ctx.entity_repo.get_by_urn(urn)
        if entity:
            return SearchResult(
                urn=entity.urn, entity_type=entity.entity_type,
                name=entity.display_name or entity.name,
                score=0.9, datahub_url=entity.datahub_url,
                payload=entity.payload,
            )
        return None
