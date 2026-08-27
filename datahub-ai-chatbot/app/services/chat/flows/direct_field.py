"""Direct field-operation answering from schema metadata."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import structlog

from app.schemas.chat import ChatResponse
from app.services.chat.field_ops import answer_field_op, find_field_entry
from app.services.chat.question_analysis import (
    _extract_field_identifier,
    _is_field_location_question,
    _trusted_resolution,
)
from retrieval.evidence import (
    FieldOp,
    detect_field_property,
    extract_field_entity,
    parse_field_operation,
)
from retrieval.intent import _norm_vn

if TYPE_CHECKING:
    from app.services.chat.context import ChatContext

log = structlog.get_logger()


def norm_field(f: str) -> str:
    return (f or "").strip().lower().replace(" ", "_")


async def answer_direct_field_op(
    ctx: ChatContext,
    query: str,
    uid: str,
    cid: str,
    trace_id: str | None = None,
    understanding: Any = None,
) -> ChatResponse | None:
    """Answer a self-contained field question directly from the resolved dataset's schema."""
    if _is_field_location_question(query):
        return None

    op = parse_field_operation(query)
    ellipsis_field: str | None = None
    if op is None or op.op == "find_field":
        if (
            understanding is not None
            and getattr(understanding, "is_field_property_question", False)
            and getattr(understanding, "focus_field", None)
            and getattr(understanding, "property", None)
        ):
            op = FieldOp(
                op="get_property",
                property=understanding.property,
                field=understanding.focus_field,
            )
        else:
            _em = re.search(r"\b(?:con|the con|vay|vao)\b", _norm_vn(query))
            if _em:
                _fm = re.search(
                    r"(?:trường|truong|field|cột|cot)\s+[\"“”'`]?"
                    r"([a-z0-9_]{2,}(?:\.[a-z0-9_]+)*)",
                    query,
                    re.I,
                )
                if _fm:
                    ellipsis_field = _fm.group(1)
            if ellipsis_field:
                op = FieldOp(
                    op="get_property",
                    property="data_type",
                    field=ellipsis_field,
                )
            else:
                _prop2 = detect_field_property(query)
                _bid = _extract_field_identifier(query)
                if _prop2 and _bid:
                    op = FieldOp(
                        op="get_property",
                        property=_prop2,
                        field=_bid,
                    )
                else:
                    return None

    field = op.field if (op is not None and op.field) else ellipsis_field
    if not field:
        return None
    entity_name, _ef = extract_field_entity(query)
    if (
        not entity_name
        and understanding is not None
        and getattr(understanding, "entity_refs", None)
    ):
        entity_name = understanding.entity_refs[0]

    entity_db = None
    if entity_name:
        resolution = await ctx.entity_resolver.resolve(
            entity_name, entity_type="dataset", trace_id=trace_id
        )
        if resolution is None or not _trusted_resolution(resolution):
            if (
                resolution is not None
                and resolution.ambiguous
                and resolution.candidates
                and len({(c.name or "").strip().lower() for c in resolution.candidates[:4]}) == 1
            ):
                resolution.resolved = resolution.candidates[0]
            else:
                return None
        if resolution and resolution.resolved:
            entity_db = await ctx.entity_repo.get_by_urn(resolution.resolved.urn)
    else:
        _evidence = ctx.memory.get_evidence(uid, cid) or []
        for _ev in reversed(_evidence):
            _evd = _ev.get("structured") or {}
            _ev_fields = [f for f in (_evd.get("fields") or []) if f]
            if any(norm_field(f) == norm_field(field) for f in _ev_fields):
                entity_db = await ctx.entity_repo.get_by_urn(_ev.get("entity_urn"))
                if entity_db is not None:
                    break

    if entity_db is None:
        retrieval = getattr(ctx, "retrieval", None)
        locate = await retrieval.resolve_field_lookup(field, trace_id) if retrieval else None
        if not locate:
            return None
        _types: dict[str, str] = {}
        _names: list[str] = []
        _seen: set[str] = set()
        for _r in locate:
            _rsf = (_r.payload or {}).get("schema_fields") or []
            _r_entry = find_field_entry(_rsf, field)
            _rtype = ((_r_entry or {}).get("type") or "").strip()
            _rname = (_r.name or "").strip()
            if _rname and _rname.lower() not in _seen:
                _seen.add(_rname.lower())
                _names.append(_rname)
            if _rtype and _rtype not in _types:
                _types[_rtype] = _rname
        if not _types:
            return None
        text = (
            f"Trường **{field}** có kiểu dữ liệu **{' / '.join(_types)}** "
            f"trong {len(_names)} dataset: {', '.join(_names[:8])}."
        )
        intent_label = {
            "data_type": "CONTEXT_FIELD_TYPE",
            "native_data_type": "CONTEXT_FIELD_TYPE",
            "description": "CONTEXT_FIELD_DESCRIPTION",
        }.get(op.property or "", "CONTEXT_FIELD_PROPERTY")
        await ctx.memory.add_turn_db(
            ctx.session, uid, cid, query, text
        )
        return ChatResponse(
            answer=text,
            intent=intent_label,
            confidence="high",
            ambiguous=False,
            insufficient_context=False,
            trace_id=trace_id or "",
            conversation_id=cid,
        )

    schema_fields = (entity_db.payload or {}).get("schema_fields") or []
    display = entity_db.display_name or entity_db.name
    text = answer_field_op(
        schema_fields,
        display,
        FieldOp(
            op="get_property",
            property=op.property or "data_type",
            field=field,
        ),
        citation=entity_db.urn,
    )
    if text is None:
        return None

    if hasattr(ctx, "evidence") and ctx.evidence is not None:
        ctx.evidence.record_evidence(
            uid,
            cid,
            kind="schema",
            entity_name=display,
            entity_urn=entity_db.urn,
            entity_type="dataset",
            structured={
                "schema_fields": schema_fields,
                "fields": [
                    (f.get("name") or "").strip()
                    for f in schema_fields
                    if (f.get("name") or "").strip()
                ],
                "focus_field": field,
            },
            tool_name="field_property",
            question=query,
            source="schema-metadata",
        )

    await ctx.memory.add_turn_db(
        ctx.session, uid, cid, query, text
    )
    intent_label = {
        "data_type": "CONTEXT_FIELD_TYPE",
        "native_data_type": "CONTEXT_FIELD_TYPE",
        "description": "CONTEXT_FIELD_DESCRIPTION",
    }.get(op.property or "", "CONTEXT_FIELD_PROPERTY")
    return ChatResponse(
        answer=text,
        intent=intent_label,
        confidence="high",
        ambiguous=False,
        insufficient_context=False,
        trace_id=trace_id or "",
        conversation_id=cid,
    )
