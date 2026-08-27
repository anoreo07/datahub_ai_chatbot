import re
from typing import Any

import structlog

from app.schemas.chat import ChatResponse, EntityItem
from app.services.chat.context import ChatContext
from app.services.chat.field_ops import answer_field_op
from app.services.chat.question_analysis import (
    _evidence_kind_for_intent,
    _evidence_tool_name,
    _extract_identifiers,
    _extract_join_field,
    _extract_lineage_keyword,
    _find_target_entity,
    _has_own_identifier,
    _name_from_urn,
    _normalize_field,
)
from retrieval.context_resolver import ContextResolution
from retrieval.evidence import FieldOp, format_fields, has_context_reference
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent, _norm_vn

log = structlog.get_logger()


class EvidenceService:
    """EvidenceService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    def record_evidence(
        self, uid: str, cid: str, *, kind: str, entity_name: str,
        entity_urn: str | None, entity_type: str | None, structured: dict,
        tool_name: str, question: str, source: str = "retrieval",
    ) -> None:
        """Append a structured metadata extract (E1, E2, ...) to the turn."""
        if not entity_name:
            return
        self._ctx.memory.record_evidence(uid, cid, {
            "kind": kind,
            "entity_name": entity_name,
            "entity_urn": entity_urn,
            "entity_type": entity_type,
            "tool_name": tool_name,
            "query": question,
            "structured": structured,
            "source": source,
        })


    async def record_sql_evidence(
        self, uid: str, cid: str, question: str, dataset_name: str,
        resp,
    ) -> None:
        """Record the generated SQL + resolved schema as reusable evidence so a
        follow-up ("owner của nó", "các trường của nó") is answered from this
        turn rather than re-searched."""
        urn = getattr(resp, "urn", None)
        columns = [c for c in (getattr(resp, "selected_columns", None) or []) if c]
        owners: list[str] = []
        domain = None
        if urn:
            try:
                db = await self._ctx.entity_repo.get_by_urn(urn)
            except Exception:  # noqa: BLE001
                db = None
            if db is not None and (db.payload or {}):
                owners = list(db.payload.get("owners") or [])
                domain = db.payload.get("domain")
                if not columns:
                    columns = [
                        (f.get("name") or "").strip()
                        for f in (db.payload.get("schema_fields") or [])
                        if (f.get("name") or "").strip()
                    ]
        self.record_evidence(
            uid, cid, kind="sql", entity_name=dataset_name,
            entity_urn=urn, entity_type="dataset",
            structured={
                "name": dataset_name,
                "fields": columns,
                "sql": getattr(resp, "sql", None),
                "joins": getattr(resp, "joins", None),
                "owners": owners,
                "domain": domain,
                "question": question,
            },
            tool_name="sql_generator", question=question, source="sql",
        )
        await self.record_active_entities(
            uid, cid, [], extra=[{
                "name": dataset_name, "entity_type": "dataset", "urn": urn,
            }], question=question,
        )


    async def record_quality_evidence(
        self, uid: str, cid: str, question: str, dataset_name: str,
        report,
    ) -> None:
        """Record the quality report as reusable evidence for follow-ups."""
        sections = [
            {"name": s.title, "score": getattr(s, "score", None)}
            for s in (getattr(report, "sections", None) or [])
        ]
        owners: list[dict] = []
        domain = None
        urn = getattr(report, "urn", None)
        if urn:
            try:
                db = await self._ctx.entity_repo.get_by_urn(urn)
            except Exception:  # noqa: BLE001
                db = None
            if db is not None and (db.payload or {}):
                owners = list(db.payload.get("owners") or [])
                domain = db.payload.get("domain")
        self.record_evidence(
            uid, cid, kind="quality", entity_name=dataset_name,
            entity_urn=urn, entity_type="dataset",
            structured={
                "name": dataset_name,
                "overall_score": getattr(report, "overall_score", None),
                "rating": getattr(report, "rating", None),
                "sections": sections,
                "owners": owners,
                "domain": domain,
                "question": question,
            },
            tool_name="quality_check", question=question, source="quality",
        )
        await self.record_active_entities(
            uid, cid, [], extra=[{
                "name": dataset_name, "entity_type": "dataset",
                "urn": urn,
            }], question=question,
        )


    async def record_evidence_from_results(
        self, uid: str, cid: str, question: str, intent: "QueryIntent",
        results: list[SearchResult],
    ) -> None:
        """Record the structured data the main pipeline produced this turn."""
        if not results:
            return
        best = results[0]
        payload = best.payload or {}
        best_payload = payload if isinstance(payload, dict) else {}
        kind = _evidence_kind_for_intent(intent, best_payload)
        if kind is None:
            return
        schema_fields = best_payload.get("schema_fields") or []
        structured: dict[str, Any] = {
            "name": (
                best_payload.get("display_name")
                or best_payload.get("name") or best.name
            ),
            "description": best_payload.get("description"),
            "domain": best_payload.get("domain"),
            "platform": best_payload.get("platform"),
            "owners": list(best_payload.get("owners") or []),
            "fields": [
                (f.get("name") or "").strip()
                for f in schema_fields if (f.get("name") or "").strip()
            ],
            "schema_fields": schema_fields,
            "glossary_terms": list(best_payload.get("glossary_terms") or []),
            "upstreams": list(best_payload.get("upstreams") or []),
            "downstreams": list(best_payload.get("downstreams") or []),
            "join_analysis": best_payload.get("join_analysis"),
        }
        join_field = _extract_join_field(question)
        if join_field:
            structured["join_field"] = join_field
        self.record_evidence(
            uid, cid, kind=kind, entity_name=best.name,
            entity_urn=best.urn, entity_type=best.entity_type,
            structured=structured, tool_name=_evidence_tool_name(intent),
            question=question,
        )


    async def record_image_evidence(
        self, uid: str, cid: str, question: str,
        image_entity: str, image_urn: str | None,
    ) -> None:
        """Record the image-derived dataset's real metadata as evidence."""
        db = None
        if image_urn:
            try:
                db = await self._ctx.entity_repo.get_by_urn(image_urn)
            except Exception:  # noqa: BLE001
                db = None
        payload = (db.payload or {}) if db is not None else {}
        schema_fields = payload.get("schema_fields") or []
        structured: dict[str, Any] = {
            "name": (db.display_name or db.name) if db is not None else image_entity,
            "description": payload.get("description"),
            "domain": payload.get("domain"),
            "owners": list(payload.get("owners") or []),
            "fields": [
                (f.get("name") or "").strip()
                for f in schema_fields if (f.get("name") or "").strip()
            ],
            "schema_fields": schema_fields,
            "glossary_terms": list(payload.get("glossary_terms") or []),
            "upstreams": list(payload.get("upstreams") or []),
            "downstreams": list(payload.get("downstreams") or []),
        }
        self.record_evidence(
            uid, cid, kind="image", entity_name=image_entity,
            entity_urn=image_urn, entity_type="dataset",
            structured=structured, tool_name="visual",
            question=question, source="vision",
        )


    async def record_overview_evidence(
        self, uid: str, cid: str, question: str, answer_text: str,
        entity_hint: str | None = None,
    ) -> None:
        """Record a Thinking-Mode answer as reusable evidence."""
        name = entity_hint
        if not name:
            idents = _extract_identifiers(question)
            name = idents[0] if idents else None
        if not name or not answer_text:
            return
        self.record_evidence(
            uid, cid, kind="reasoning", entity_name=name,
            entity_urn=None, entity_type=None,
            structured={"summary": answer_text[:2000], "question": question},
            tool_name="thinking", question=question, source="thinking",
        )


    async def answer_from_evidence(
        self, uid: str, cid: str, question: str, res: ContextResolution,
        trace_id: str | None = None,
    ) -> "ChatResponse | None":
        """Answer a follow-up strictly from the recorded evidence (E1, E2, ...).

        Returns ``None`` when the evidence cannot ground the answer — the caller
        then falls through to the normal pipeline. Every answer returned here is
        grounded ONLY in ``res.referenced_evidence.structured``; no resolver /
        hybrid search / entity-repository re-fetch happens for a
        context-referencing follow-up.
        """
        ev = res.referenced_evidence
        if ev is None:
            return None
        structured = ev.structured or {}
        entity = res.entity_name or ev.entity_name or ""
        hint = res.intent_hint
        fields = [f for f in (structured.get("fields") or []) if f]
        norm_fields = {_normalize_field(f) for f in fields}

        log.info("evidence_answer", trace_id=trace_id, question=question[:120],
                 evidence=res.referenced_evidence_ids, hint=hint,
                 entity=entity[:80], context_only=res.context_only)

        # A field-property / field-focus follow-up that resolves to evidence but
        # carries no explicit field ("Còn kiểu dữ liệu của nó?", "field đó là
        # gì?") still names a field: the column this dataset shares with a
        # directly-linked table (the natural join key) is the field being
        # discussed. Falling back to it keeps the focus durable instead of
        # over-answering with the whole schema or dropping to "no info".
        if res.focus_field is None and (
            res.property_name or res.operation
            or re.search(
                r"field\s+(?:đó|do|này|nay|đó|kia)\s+là\s+gì|trường\s+(?:đó|do|này|nay|kia)"
                r"\s+là\s+gì|truong\s+(?:do|nay|kia)\s+la\s+gi|field\s+(?:do|nay|kia)"
                r"\s+la\s+gi",
                question, re.I,
            )
        ):
            inferred = (
                structured.get("focus_field")
                or structured.get("join_field")
                or await self._infer_join_field(structured)
            )
            if inferred:
                res.focus_field = inferred
                log.info("evidence_focus_inferred", trace_id=trace_id,
                         question=question[:120], focus=inferred,
                         evidence=res.referenced_evidence_ids)

        # ---------------- field-level operation ---------------- #
        # "warehouse_id có kiểu dữ liệu gì?", "field đó có mô tả gì?",
        # "field nào liên quan đến warehouse?" -> answer exactly that field /
        # property from the referenced schema, never the whole schema again.
        field_answer = await self.evidence_field_answer(
            uid, cid, question, res, entity, structured, trace_id,
        )
        if field_answer is not None:
            return field_answer

        # ---------------- focused field identification ---------------- #
        # A follow-up that names a real field of the referenced schema but is
        # NOT a property / join / location question ("movement_date là field
        # nào?", "field đó là gì?") asks WHAT that field is. Answer with the
        # field's description + type only — never the whole schema listing
        # again (over-answer, A08/A10). Join/location wording is left to its
        # dedicated branch below.
        if hint != "join" and not (
            res.target_field and re.search(
                r"liên\s+kết|lien\s+ket|join|khóa\s+liên|khoa\s+lien",
                question, re.I,
            )
        ):
            focused = await self.evidence_focus_field_answer(
                uid, cid, question, res, entity, structured, trace_id,
            )
            if focused is not None:
                return focused

        # ---------------- join-key matching on the referenced schema ------- #
        if hint == "join" or (hint == "schema" and res.target_field):
            response = await self.evidence_join_answer(
                uid, cid, question, res, entity, fields, norm_fields, trace_id,
            )
            if response is not None:
                return response

        # ---------------- field / dataset glossary ---------------- #
        if hint == "glossary":
            response = await self.evidence_glossary_answer(
                uid, cid, question, res, entity, structured, trace_id,
            )
            if response is not None:
                return response

        # ---------------- owner ---------------- #
        if hint == "owner":
            names = [
                (o.get("name") or "").strip()
                for o in structured.get("owners") or [] if (o.get("name") or "")
            ]
            if names:
                text = f"Dataset **{entity}** có owner: {', '.join(names)}."
            else:
                text = (
                    f"Dataset **{entity}** hiện không có người sở hữu (owner) "
                    f"trong metadata đã lấy."
                )
            return await self.evidence_finish(
                uid, cid, question, text, "OWNER_LOOKUP", entity_name=entity,
                trace_id=trace_id,
            )

        # ---------------- domain ---------------- #
        if hint == "domain":
            domain = structured.get("domain")
            if domain:
                text = f"Dataset **{entity}** thuộc lĩnh vực/domain **{domain}**."
            else:
                text = (
                    f"Dataset **{entity}** chưa có domain được ghi nhận trong "
                    f"metadata vừa lấy."
                )
            return await self.evidence_finish(
                uid, cid, question, text, "ENTITY_DOMAIN", entity_name=entity,
                trace_id=trace_id,
            )

        # ---------------- quality report on collected evidence ---------------- #
        # "Chất lượng của dataset trong ảnh thế nào?" / "chất lượng của nó?"
        # after a Data Quality Check -> answer deterministically from the stored
        # quality report (sections + overall score), never re-run the check.
        if hint == "quality":
            answer_text = self.evidence_quality_answer(entity, structured)
            if answer_text is not None:
                return await self.evidence_finish(
                    uid, cid, question, answer_text, "QUALITY_REPORT",
                    entity_name=entity, trace_id=trace_id,
                )

        # ---------------- lineage filter / scope ---------------- #
        if hint == "lineage":
            if not (res.scope_all or res.context_only or has_context_reference(question)):
                # A bare "lineage của nó" is already handled by the proven
                # coreference pipeline; only explicit evidence references are
                # answered strictly from the store here.
                return None
            response = await self.evidence_lineage_answer(
                uid, cid, question, res, entity, hint, trace_id,
            )
            if response is not None:
                return response

        # ---------------- schema listing (incl. capability ellipsis) ------- #
        if hint == "schema" and fields:
            text = (
                f"Dataset **{entity}** có các trường: {format_fields(fields)}."
            )
            return await self.evidence_finish(
                uid, cid, question, text, "SCHEMA_LOOKUP", entity_name=entity,
                trace_id=trace_id,
            )

        # ---------------- field location (context-only) ---------------- #
        # "Không tìm kiếm thêm. warehouse_id nằm ở bảng nào?" — a context-only
        # follow-up naming a field but no property asks WHERE that field lives.
        # Answer from the referenced evidence (the table that owns it) without
        # re-searching the whole catalog.
        if res.context_only and res.focus_field and not (
            res.operation or res.property_name
        ):
            text = (
                f"Field **{res.focus_field}** nằm trong bảng **{entity}** — "
                f"dựa trên metadata vừa lấy ({ev.evidence_id})."
            )
            return await self.evidence_finish(
                uid, cid, question, text, "CONTEXT_FIELD_LOCATION",
                entity_name=entity, trace_id=trace_id,
            )

        # ---------------- context-only fallthrough ---------------- #
        if res.context_only:
            text = (
                f"Dựa trên metadata vừa lấy của **{entity}**, hiện không có "
                f"thông tin thêm nào để trả lời câu hỏi này. Bạn có thể hỏi về "
                f"schema, owner, domain hoặc lineage của **{entity}**."
            )
            return await self.evidence_finish(
                uid, cid, question, text, "CONTEXT_EVIDENCE", entity_name=entity,
                trace_id=trace_id,
            )

        return None


    async def _infer_join_field(self, structured: dict) -> str | None:
        """The column this dataset shares with a directly-linked dataset.

        A dataset's natural join key is the field duplicated in the schema of an
        upstream/downstream table (e.g. ``warehouse_id`` appears both in
        ``dim_warehouse`` and ``fact_inventory_movement``). Used as the durable
        discussion-field fallback for anaphoric field follow-ups.
        """
        own_entries = [
            f for f in (structured.get("schema_fields") or [])
            if (f.get("name") or "").strip()
        ]
        if not own_entries:
            return None
        own = {_normalize_field(f.get("name")) for f in own_entries}
        linked = list(dict.fromkeys(
            list((structured.get("upstreams") or [])[:3])
            + list((structured.get("downstreams") or [])[:3])
        ))
        for urn in linked:
            if not urn:
                continue
            try:
                other = await self._ctx.entity_repo.get_by_urn(urn)
            except Exception:  # noqa: BLE001
                other = None
            if other is None:
                continue
            other_sf = ((other.payload or {}).get("schema_fields") or [])
            if not other_sf:
                continue
            shared = own & {
                _normalize_field(f.get("name")) for f in other_sf
                if (f.get("name") or "").strip()
            }
            if not shared:
                continue
            preferred = next(
                (f for f in shared if re.search(r"(?:_id|_code|_key)$", f)),
                None,
            )
            return preferred or sorted(shared)[0]
        return None


    async def evidence_focus_field_answer(
        self, uid: str, cid: str, question: str, res: ContextResolution,
        entity: str, structured: dict, trace_id: str | None = None,
    ) -> "ChatResponse | None":
        """Answer a follow-up that identifies a real field of the referenced
        schema ("movement_date là field nào?", "field đó là gì?") with a
        focused answer — the field's description + data type — instead of
        re-rendering the whole schema (over-answer).

        Only fires when ``focus_field`` names a field that actually exists in
        the referenced evidence and the question is a "which/what field" ask
        (no property / join / location wording). Returns ``None`` otherwise so
        the dedicated branches (property, join, location, glossary...) handle
        their own shapes.
        """
        focus = res.focus_field
        if not focus:
            return None
        # A property request is answered by evidence_field_answer; a location /
        # join request by its dedicated branch. Only description-flavoured asks
        # belong here.
        if res.operation or res.property_name:
            return None
        q = (question or "").lower()
        if re.search(
            r"\bnằm\s+ở\b|nam\s+o\b|thuộc\s+bảng|thuoc\s+bang|liên\s+kết|"
            r"lien\s+ket|join\s+key|\bjoin\b", q, re.I,
        ):
            return None
        if not re.search(
            r"là\s+gì|la\s+gi|là\s+field|là\s+trường|la\s+truong|field\s+nào|"
            r"field\s+nao|trường\s+nào|truong\s+nao|cột\s+nào|cot\s+nao|"
            r"\bwhat\b|\bis\s+it\b|mô\s+tả|mo\s+ta|ý\s+nghĩa|y\s+nghia", q, re.I,
        ):
            return None

        schema_fields = structured.get("schema_fields") or []
        target_norm = _normalize_field(focus)
        entry = next(
            (f for f in schema_fields
             if _normalize_field(f.get("name") or "") == target_norm),
            None,
        )
        if entry is None:
            return None
        desc = (entry.get("description") or "").strip().strip('"')
        ftype = (entry.get("type") or entry.get("data_type") or "").strip()
        if not desc and not ftype:
            return None

        parts: list[str] = []
        parts.append(f"Field **{entry.get('name')}** là một trường của **{entity}**")
        if ftype:
            parts.append(f"có kiểu dữ liệu **{ftype}**")
        if desc:
            parts.append(f"ý nghĩa: “{desc}”")
        text = f"{parts[0]} ({', '.join(parts[1:])})." if len(parts) > 1 \
            else f"{parts[0]}."
        if res.context_only:
            text += " (dựa trên metadata vừa lấy)"
        log.info("route_field_focus", trace_id=trace_id, question=question[:120],
                 evidence=res.referenced_evidence_ids, entity=entity[:80],
                 field=entry.get("name"))
        # Re-record the evidence with the field focus so a bare "Còn kiểu dữ
        # liệu của nó?" / "nó là gì?" follow-up keeps resolving to this field.
        ev = res.referenced_evidence
        self.record_evidence(
            uid, cid, kind=ev.kind, entity_name=ev.entity_name,
            entity_urn=ev.entity_urn, entity_type=ev.entity_type,
            structured={
                **structured,
                "focus_field": entry.get("name") or focus,
                "fields": [
                    (f.get("name") or "").strip()
                    for f in schema_fields if (f.get("name") or "").strip()
                ],
            },
            tool_name=ev.tool_name, question=question, source=ev.source,
        )
        return await self.evidence_finish(
            uid, cid, question, text, "CONTEXT_FIELD_DESCRIPTION",
            entity_name=entity, trace_id=trace_id,
        )


    async def evidence_field_answer(
        self, uid: str, cid: str, question: str, res: ContextResolution,
        entity: str, structured: dict, trace_id: str | None = None,
    ) -> "ChatResponse | None":
        """Answer a field-level follow-up from the referenced schema metadata.

        Supports ``get_property`` ("warehouse_id có kiểu dữ liệu gì?", "field
        đó có mô tả gì?") and ``find_field`` ("field nào liên quan đến
        warehouse?") against the referenced evidence's ``schema_fields``. Field
        glossary is delegated to :meth:`evidence_glossary_answer` (it must
        disambiguate field-vs-term). Returns ``None`` to fall through when the
        evidence cannot ground the answer.
        """
        schema_fields = structured.get("schema_fields") or []
        prop = res.property_name
        focus = res.focus_field or structured.get("focus_field")
        field_op: FieldOp | None = None
        if prop == "glossary":
            # Field glossary must be decided field-vs-term from the evidence
            # context (handled by evidence_glossary_answer), not answered here.
            return None
        if res.operation == "get_property" and prop:
            field_op = FieldOp(op="get_property", property=prop, field=focus)
        elif res.operation == "find_field":
            field_op = FieldOp(op="find_field", keyword=res.search_keyword)
        elif focus and prop and prop != "glossary":
            # Anaphoric "field đó / trường này có mô tả gì?" — the property is
            # named but no field token; apply it to the focus field.
            field_op = FieldOp(op="get_property", property=prop, field=focus)
        if field_op is None:
            return None

        text = answer_field_op(
            schema_fields, entity, field_op,
            citation=res.referenced_evidence.evidence_id,
        )
        if text is None:
            return None
        intent_label = "CONTEXT_FIELD_FIND" if field_op.op == "find_field" else {
            "data_type": "CONTEXT_FIELD_TYPE",
            "native_data_type": "CONTEXT_FIELD_TYPE",
            "description": "CONTEXT_FIELD_DESCRIPTION",
        }.get(field_op.property or "", "CONTEXT_FIELD_PROPERTY")

        # Re-record the evidence with the field focus so a bare "field đó / nó"
        # follow-up keeps resolving to this field.
        ev = res.referenced_evidence
        self.record_evidence(
            uid, cid, kind=ev.kind, entity_name=ev.entity_name,
            entity_urn=ev.entity_urn, entity_type=ev.entity_type,
            structured={
                **structured,
                "focus_field": field_op.field or field_op.keyword,
                "fields": [
                    (f.get("name") or "").strip()
                    for f in schema_fields if (f.get("name") or "").strip()
                ],
            },
            tool_name=ev.tool_name, question=question, source=ev.source,
        )
        log.info("route_field_op", trace_id=trace_id, question=question[:120],
                 evidence=res.referenced_evidence_ids, entity=entity[:80],
                 op=field_op.op, property=field_op.property,
                 field=field_op.field, keyword=field_op.keyword)
        return await self.evidence_finish(
            uid, cid, question, text, intent_label, entity_name=entity,
            trace_id=trace_id,
        )


    async def evidence_join_answer(
        self, uid: str, cid: str, question: str, res: ContextResolution,
        entity: str, fields: list[str], norm_fields: set[str],
        trace_id: str | None = None,
    ) -> "ChatResponse | None":
        structured = res.referenced_evidence.structured or {}
        target_field = res.target_field or res.focus_field \
            or structured.get("join_field")
        join_field: str | None = None
        if target_field:
            candidate = next(
                (f for f in fields if _normalize_field(f) == _normalize_field(target_field)),
                None,
            )
            if candidate:
                join_field = candidate
            elif _normalize_field(target_field) in norm_fields:
                join_field = target_field
            elif structured.get("join_field"):
                join_field = structured.get("join_field")
            else:
                join_field = None
        else:
            join_field = structured.get("join_field")

        target_entity = _find_target_entity(res, entity) or res.target_entity
        if join_field:
            text = (
                f"### Field liên kết của **{entity}**\n"
                f"Theo schema vừa lấy, **{join_field}** là trường có khả năng "
                f"liên kết với **{res.target_entity}** (trường "
                f"**{res.target_field}** cùng tên). Trả lời dựa trên metadata "
                f"đã lấy, không cần tìm kiếm thêm toàn hệ thống."
            )
        elif target_entity:
            edge_entity = None
            for key in ("upstreams", "downstreams"):
                for ref in structured.get(key) or []:
                    ref_name = _name_from_urn(ref)
                    if _normalize_field(target_entity) in _normalize_field(ref_name):
                        edge_entity = ref_name
                        break
                if edge_entity:
                    break
            if edge_entity:
                text = (
                    f"Trong metadata vừa lấy, **{entity}** có liên kết với "
                    f"**{edge_entity}** (linked to **{target_entity}**)."
                )
            else:
                text = (
                    f"Trong metadata vừa lấy, **{entity}** không ghi nhận liên "
                    f"kết trực tiếp nào với **{target_entity}**."
                )
        else:
            text = (
                f"Theo schema vừa lấy, **{entity}** chưa có trường khóa (join key) "
                f"nào khớp với trường bạn nêu trong metadata này."
            )

        # The matched join key becomes the new field focus for further follow-ups.
        self.record_evidence(
            uid, cid, kind="schema", entity_name=entity,
            entity_urn=res.entity_urn, entity_type=res.entity_type,
            structured={
                **structured,
                "focus_field": join_field or target_field,
                "fields": fields,
            },
            tool_name="schema_join", question=question,
        )
        return await self.evidence_finish(
            uid, cid, question, text, "CONTEXT_JOIN", entity_name=entity,
            trace_id=trace_id,
        )


    async def evidence_glossary_answer(
        self, uid: str, cid: str, question: str, res: ContextResolution,
        entity: str, structured: dict, trace_id: str | None = None,
    ) -> "ChatResponse | None":
        field = res.focus_field
        if not field:
            return None
        schema_fields = structured.get("schema_fields") or []
        entry = next(
            (f for f in schema_fields
             if _normalize_field(f.get("name")) == _normalize_field(field)),
            None,
        )
        field_terms = [
            t for t in (entry or {}).get("glossary_terms") or [] if t
        ] if entry else []
        dataset_terms = [
            t for t in structured.get("glossary_terms") or [] if t
        ]
        field_norm = _normalize_field(field)
        term_match = next(
            (t for t in dataset_terms
             if field_norm in _normalize_field(t)),
            None,
        )
        if entry is None and term_match is None:
            # The named token is neither a field nor a known term in this
            # evidence — let the normal (term) pipeline resolve it.
            return None
        if entry is None and term_match:
            text = (
                f"“{field}” là một **glossary term** (không phải field của "
                f"**{entity}**) — trong metadata vừa lấy, dataset **{entity}** "
                f"có gắn glossary term **{term_match}**."
            )
            return await self.evidence_finish(
                uid, cid, question, text, "CONTEXT_FIELD_GLOSSARY",
                entity_name=entity, trace_id=trace_id,
            )
        # Field-level terms recorded as raw strings take priority.
        if field_terms:
            term_names = ", ".join(field_terms[:8])
            text = (
                f"Trong metadata vừa lấy, field **{field}** của dataset "
                f"**{entity}** được gắn glossary term: **{term_names}**."
            )
        elif dataset_terms:
            text = (
                f"Field **{field}** không có glossary term riêng trong metadata "
                f"vừa lấy. Dataset **{entity}** có các glossary term chung: "
                f"{', '.join(dataset_terms[:8])}."
            )
        else:
            text = (
                f"Trong metadata vừa lấy, field **{field}** không được gắn "
                f"glossary term nào."
            )
        return await self.evidence_finish(
            uid, cid, question, text, "CONTEXT_FIELD_GLOSSARY",
            entity_name=entity, trace_id=trace_id,
        )


    async def evidence_lineage_answer(
        self, uid: str, cid: str, question: str, res: ContextResolution,
        entity: str, hint: str, trace_id: str | None = None,
    ) -> "ChatResponse | None":
        structured = res.referenced_evidence.structured or {}
        keyword = _extract_lineage_keyword(question)
        sections: dict[str, list[str]] = {
            "upstream": [
                u for u in structured.get("upstreams") or []
                if isinstance(u, str)
            ],
            "downstream": [
                d for d in structured.get("downstreams") or []
                if isinstance(d, str)
            ],
        }

        def _norm_refs(raw: list[str]) -> list[str]:
            out: list[str] = []
            for r in raw:
                name = _name_from_urn(r)
                if name and name not in out:
                    out.append(name)
            return out

        upstream_names = _norm_refs(sections["upstream"])
        downstream_names = _norm_refs(sections["downstream"])

        # VN/EN alias map so "downstream liên quan đến tồn kho" matches tables
        # named in English ("...fact_inventory_movement") and vice versa.
        keyword_aliases: list[str] = []
        if keyword:
            kw_ascii = (
                _norm_vn(keyword).encode("ascii", "ignore").decode("ascii")
                or _norm_vn(keyword)
            )
            vn_en_map = {
                "ton kho": "inventory", "tồn kho": "inventory",
                "tonkho": "inventory", "kho": "warehouse",
                "hang ton": "inventory", "warehouse": "warehouse",
                "doanh thu": "revenue", "ban hang": "sales",
                "ban": "sales", "mua hang": "purchase",
            }
            keyword_aliases = [kw_ascii, _norm_vn(keyword)]
            for k, v in vn_en_map.items():
                if k in kw_ascii or k in _norm_vn(keyword):
                    keyword_aliases.append(v)
            keyword_aliases = list(dict.fromkeys(keyword_aliases))

        def _matches(rname: str) -> bool:
            rn = _norm_vn(rname).encode("ascii", "ignore").decode("ascii").lower()
            rn = rn.replace(" ", "_")
            return any(a and a in rn for a in keyword_aliases)

        if keyword:
            upstream_names = [u for u in upstream_names if _matches(u)]
            downstream_names = [d for d in downstream_names if _matches(d)]

        lines: list[str] = [f"### Lineage của **{entity}** (từ metadata vừa lấy)"]
        if upstream_names:
            lines.append("Upstream: " + ", ".join(upstream_names[:20]))
        else:
            lines.append("Upstream: không có")
        if downstream_names:
            lines.append("Downstream: " + ", ".join(downstream_names[:20]))
        else:
            lines.append("Downstream: không có")
        if keyword:
            lines.append(
                f"> Đã lọc theo “{keyword}” từ kết quả lineage đã lấy ở trên."
            )
        lines.append(f"> Chỉ dựa trên metadata vừa lấy (E{res.referenced_evidence.evidence_id}).")
        text = "\n".join(lines)
        return await self.evidence_finish(
            uid, cid, question, text, "CONTEXT_LINEAGE", entity_name=entity,
            trace_id=trace_id,
        )


    def evidence_quality_answer(
        self, entity: str, structured: dict,
    ) -> str | None:
        """Deterministic quality answer from a previously recorded quality report.

        Returns ``None`` when the referenced evidence does not hold a real quality
        report (fall through to the normal pipeline).
        """
        if not isinstance(structured, dict):
            return None
        if "overall_score" not in structured and not structured.get("sections"):
            return None
        overall = structured.get("overall_score")
        rating = structured.get("rating")
        sections = structured.get("sections") or []
        lines = [f"### Chất lượng dữ liệu của **{entity}**"]
        if overall is not None:
            score_text = (
                f"{overall:.1f}/100" if isinstance(overall, (int, float))
                else str(overall)
            )
            rating_text = f" (mức **{rating}**)" if rating else ""
            lines.append(f"- Điểm tổng thể: **{score_text}**{rating_text}")
        if sections:
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                sec_name = (sec.get("name") or "").strip()
                score = sec.get("score")
                if not sec_name or score is None:
                    continue
                score_text = (
                    f"{score:.1f}/100" if isinstance(score, (int, float))
                    else str(score)
                )
                lines.append(f"- {sec_name}: **{score_text}**")
        else:
            lines.append("- Chưa có số liệu chi tiết trong metadata vừa lấy.")
        lines.append("Dựa trên metadata vừa lấy, không tìm kiếm thêm.")
        return "\n".join(lines)


    async def evidence_finish(
        self, uid: str, cid: str, question: str, text: str,
        intent_label: str, entity_name: str, trace_id: str | None = None,
    ) -> "ChatResponse":
        """Shared bookkeeping for an evidence-based answer."""
        await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, text)
        await self.record_active_entities(uid, cid, [], extra=[{
            "name": entity_name,
        }], question=question)
        # Attach the canonical entity (URN + URL) so follow-up answers that are
        # grounded purely in evidence still carry the entity for grounding /
        # evaluation, not just free text.
        entity = await self._resolve_evidence_entity(entity_name, trace_id)
        return ChatResponse(
            answer=text, intent=intent_label, confidence="high",
            ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=cid,
            entities=[entity] if entity else [],
        )

    async def _resolve_evidence_entity(
        self, entity_name: str, trace_id: str | None = None,
    ) -> "EntityItem | None":
        if not entity_name:
            return None
        try:
            resolution = await self._ctx.entity_resolver.resolve(
                entity_name, trace_id=trace_id)
        except Exception:  # noqa: BLE001
            return None
        if not resolution.resolved:
            return None
        return EntityItem(
            urn=resolution.resolved.urn,
            name=getattr(resolution.resolved, "display_name", None)
            or resolution.resolved.name,
            url=getattr(resolution.resolved, "datahub_url", None),
            entity_type=getattr(resolution.resolved, "entity_type", None),
            platform=getattr(resolution.resolved, "platform", None),
            domain=getattr(resolution.resolved, "domain", None),
            description=getattr(resolution.resolved, "description", None),
            environment=getattr(resolution.resolved, "environment", None),
        )


    async def record_active_entities(
        self, uid: str, cid: str, results: list[SearchResult],
        extra: list[dict] | None = None,
        question: str | None = None,
    ) -> None:
        """Store the canonical entities this turn resolved for coreference state."""
        # An explicitly-named catalog entity ("lineage của fact_sales_order")
        # becomes the new anaphora subject: the image-derived focus is dropped.
        if question and _has_own_identifier(question):
            self._ctx.memory.clear_image_focus(uid, cid)
        entities: list[dict] = []
        seen: set[str] = set()
        for r in (results or [])[:4]:
            key = r.urn or r.name
            if not key or key in seen:
                continue
            seen.add(key)
            entities.append({
                "name": r.name, "entity_type": r.entity_type, "urn": r.urn,
            })
        for e in (extra or []):
            n = (e.get("name") or "").strip()
            if not n or n in seen:
                continue
            seen.add(n)
            entities.append(e)
        if entities:
            self._ctx.memory.record_active_entities(uid, cid, entities)
