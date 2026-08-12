import re

import structlog

from app.auth.models import UserContext
from app.schemas.actions import SqlResponse
from app.schemas.chat import ChatResponse, EntityItem
from app.services.action_service import ActionService, _schema_columns
from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import _infer_entity_from_history
from app.services.quality_report import render_markdown, render_summary_markdown
from app.services.sql_llm import GroundedSqlGenerator
from guardrails.sanitizer import mask_secrets
from retrieval.intent import _norm_vn

log = structlog.get_logger()


class ChatFlowsService:
    """ChatFlowsService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def enhance_sql(self, question: str, entity, resp) -> SqlResponse:
        """Constrained hybrid pass: ask the LLM to refine the *grounded* SQL,
        then reject anything that references columns outside the schema."""
        if not resp or not getattr(resp, "valid", False):
            return resp
        try:
            gen = GroundedSqlGenerator(self._ctx.generator)
            columns = [
                (f.get("name") or "").strip()
                for f in _schema_columns((entity or {}).payload)
                if (f.get("name") or "").strip()
            ]
            refined = await gen.enhance(
                question, entity.name, columns, resp.sql,
            )
        except Exception:
            log.exception("sql_llm_enhance_failed", dataset=getattr(entity, "name", ""))
            return resp
        if not refined:
            return resp
        return SqlResponse(
            dataset=resp.dataset, urn=resp.urn,
            selected_columns=resp.selected_columns,
            unavailable_columns=resp.unavailable_columns,
            sql=refined, joins=resp.joins,
            explanation=resp.explanation
            + ["SQL được tinh chỉnh bởi AI (chỉ dùng cột đã kiểm tra trong schema)."],
            valid=True,
        )


    async def sql_generation_flow(
        self, question: str, user_ctx: UserContext, trace_id: str,
        cid: str, entity_hint: str | None,
    ) -> ChatResponse | None:
        """Deterministic, grounded SQL generation for a field/query request.

        Priority: (1) an explicit dataset named in the request, (2) a single
        strongly-ranked schema match for the filter field, (3) a clarification
        when several datasets are equally plausible, (4) a grounded "no matching
        schema" explanation. Never falls back to name-substring entity search.
        """
        from app.services.action_service import extract_filter_fields

        svc = ActionService(self._ctx.session, auth_service=self._ctx.auth_service)

        async def _remember(answer: str, cq: str) -> None:
            await self._ctx.memory.add_turn_db(self._ctx.session, user_ctx.user_id, cid, cq, answer)

        async def _sql_response(dataset_name: str, resp) -> ChatResponse:
            if not resp.valid:
                message = resp.explanation[0] if resp.explanation else (
                    "Không thể sinh SQL cho yêu cầu này."
                )
                return ChatResponse(
                    answer=message, intent="SQL_GENERATION", confidence="high",
                    ambiguous=False, insufficient_context=False,
                    trace_id=trace_id, conversation_id=cid,
                )
            block = f"```sql\n{resp.sql}\n```"
            answer_text = (
                f"SQL cho dataset '{dataset_name}':\n\n{block}"
                + ("\n\n" + "\n".join(resp.explanation) if resp.explanation else "")
            )
            await self._ctx.evidence.record_sql_evidence(
                user_ctx.user_id, cid, question, dataset_name, resp,
            )
            resolved = await svc.resolve_dataset(dataset_name, user=user_ctx)
            return ChatResponse(
                answer=answer_text, intent="SQL_GENERATION", confidence="high",
                ambiguous=False, insufficient_context=False,
                entities=[EntityItem(urn=resp.urn, name=resp.dataset,
                                     url=resolved.datahub_url if resolved else None)],
                trace_id=trace_id, conversation_id=cid,
            )

        fields = extract_filter_fields(question)

        # --- (1) An explicit dataset mentioned in the request -----------------
        explicit = None
        if entity_hint:
            explicit = await svc.resolve_dataset(entity_hint, user=user_ctx)
        if explicit is None:
            dataset_tokens = [t for t in re.findall(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+", question, re.I)]
            for tok in dataset_tokens:
                candidate = await svc.resolve_dataset(tok, user=user_ctx)
                if candidate is not None:
                    explicit = candidate
                    break

        if explicit is not None:
            schema = (explicit.payload or {}).get("schema_fields") or []
            norm_to_orig = {
                _norm_vn(f.get("name") or ""): (f.get("name") or "").strip()
                for f in schema
                if isinstance(f, dict) and f.get("name")
            }
            available = [norm_to_orig[ff] for ff in fields if ff in norm_to_orig]
            name = explicit.display_name or explicit.name
            resp = await svc.generate_sql(
                name, requested_columns=available, user=user_ctx,
                question=question,
            )
            resp = await self.enhance_sql(question, explicit, resp)
            answer = await _sql_response(name, resp)
            await _remember(answer.answer, question)
            log.info("sql_flow_explicit", trace_id=trace_id, dataset=name,
                     fields=fields, available=available)
            return answer

        # --- (2)/(3)/(4) field-aware discovery --------------------------------
        candidates = await svc.discover_sql_candidates(question, user=user_ctx)
        if not candidates:
            answer_text = (
                "Không tìm thấy dataset nào trong metadata DataHub có schema "
                "chứa trường lọc bạn yêu cầu"
                + (f" ('{', '.join(fields)}')" if fields else "")
                + ". Không thể sinh SQL khi không xác định được bảng nguồn."
            )
            await _remember(answer_text, question)
            log.info("sql_flow_not_found", trace_id=trace_id, fields=fields)
            return ChatResponse(
                answer=answer_text, intent="SQL_GENERATION", confidence="high",
                ambiguous=False, insufficient_context=True,
                trace_id=trace_id, conversation_id=cid,
            )

        best = candidates[0]
        clear_winner = (
            len(candidates) == 1
            or best.score - candidates[1].score >= 1.5
            or (best.matched_fields and not candidates[1].matched_fields)
        )
        # Context-aware disambiguation: when a filter-field request does not name
        # an explicit dataset and several datasets share the field (e.g.
        # "warehouse_id" exists in dim_warehouse AND many fact_* tables), the
        # dimension table that DEFINES the field is the canonical source of
        # truth. Prefer it instead of asking a clarification for an ambiguity
        # that metadata + naming can already resolve.
        if not clear_winner and best.matched_fields:
            dim_candidates = [
                c for c in candidates
                if (c.entity.name or "").startswith("dim_") and c.matched_fields
            ]
            if dim_candidates:
                best = dim_candidates[0]
                clear_winner = True
                log.info("sql_flow_dim_preferred", trace_id=trace_id,
                         field=best.matched_fields[:1],
                         dataset=best.entity.display_name or best.entity.name)
        if clear_winner:
            name = best.entity.display_name or best.entity.name
            resp = await svc.generate_sql(
                name, requested_columns=best.matched_fields, user=user_ctx,
                question=question,
            )
            resp = await self.enhance_sql(question, best.entity, resp)
            answer = await _sql_response(name, resp)
            await _remember(answer.answer, question)
            log.info("sql_flow_generated", trace_id=trace_id, dataset=name,
                     score=best.score, fields=best.matched_fields)
            return answer

        options = " | ".join(f"'{c.entity.display_name or c.entity.name}'" for c in candidates[:3])
        clarification = (
            f"Có nhiều dataset đều chứa trường "
            f"'{', '.join(best.matched_fields) or ', '.join(fields)}': {options}. "
            "Bạn muốn sinh SQL cho dataset nào?"
        )
        await _remember(clarification, question)
        log.info("sql_flow_clarify", trace_id=trace_id, fields=best.matched_fields,
                 top=[(c.entity.display_name or c.entity.name, c.score) for c in candidates[:3]])
        return ChatResponse(
            answer=clarification, intent="SQL_GENERATION", confidence="low",
            ambiguous=True, insufficient_context=False,
            entities=[EntityItem(urn=c.entity.urn, name=c.entity.display_name or c.entity.name,
                                 url=c.entity.datahub_url) for c in candidates[:3]],
            trace_id=trace_id, conversation_id=cid,
        )


    async def quality_check_flow(
        self, question: str, user_ctx: UserContext, trace_id: str,
        cid: str, entity_hint: str | None,
    ) -> ChatResponse | None:
        """Deterministic metadata-based data quality report for a dataset.

        Picks a dataset (explicit mention, entity hint, then a single history
        reference), runs ``ActionService.quality_check``, and returns the report
        rendered as markdown plus the structured report payload for the export UI.
        """
        svc = ActionService(self._ctx.session, auth_service=self._ctx.auth_service)

        async def _remember(answer: str, cq: str) -> None:
            await self._ctx.memory.add_turn_db(self._ctx.session, user_ctx.user_id, cid, cq, answer)

        async def _report(dataset_name: str) -> ChatResponse | None:
            report = await svc.quality_check(dataset_name, user=user_ctx)
            if not report.valid:
                await _remember(
                    "Không tìm thấy dataset để đánh giá chất lượng.",
                    question,
                )
                return ChatResponse(
                    answer="Không tìm thấy dataset trong metadata DataHub. "
                           "Bạn có thể cho tên dataset cụ thể không?",
                    intent="QUALITY_CHECK", confidence="high",
                    ambiguous=False, insufficient_context=True,
                    trace_id=trace_id, conversation_id=cid,
                )
            wants_full = bool(re.search(
                r"đầy đủ|chi tiết|\bfull\b|toàn bộ|báo cáo đầy đủ|complete",
                question, re.I,
            ))
            answer_text = (
                render_markdown(report) if wants_full
                else render_summary_markdown(report)
            )
            await self._ctx.evidence.record_quality_evidence(
                user_ctx.user_id, cid, question, dataset_name, report,
            )
            await _remember(answer_text, question)
            log.info("quality_flow_report", trace_id=trace_id, dataset=dataset_name,
                     score=report.overall_score, rating=report.rating,
                     sections=len(report.sections))
            return ChatResponse(
                answer=answer_text, intent="QUALITY_CHECK", confidence="high",
                ambiguous=False, insufficient_context=False,
                entities=[EntityItem(urn=report.urn, name=dataset_name, url=report.url)],
                quality_report=report, trace_id=trace_id, conversation_id=cid,
            )

        # (1) Explicit dataset named in the question.
        target = entity_hint
        if target is None:
            tokens = re.findall(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+", question, re.I)
            if tokens:
                target = tokens[0]
        if target is None:
            target = _infer_entity_from_history([(question, "")])
        if target is not None:
            resolution = await self._ctx.entity_resolver.resolve(
                target, entity_type="dataset", trace_id=trace_id,
            )
            if resolution.ambiguous:
                options = " | ".join(
                    f"'{c.name}'" for c in resolution.candidates[:3]
                )
                clarification = (
                    f"Có nhiều dataset khớp với '{target}': {options}. "
                    "Bạn muốn đánh giá chất lượng cho dataset nào?"
                )
                await _remember(clarification, question)
                return ChatResponse(
                    answer=clarification, intent="QUALITY_CHECK", confidence="low",
                    ambiguous=True, insufficient_context=False,
                    entities=[EntityItem(urn=c.urn, name=c.name, url=c.datahub_url)
                              for c in resolution.candidates[:3]],
                    trace_id=trace_id, conversation_id=cid,
                )
            resolved = await svc.resolve_dataset(target, user=user_ctx)
            if resolved is not None:
                return await _report(resolved.display_name or resolved.name)
        return None


    async def sync_relation_flow(
        self, question: str, user_ctx: UserContext, trace_id: str, cid: str,
    ) -> ChatResponse | None:
        """Deterministic "X được sync với gì?" answer.

        A synchronisation/mapping question names a column (typically the primary
        key of a dimension table) and asks which other tables carry the same
        column. Answering is a pure schema scan: every dataset whose schema
        contains the field is a sync/join target.
        """
        fields = re.findall(
            r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+|[a-z0-9]+_[a-z0-9_]+", question,
        )
        if not fields:
            return None
        field = fields[0]
        target = _norm_vn(field).replace(" ", "_")
        datasets = await self._ctx.entity_repo.list_by_type("dataset", limit=2000)
        if self._ctx.auth_service is not None:
            accessible = await self._ctx.auth_service.filter_accessible_urns(
                user_ctx, [e.urn for e in datasets]
            )
            datasets = [e for e in datasets if e.urn in accessible]
        hits = []
        for ds in datasets:
            for f in ((ds.payload or {}).get("schema_fields") or []):
                fname = ((f or {}).get("name") or "").strip()
                if _norm_vn(fname).replace(" ", "_") == target:
                    hits.append(ds)
                    break
        if not hits:
            return None
        lines = [f"Trường '{field}' được dùng làm khóa liên kết/đồng bộ giữa các dataset sau:"]
        for ds in hits[:10]:
            lines.append(f"- {ds.display_name or ds.name}")
        if len(hits) > 10:
            lines.append(f"- ... và {len(hits) - 10} dataset khác")
        answer_text = mask_secrets("\n".join(lines))
        entity_list = [
            EntityItem(urn=ds.urn, name=ds.display_name or ds.name, url=ds.datahub_url)
            for ds in hits[:10]
        ]
        primary = hits[0]
        self._ctx.evidence.record_evidence(
            user_ctx.user_id, cid, kind="sync", entity_name=primary.display_name or primary.name,
            entity_urn=primary.urn, entity_type="dataset",
            structured={
                "name": primary.display_name or primary.name,
                "field": field,
                "related_datasets": [
                    {"urn": d.urn, "name": d.display_name or d.name} for d in hits[:10]
                ],
                "question": question,
            },
            tool_name="schema_sync", question=question, source="sync",
        )
        await self._ctx.evidence.record_active_entities(
            user_ctx.user_id, cid, [], extra=[{
                "name": primary.display_name or primary.name,
                "entity_type": "dataset", "urn": primary.urn,
            }], question=question,
        )
        await self._ctx.memory.add_turn_db(
            self._ctx.session, user_ctx.user_id, cid, question, answer_text,
        )
        log.info("sync_relation_flow", trace_id=trace_id, field=field, hits=len(hits))
        return ChatResponse(
            answer=answer_text, intent="SCHEMA_LOOKUP", entities=entity_list,
            confidence="high", ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=cid,
        )


    async def dataset_terms_flow(
        self, uid: str, cid: str, entity_name: str,
        entity_type: str | None, trace_id: str | None, *, question: str = "",
    ) -> ChatResponse | None:
        """Answer a "Nó có glossary term nào không?" follow-up about a dataset.

        Deterministically lists the glossary terms bound to the conversation's
        active dataset in DataHub. Returns None when the entity is not a dataset
        (caller then routes normally).
        """
        if entity_type not in (None, "dataset"):
            return None
        resolution = await self._ctx.entity_resolver.resolve(
            entity_name, entity_type="dataset", trace_id=trace_id,
        )
        if not resolution or not resolution.resolved:
            return None
        db = await self._ctx.entity_repo.get_by_urn(resolution.resolved.urn)
        if db is None:
            return None
        name = db.display_name or db.name
        term_urns = (db.payload or {}).get("glossary_terms") or []
        rows: list = []
        if not term_urns:
            answer = (
                f"Dataset **{name}** hiện chưa được gán glossary term nào "
                "trong DataHub."
            )
        else:
            all_terms = await self._ctx.entity_repo.list_by_type("glossary_term")
            by_urn = {t.urn: t for t in all_terms}
            rows = [by_urn[u] for u in term_urns if u in by_urn]
            if not rows:
                answer = (
                    f"Dataset **{name}** có {len(term_urns)} glossary term "
                    "liên kết nhưng metadata chưa tải đầy đủ định nghĩa."
                )
            else:
                lines = [
                    f"Dataset **{name}** được gán các glossary term sau:"
                ]
                for t in rows[:8]:
                    desc = (t.payload or {}).get("description") or ""
                    detail = f": {str(desc)[:200]}" if desc else ""
                    lines.append(f"- **{t.display_name or t.name}**{detail}")
                answer = "\n".join(lines)
        log.info("dataset_terms_flow", trace_id=trace_id, dataset=name,
                 glossary_count=len(term_urns))
        self._ctx.evidence.record_evidence(
            uid, cid, kind="dataset_terms", entity_name=name,
            entity_urn=db.urn, entity_type="dataset",
            structured={
                "name": name,
                "terms": [
                    {"urn": t.urn, "name": t.display_name or t.name,
                     "description": str((t.payload or {}).get("description") or "")[:200]}
                    for t in rows[:8]
                ],
                "question": "terms of this dataset",
            },
            tool_name="glossary_terms", question=question, source="glossary",
        )
        return ChatResponse(
            answer=answer, intent="TERMS_FOR_ENTITY", confidence="high",
            ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=cid,
        )


    async def term_datasets_flow(
        self, uid: str, cid: str, term_name: str, trace_id: str | None,
        *, question: str = "",
    ) -> ChatResponse | None:
        """Deterministic "có dataset nào liên quan đến nó không?" for a term.

        Resolves the glossary term and lists the datasets bound to it in DataHub.
        Returns None when the term does not resolve (caller falls through to the
        normal not-found flow).
        """
        resolution = await self._ctx.entity_resolver.resolve(
            term_name, entity_type="glossary_term", trace_id=trace_id,
        )
        if not resolution or not resolution.resolved:
            return None
        term = resolution.resolved
        display = term.name or term_name
        term_urn = term.urn
        all_datasets = await self._ctx.entity_repo.list_by_type("dataset")
        linked = [
            e for e in all_datasets
            if e.payload and term_urn in (e.payload.get("glossary_terms") or [])
        ]
        if not linked:
            answer = (
                f"Glossary term **{display}** có trong DataHub nhưng hiện chưa "
                "được gán cho dataset nào."
            )
        else:
            names = sorted(
                {e.display_name or e.name for e in linked}
            )
            answer = (
                f"Glossary term **{display}** được gán cho {len(linked)} dataset: "
                + ", ".join(names)
            )
        log.info("term_datasets_flow", trace_id=trace_id, term=display,
                 linked_count=len(linked))
        self._ctx.evidence.record_evidence(
            uid, cid, kind="term_datasets", entity_name=display,
            entity_urn=term_urn, entity_type="glossary_term",
            structured={
                "name": display,
                "datasets": [
                    {"urn": e.urn, "name": e.display_name or e.name}
                    for e in linked[:10]
                ],
                "question": "datasets bound to this term",
            },
            tool_name="term_to_datasets", question=question, source="glossary",
        )
        return ChatResponse(
            answer=answer, intent="TERM_TO_DATASETS", confidence="high",
            ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=cid,
        )
