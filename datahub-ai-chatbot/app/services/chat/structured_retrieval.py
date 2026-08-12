import re
from typing import Any

import structlog

from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import (
    _TERM_REMOVE_WORDS,
    _entity_payload_to_text,
    _extract_entity_like,
    _extract_field_identifier,
    _extract_filter_value,
    _extract_identifiers,
    _extract_name,
    _is_noisy_entity,
    _looks_like_join,
    _trusted_resolution,
)
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent, _norm_vn

log = structlog.get_logger()


class StructuredRetrievalService:
    """StructuredRetrievalService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def structured_retrieval(self, intent: QueryIntent, question: str,
                                    inferred_entity: str | None = None,
                                    inferred_type: str | None = None,
                                    trace_id: str | None = None) -> list[SearchResult]:
        from retrieval.hybrid_search import SearchResult

        if intent == QueryIntent.TERM_DEFINITION:
            # Acronym terms (KPI, OEE, JIT, PO, GRN...) defeat the natural-language
            # extractor when the rest of the sentence is ambiguous ("Term là gì?
            # KPI"). A term/glossary question naming an uppercase acronym uses it
            # directly - it is an explicit, deterministic glossary-term signal.
            term_name = None
            term_is_acronym = False
            if inferred_entity:
                term_name = inferred_entity
            else:
                am = re.search(r"\b[A-Z]{2,8}(?:-[A-Z]+)*\b", question)
                if am:
                    term_name = am.group(0)
                    term_is_acronym = True
            if not term_name:
                term_name = await self._ctx.entities.entity_name_for(
                    question, _TERM_REMOVE_WORDS, trace_id=trace_id,
                )
            if not term_name:
                log.info("structured_no_name", trace_id=trace_id, intent=intent.value,
                         question=question[:100])
                return []
            # Implicit field reference: the user names a column directly
            # ("warehouse_id là gì?") without the words "trường/field". The
            # snake_case identifier is preserved so we look it up as a schema
            # field FIRST, before the glossary resolver can normalize
            # "warehouse id" into an unrelated fuzzy match and steal the answer.
            field_ident = _extract_field_identifier(question)
            if field_ident and not inferred_entity:
                field_results = await self.resolve_field_lookup(field_ident, trace_id=trace_id)
                if field_results:
                    log.info("structured_implicit_field", trace_id=trace_id,
                             field=field_ident, hits=len(field_results),
                             question=question[:100])
                    return field_results
            # "dataset/dashboard X là gì ?" must resolve the requested type, not a
            # glossary term. Fall back to glossary_term only when no type is named.
            q = question.lower()
            preferred_types: list[str] = []
            if inferred_type == "glossary_term":
                preferred_types = ["glossary_term", "dataset", "dashboard"]
            elif inferred_type in ("dataset", "dashboard"):
                preferred_types = [inferred_type, "glossary_term"]
            elif "dataset" in q or "data set" in q or "bảng" in q or "bảng số" in q:
                preferred_types = ["dataset", "dashboard", "glossary_term"]
            elif "dashboard" in q or "report" in q:
                preferred_types = ["dashboard", "dataset", "glossary_term"]
            else:
                preferred_types = ["glossary_term", "dataset", "dashboard"]
            last_error = None
            for etype in preferred_types:
                resolution = await self._ctx.entities.resolve_with_expansion(
                    term_name, question, entity_type=etype, trace_id=trace_id)
                if resolution and _trusted_resolution(resolution):
                    return await self._ctx.entities.resolve_to_results(
                        resolution, trace_id=trace_id,
                    )
                last_error = resolution or last_error
            # Pure acronym that is NOT a catalog term: a "field escaping" fallback
            # or an LLM kind-classifier would just blur it into an unrelated
            # result. Deterministically fall through to the not-found/suggestion
            # path so the acronym itself is named in the answer.
            if term_is_acronym:
                log.info("structured_acronym_unresolved", trace_id=trace_id,
                         term=term_name)
                return []
            # No trusted glossary/dataset match. The name may be a FIELD (column)
            # inside a dataset (e.g. "uom_name" in dataset "dim_uom"). Use the LLM
            # to decide what the user is actually asking about before giving up.
            field_results = await self.resolve_field_lookup(term_name, trace_id=trace_id)
            kind = await self._ctx.entities.classify_term_kind(
                question, term_name, has_field_hit=bool(field_results), trace_id=trace_id)
            log.info("structured_low_trust", trace_id=trace_id, term=term_name,
                     top=last_error.resolved.name if last_error and last_error.resolved else None,
                     top_score=(
                         last_error.resolved.score
                         if last_error and last_error.resolved else None
                     ),
                     llm_kind=kind, field_hits=len(field_results))
            if kind == "field" and field_results:
                return field_results
            if kind == "glossary":
                resolution = await self._ctx.entity_resolver.resolve(
                    term_name, entity_type="glossary_term", trace_id=trace_id)
                if resolution.resolved and _trusted_resolution(resolution):
                    return await self._ctx.entities.resolve_to_results(
                        resolution, trace_id=trace_id,
                    )
            if kind == "dataset":
                resolution = await self._ctx.entity_resolver.resolve(
                    term_name, entity_type="dataset", trace_id=trace_id)
                if resolution.resolved and _trusted_resolution(resolution):
                    return await self._ctx.entities.resolve_to_results(
                        resolution, trace_id=trace_id,
                    )
            if field_results:
                return field_results
            return []

        if intent == QueryIntent.OWNER_LOOKUP:
            entity_name = inferred_entity or await self._ctx.entities.entity_name_for(question, [
                "ai sở hữu", "ai là", "ai la", "ai là chủ", "business owner",
                "owner", "của ai", "cua ai", "who owns", "who is the owner of",
                "thuộc về ai", "thuộc ai", "thuộc sở hữu", "sở hữu của ai",
                "thuộc về", "thuộc", "người sở hữu", "chủ sở hữu",
                "belongs to whom", "owned by whom", "whose",
            ], prefer_type="dataset", trace_id=trace_id)
            resolution = await self._ctx.entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._ctx.entities.resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.ENTITY_DOMAIN:
            entity_name = inferred_entity or await self._ctx.entities.entity_name_for(question, [
                "thuộc về domain", "thuộc domain", "thuộc lĩnh vực", "thuộc miền",
                "thuộc về", "thuộc", "domain nào", "lĩnh vực nào", "miền nào",
                "domain của", "lĩnh vực của", "nằm trong",
                "belongs to which domain", "which domain", "what domain",
                "belongs to", "belong to", "does it belong", "belongs",
                "belong", "does", "thuộc của",
                "là gì", "la gi", "nào", "nao",
            ])
            if not entity_name:
                entity_name = inferred_entity or ""
            resolution = await self._ctx.entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._ctx.entities.resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.TERM_TO_DATASETS:
            # Field-location questions ("warehouse_id thuộc dataset nào?",
            # "promotion_id nằm trong dataset nào?") occasionally route here
            # instead of SCHEMA_LOOKUP/TERM_DEFINITION. When the question names a
            # column directly and asks where it lives, answer from the schema
            # field lookup - the glossary-term flow would otherwise canonicalize
            # e.g. "warehouse_id" into an unrelated term such as "WMS" and answer
            # "term chưa được gắn".
            field_ident = _extract_field_identifier(question)
            if field_ident and re.search(
                r"(nằm trong|nam trong|thuộc|thuoc|nằm ở|trong dataset|của bảng|"
                r"of (dataset|table)|in (dataset|table)|trong bảng)",
                question,
            ):
                field_results = await self.resolve_field_lookup(
                    field_ident, trace_id=trace_id)
                if field_results:
                    log.info("structured_field_to_datasets", trace_id=trace_id,
                             field=field_ident, hits=len(field_results),
                             question=question[:100])
                    return field_results
            term_name = inferred_entity or await self._ctx.entities.entity_name_for(question, [
                "dataset nào gắn term", "dataset nào có term",
                "find dataset", "entity nào gắn", "gắn term",
            ], prefer_type="glossary_term", trace_id=trace_id)
            if not term_name:
                log.info("structured_no_term", trace_id=trace_id, intent=intent.value,
                         question=question[:100])
                return []
            resolution = await self._ctx.entity_resolver.resolve(
                term_name, entity_type="glossary_term",
                trace_id=trace_id,
            )
            if resolution.resolved and _trusted_resolution(resolution):
                all_entities = await self._ctx.entity_repo.list_by_type("dataset")
                term_urn = resolution.resolved.urn
                # Synonym closure: datasets are often linked to the term under a
                # different vocabulary (e.g. term "Revenue" lives in the catalog
                # as urn:...:Revenue, but datasets carry its Vietnamese sibling
                # urn:...:doanh_thu). Expand the term's synonyms and look up
                # datasets by ANY of the linked term URNs.
                linked_urns = {term_urn}
                try:
                    expansion = self._ctx.semantic.expand(term_name)
                    for st in expansion.terms[1:]:
                        syn_res = await self._ctx.entity_resolver.resolve(
                            st, entity_type="glossary_term", trace_id=trace_id)
                        if syn_res.resolved:
                            linked_urns.add(syn_res.resolved.urn)
                except Exception:  # noqa: BLE001
                    pass
                matching = [
                    e for e in all_entities
                    if e.payload and (
                        set(e.payload.get("glossary_terms") or []) & linked_urns
                    )
                ]
                results: list[SearchResult] = []
                for e in matching:
                    payload = e.payload or {}
                    content = _entity_payload_to_text(e.entity_type, payload)
                    results.append(SearchResult(
                        urn=e.urn, entity_type=e.entity_type, name=e.display_name or e.name,
                        score=0.9, datahub_url=e.datahub_url,
                        payload={**payload, "content": content},
                    ))
                if not results:
                    # The term IS in the catalog but no dataset is linked to it.
                    # Return the term itself as the single grounded result so the
                    # pipeline can answer "not used by any dataset" deterministically
                    # instead of reporting a bogus "not found" for the term.
                    term_db = await self._ctx.entity_repo.get_by_urn(term_urn)
                    if term_db:
                        payload = term_db.payload or {}
                        content = _entity_payload_to_text(term_db.entity_type, payload)
                        results.append(SearchResult(
                            urn=term_db.urn, entity_type=term_db.entity_type,
                            name=term_db.display_name or term_db.name, score=0.7,
                            datahub_url=term_db.datahub_url,
                            payload={**payload, "content": content},
                        ))
                log.info("structure_term_to_datasets", trace_id=trace_id, term=term_name,
                         matching=len(matching))
                if not any(r.entity_type == "dataset" for r in results):
                    # The exact term resolved but datasets carry the linkage under
                    # a DIFFERENT vocabulary (e.g. catalog term "Revenue" vs the
                    # datasets' linked urn ...:doanh_thu). Fall back to the concept
                    # mapper, which unifies term synonyms with the dataset-side
                    # glossary URNs and returns datasets rather than "chưa".
                    concept = await self.term_concept_to_datasets(
                        term_name, question, trace_id=trace_id,
                    )
                    dataset_results = [r for r in concept if r.entity_type == "dataset"]
                    if dataset_results:
                        log.info("structure_term_via_concept", trace_id=trace_id,
                                 term=term_name, datasets=len(dataset_results))
                        return dataset_results
                return results
            # Concept query fallback: the phrase is a concept ("doanh thu",
            # "hàng tồn kho", "chất lượng") rather than an exact term name.
            # Expand it semantically, find matching glossary terms, then map each
            # term to datasets whose name/description overlap its keywords.
            return await self.term_concept_to_datasets(term_name, question,
                                                        trace_id=trace_id)

        if intent == QueryIntent.LINEAGE:
            entity_name = inferred_entity or await self._ctx.entities.entity_name_for(question, [
                "lấy dữ liệu từ đâu", "upstream", "downstream",
                "nguồn", "phụ thuộc", "source of data",
                "thông tin về lineage", "thông tin về linage",
                "lineage", "linage", "thông tin", "thong tin",
                "luồng dữ liệu", "dòng dữ liệu", "luong du lieu", "dong du lieu",
                "data flow", "flow of data", "như nào", "nhu nao", "như thế nào",
            ], prefer_type="dataset", trace_id=trace_id)
            resolution = await self._ctx.entity_resolver.resolve(entity_name, entity_type="dataset",
                                                             trace_id=trace_id)
            if resolution.resolved:
                entity_db = await self._ctx.entity_repo.get_by_urn(resolution.resolved.urn)
                if entity_db and entity_db.payload:
                    main_content = _entity_payload_to_text(
                        entity_db.entity_type, entity_db.payload,
                    )

                    upstreams: list[str] = []
                    downstreams: list[str] = []
                    try:
                        up = await self._ctx.source.get_lineage(entity_db.urn, direction="upstream")
                        down = await self._ctx.source.get_lineage(
                            entity_db.urn, direction="downstream",
                        )
                        upstreams = [r["entity"]["urn"] for r in up.get("relationships", [])
                                     if (r.get("entity") or {}).get("urn")]
                        downstreams = [r["entity"]["urn"] for r in down.get("relationships", [])
                                       if (r.get("entity") or {}).get("urn")]
                    except Exception:
                        log.exception("lineage_live_failed", trace_id=trace_id, urn=entity_db.urn)
                    # When the live source returns no lineage (mock mode, or the
                    # source is offline), fall back to the persisted metadata so
                    # stored upstream/downstream relations still answer the query.
                    if not upstreams and not downstreams:
                        upstreams = list(entity_db.payload.get("upstreams") or [])
                        downstreams = list(entity_db.payload.get("downstreams") or [])

                    log.info("structure_lineage", trace_id=trace_id,
                             entity=entity_db.display_name or entity_db.name,
                             upstream_count=len(upstreams), downstream_count=len(downstreams),
                             source="live")

                    payload = {
                        **entity_db.payload,
                        "upstreams": upstreams,
                        "downstreams": downstreams,
                        "content": (
                            f"Entity: {main_content}\n"
                            "Upstream: "
                            f"{', '.join(upstreams) if upstreams else 'None'}\n"
                            "Downstream: "
                            f"{', '.join(downstreams) if downstreams else 'None'}"
                        ),
                    }
                    results: list[SearchResult] = []
                    results.append(SearchResult(
                        urn=entity_db.urn, entity_type=entity_db.entity_type,
                        name=entity_db.display_name or entity_db.name,
                        score=1.0, datahub_url=entity_db.datahub_url,
                        payload=payload,
                    ))

                    async def _related(urn: str, score: float) -> SearchResult:
                        rel_entity = await self._ctx.entity_repo.get_by_urn(urn)
                        name = (rel_entity.display_name or rel_entity.name) if rel_entity else urn
                        content = _entity_payload_to_text(
                            rel_entity.entity_type if rel_entity else "dataset",
                            rel_entity.payload if rel_entity else {},
                        ) if rel_entity else urn
                        return SearchResult(
                            urn=urn,
                            entity_type=rel_entity.entity_type if rel_entity else "dataset",
                            name=name, score=score,
                            datahub_url=rel_entity.datahub_url if rel_entity else None,
                            payload={"content": f"Related entity: {content}"},
                        )

                    for u in upstreams:
                        results.append(await _related(u, 0.8))
                    for d in downstreams:
                        results.append(await _related(d, 0.75))
                    return results
            return []

        if intent == QueryIntent.SCHEMA_LOOKUP:
            # Schema / join question across two datasets ("trường nào dùng để
            # liên kết X với Y?") -> resolve both schemas and infer join keys
            # from real metadata, never by extracting the whole sentence as a name.
            if _looks_like_join(question):
                join_results = await self.schema_join_lookup(question, trace_id=trace_id)
                if join_results:
                    log.info("structured_schema_join", trace_id=trace_id,
                             question=question[:100], result_count=len(join_results))
                    return join_results
            entity_name = inferred_entity or await self._ctx.entities.entity_name_for(question, [
                "field", "schema", "cột", "trường", "có những",
                "columns", "fields", "thuộc tính",
            ], prefer_type="dataset", trace_id=trace_id)
            resolution = await self._ctx.entity_resolver.resolve(entity_name, entity_type="dataset",
                                                             trace_id=trace_id)
            if resolution.resolved and _trusted_resolution(resolution):
                return await self._ctx.entities.resolve_to_results(resolution, trace_id=trace_id)
            # The asked name may be a FIELD (column) inside one or more datasets,
            # e.g. "trường uom_name là gì?" -> uom_name belongs to dataset dim_uom.
            field_results = await self.resolve_field_lookup(entity_name, trace_id=trace_id)
            if field_results:
                log.info("structured_field_lookup", trace_id=trace_id,
                         field=entity_name, datasets=len(field_results))
                return field_results
            return await self._ctx.entities.resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.DATAHUB_URL:
            entity_name = inferred_entity or _extract_name(question, [
                "link", "url", "datahub", "đường dẫn",
            ])
            resolution = await self._ctx.entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._ctx.entities.resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.ENTITY_EXISTS:
            entity_name = inferred_entity or _extract_name(question, [
                "có tồn tại", "tồn tại không", "exist",
                "có không", "does.*exist",
            ])
            resolution = await self._ctx.entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._ctx.entities.resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.CERTIFIED_LIST:
            entities = await self._ctx.entity_repo.list_certified()
            return self._ctx.entities.entities_to_results(entities)

        if intent in (QueryIntent.DOMAIN_QUERY, QueryIntent.PLATFORM_QUERY,
                      QueryIntent.TAG_QUERY, QueryIntent.ENTITIES_BY_OWNER):
            value = inferred_entity or _extract_filter_value(question, intent)
            if not value:
                return []
            log.info("structured_filter", trace_id=trace_id, intent=intent.value,
                     value=value, question=question[:100])
            if intent == QueryIntent.DOMAIN_QUERY:
                entities = await self._ctx.entity_repo.list_by_domain(value)
            elif intent == QueryIntent.PLATFORM_QUERY:
                entities = await self._ctx.entity_repo.list_by_platform(value)
            elif intent == QueryIntent.TAG_QUERY:
                entities = await self._ctx.entity_repo.list_by_tag(value)
            else:
                entities = await self._ctx.entity_repo.list_by_owner(value)
            log.info("structured_filter_result", trace_id=trace_id, intent=intent.value,
                     value=value, count=len(entities))
            return self._ctx.entities.entities_to_results(entities)

        return []


    async def recursive_impact_retrieval(self, plan,
                                          question: str,
                                          suggested_name: str | None = None,
                                          trace_id: str | None = None) -> list[SearchResult]:
        """Run recursive downstream impact analysis for an IMPACT question.

        Uses the metadata graph (BFS over lineage) to gather all consumers within
        ``depth`` hops so the generator can explain the blast radius of changing
        or removing an entity.
        """
        from config.settings import settings as _settings

        name = (plan.primary_entity or suggested_name or "").strip()
        # Root-cause fix for "xoa dim warehouse thi bi anh huong": the regex
        # fallback emits a whole-sentence phrase. The entity extractor scans the
        # question against real catalog names and returns the actual entity.
        extraction_note = None
        if _is_noisy_entity(name):
            extracted = await self._ctx.entity_extractor.resolve_primary_dataset(question)
            name = (extracted.name if extracted else None) \
                or suggested_name \
                or _extract_entity_like(question) \
                or name
            extraction_note = extracted.name if extracted else None
        params: dict = {"name": name}
        if plan.params.depth:
            params["depth"] = plan.params.depth
        results = await self._ctx.tools.execute("recursive_impact", params)
        log.info("recursive_impact", trace_id=trace_id, question=question[:100],
                 entity=name, depth=params.get("depth", _settings.IMPACT_DEFAULT_DEPTH),
                 result_count=len(results), extraction_note=extraction_note,
                 impact_summary=(results[0].payload or {}).get("impact_summary")
                 if results else None)
        return results


    async def term_concept_to_datasets(
        self, concept: str, question: str,
        trace_id: str | None = None,
    ) -> list[SearchResult]:
        """Resolve a TERM_TO_DATASETS concept query (e.g. "doanh thu", "tồn
        kho") into matching glossary terms + datasets that mention them.

        Runs when the extracted name is not an exact glossary term: the term is
        expanded through the synonym table, glossary terms are scored by keyword
        overlap with the expansion, and the top terms are returned together with
        datasets whose name or description mentions the term keywords.
        """
        from retrieval.hybrid_search import SearchResult
        from retrieval.semantic_expansion import expand as _expand

        expanded = _expand(concept)
        keywords = [t for t in expanded.terms if len(t) > 2]
        norm_keywords = [_norm_vn(t) for t in keywords]
        if not norm_keywords:
            return []

        terms = await self._ctx.entity_repo.list_by_type("glossary_term", limit=2000)
        scored: list[tuple[float, str]] = []
        for t in terms:
            payload = t.payload or {}
            blob = _norm_vn(t.name) + " " + _norm_vn(payload.get("description") or "")
            score = sum(1 for k in norm_keywords if k and k in blob)
            if score:
                scored.append((score, t.urn))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top_terms = [urn for _, urn in scored[:3]]
        log.info("term_concept_matched", trace_id=trace_id, concept=concept[:80],
                 keywords=keywords[:8], matched_terms=len(scored))

        results: list[SearchResult] = []
        seen: set[str] = set()
        term_keywords = [
            _norm_vn(x)
            for urn in top_terms
            for x in [await self._ctx.entities.display_name(urn)] if x
        ]
        for urn in top_terms:
            entity_db = await self._ctx.entity_repo.get_by_urn(urn)
            if not entity_db:
                continue
            payload = entity_db.payload or {}
            content = _entity_payload_to_text(entity_db.entity_type, payload)
            results.append(SearchResult(
                urn=entity_db.urn, entity_type=entity_db.entity_type,
                name=entity_db.display_name or entity_db.name,
                score=0.95, datahub_url=entity_db.datahub_url,
                payload={**payload, "content": content},
            ))
            seen.add(entity_db.urn)

        all_keys = norm_keywords + term_keywords
        # Glossary-linking: datasets carry the term via their "glossary_terms"
        # URNs (e.g. urn:li:glossaryTerm:doanh_thu). If a matched glossary term
        # is actually LINKED to datasets, those are the authoritative matches —
        # datasets whose name/description happen to mention a synonym are only a
        # text-based supplement. Without this, "Term Revenue được gắn cho dataset
        # nào?" would never surface sales.orders, whose description does not
        # literally contain "revenue"/"doanh thu".
        term_slugs = {u.rsplit(":", 1)[-1].lower() for u in top_terms}
        datasets = await self._ctx.entity_repo.list_by_type("dataset", limit=2000)
        dataset_hits: list[Any] = []
        text_hits: list[Any] = []
        for ds in datasets:
            if ds.urn in seen:
                continue
            payload = ds.payload or {}
            ds_terms = [
                (str(t) or "").rsplit(":", 1)[-1].lower()
                for t in (payload.get("glossary_terms") or [])
            ]
            if term_slugs and (set(ds_terms) & term_slugs):
                dataset_hits.append(ds)
                continue
            blob = _norm_vn(ds.name) + " " + _norm_vn(payload.get("description") or "")
            if any(k and k in blob for k in all_keys):
                text_hits.append(ds)
        for ds in dataset_hits + text_hits:
            payload = ds.payload or {}
            content = _entity_payload_to_text(ds.entity_type, payload)
            results.append(SearchResult(
                urn=ds.urn, entity_type=ds.entity_type,
                name=ds.display_name or ds.name,
                score=0.85 if ds in dataset_hits else 0.7,
                datahub_url=ds.datahub_url,
                payload={**payload, "content": content},
            ))
            seen.add(ds.urn)
            if len([r for r in results if r.entity_type == "dataset"]) >= 8:
                break
        log.info("term_concept_to_datasets", trace_id=trace_id, concept=concept[:80],
                 terms=len(top_terms), datasets=sum(1 for r in results
                                                    if r.entity_type == "dataset"))
        return results


    async def resolve_field_lookup(self, field_name: str,
                                    trace_id: str | None = None) -> list[SearchResult]:
        """Find the dataset(s) that contain a schema field named ``field_name``.

        Returns a SearchResult per matching dataset whose content highlights the
        field, so the generator can explain what the column means.
        """
        from retrieval.hybrid_search import SearchResult
        if not field_name:
            return []
        target = _norm_vn(field_name).replace(" ", "_")
        datasets = await self._ctx.entity_repo.list_by_type("dataset", limit=2000)
        results: list[SearchResult] = []
        seen_urns: set[str] = set()
        for ds in datasets:
            if ds.urn in seen_urns:
                continue
            fields = (ds.payload or {}).get("schema_fields") or []
            match = None
            for f in fields:
                fname = (f or {}).get("name") or ""
                if _norm_vn(fname).replace(" ", "_") == target:
                    match = f
                    break
            if match is None:
                continue
            seen_urns.add(ds.urn)
            payload = {**(ds.payload or {})}
            fdesc = (match.get("description") or "").strip()
            ftype = (match.get("type") or "").strip()
            field_line = f"- {match.get('name', field_name)} ({ftype})"
            if fdesc:
                field_line += f": {fdesc}"
            content = _entity_payload_to_text(ds.entity_type, payload)
            content = (
                f"Trường '{match.get('name', field_name)}' thuộc dataset "
                f"{ds.display_name or ds.name}:\n{field_line}\n\n{content}"
            )
            results.append(SearchResult(
                urn=ds.urn, entity_type=ds.entity_type,
                name=ds.display_name or ds.name,
                score=0.95, datahub_url=ds.datahub_url,
                payload={**payload, "content": content},
            ))
        # Prefer the canonical (dimension) tables: a field like "warehouse_id"
        # lives in dim_warehouse as the key AND in many fact_* tables as an FK.
        # The dimension definition is the source of truth, so when it exists we
        # answer from it instead of listing every referencing fact table.
        if len(results) > 1:
            dims = [r for r in results if (r.name or "").startswith("dim_")]
            if dims:
                results = dims[:3]
        log.info("field_lookup", trace_id=trace_id, field=field_name, hits=len(results))
        return results


    async def schema_join_lookup(
        self, question: str, trace_id: str | None = None,
    ) -> list[SearchResult]:
        """Resolve two datasets from a schema-join question and infer join keys.

        Grounded only: reports real shared field names when they exist, otherwise
        states that no direct key is mapped and lists the candidate FK columns.
        """
        from retrieval.hybrid_search import SearchResult

        idents = _extract_identifiers(question)
        resolved: list[dict] = []
        seen: set[str] = set()
        for cand in idents:
            try:
                res = await self._ctx.entity_resolver.resolve(
                    cand, entity_type="dataset", trace_id=trace_id,
                )
            except Exception:  # noqa: BLE001
                continue
            if not res or not res.resolved or res.resolved.urn in seen:
                continue
            seen.add(res.resolved.urn)
            db = await self._ctx.entity_repo.get_by_urn(res.resolved.urn)
            if db is None:
                continue
            payload = db.payload or {}
            resolved.append({
                "name": db.display_name or db.name,
                "urn": db.urn,
                "payload": payload,
                "fields": [
                    f.get("name") or "" for f in (payload.get("schema_fields") or [])
                ],
            })
        if len(resolved) < 2:
            return []

        def _norm(s: str) -> str:
            return s.strip().lower().replace(" ", "_")

        primary, targets = resolved[0], resolved[1:]
        lines: list[str] = [f"### Liên kết giữa {primary['name']} và các bảng khác"]
        for t in targets:
            t_set = {_norm(f) for f in t["fields"] if f}
            shared = [f for f in primary["fields"] if f and _norm(f) in t_set]
            fk_candidates = [
                f for f in primary["fields"]
                if f and _norm(f).endswith(("_id", "_key", "_code"))
                and _norm(f) not in t_set
            ]
            if shared:
                lines.append(
                    f"- **{t['name']}**: liên kết qua trường cùng tên "
                    f"**{', '.join(shared)}**."
                )
            else:
                fk_txt = ", ".join(fk_candidates[:8]) or "không có"
                lines.append(
                    f"- **{t['name']}**: trong metadata hiện có, không có trường "
                    f"nào của {primary['name']} trùng tên với trường của "
                    f"{t['name']}. Các trường dạng khóa của {primary['name']} "
                    f"({fk_txt}) chưa được map thành quan hệ ngoại khóa "
                    "tới bảng này."
                )
        lines.append(
            "> Trả lời dựa trên schema & metadata hiện có trong DataHub."
        )
        content = "Schema join analysis:\n" + "\n".join(lines)
        body = {
            **primary["payload"],
            "content": content,
            "join_analysis": "\n".join(lines),
        }
        return [SearchResult(
            urn=primary["urn"], entity_type="dataset", name=primary["name"],
            score=1.0, datahub_url=None, payload=body,
        )]
