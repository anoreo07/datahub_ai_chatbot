"""Reference resolution over the conversation's evidence store.

Given a follow-up question and the evidence collected so far (E1, E2, ...),
decide *what* the question refers to and *how* to answer it using only that
evidence:

* which evidence record(s) are referenced ("schema vừa lấy", "kết quả vừa
  rồi", "field đó", anaphora to the last active entity / image-derived
  dataset);
* whether the user constrains the answer to metadata already fetched
  ("chỉ dựa trên metadata vừa lấy") — ``context_only``;
* what the user wants done with it (schema listing, join-key matching, field
  glossary check, owner, domain, lineage filter, SQL, quality...);
* which concrete field / target table is named ("dim_warehouse.warehouse_id").

This module is deliberately data-only and synchronous: the resolved plan is
executed by ``ChatService``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from retrieval.evidence import (
    EvidenceRecord,
    FieldOp,
    detect_evidence_intent,
    detect_field_property,
    extract_field_refs,
    extract_target_ref,
    has_anaphora,
    has_context_only_constraint,
    has_context_reference,
    looks_like_a_field,
    parse_field_operation,
)

_DEMONSTRATIVE_SUBJ = re.compile(
    r"([a-zà-ỹ0-9_][a-zà-ỹ0-9_ \-,]*?)\s+(?:đó|do|này|nay|đây|day)\b", re.I,
)
_FOCUS_STOPWORDS = {
    "field", "fields", "trường", "truong", "cột", "cot", "column", "columns",
    "schema", "dataset", "datasets", "bảng", "bang", "metadata", "term",
    "glossary", "cái", "mấy", "the",
}


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "_")


def _named_focus(question: str) -> str | None:
    """The noun phrase directly before a demonstrative ("cold chain đó")."""
    m = _DEMONSTRATIVE_SUBJ.search(question or "")
    if not m:
        return None
    token = m.group(1).strip()
    low = token.lower()
    if not token or low in _FOCUS_STOPWORDS:
        return None
    return token

@dataclass
class ContextResolution:
    is_followup: bool = False
    context_only: bool = False
    scope_all: bool = False
    referenced_evidence: EvidenceRecord | None = None
    referenced_evidence_ids: list[str] = field(default_factory=list)
    entity_name: str | None = None
    entity_urn: str | None = None
    entity_type: str | None = None
    intent_hint: str | None = None
    field_refs: list[str] = field(default_factory=list)
    focus_field: str | None = None
    target_entity: str | None = None
    target_field: str | None = None
    extra_fields: list[str] = field(default_factory=list)
    operation: str | None = None        # "get_property" | "find_field" | None
    property_name: str | None = None    # data_type / description / ...
    search_keyword: str | None = None   # find_field keyword

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_followup": self.is_followup,
            "context_only": self.context_only,
            "scope_all": self.scope_all,
            "referenced_evidence_ids": self.referenced_evidence_ids,
            "referenced_evidence": (
                self.referenced_evidence.to_dict()
                if self.referenced_evidence else None
            ),
            "entity_name": self.entity_name,
            "entity_urn": self.entity_urn,
            "entity_type": self.entity_type,
            "intent_hint": self.intent_hint,
            "field_refs": self.field_refs,
            "focus_field": self.focus_field,
            "target_entity": self.target_entity,
            "target_field": self.target_field,
            "operation": self.operation,
            "property_name": self.property_name,
            "search_keyword": self.search_keyword,
        }


def _scope_all(question: str) -> bool:
    q = (question or "").lower()
    return any(
        k in q for k in (
            "toàn bộ kết quả", "toan bo ket qua",
            "kết quả vừa rồi", "ket qua vua roi",
            "kết quả vừa lấy", "ket qua vua lay",
            "toàn bộ metadata", "toan bo metadata",
            "all results", "tất cả kết quả", "tat ca ket qua",
        )
    )


def _last_schema(records: list[EvidenceRecord]) -> EvidenceRecord | None:
    for r in reversed(records):
        if r.kind in ("schema", "image") and (r.structured or {}).get("fields"):
            return r
    return None


def _last_kind(records: list[EvidenceRecord], kind: str) -> EvidenceRecord | None:
    for r in reversed(records):
        if r.kind == kind:
            return r
    return None


def _match_active_evidence(
    records: list[EvidenceRecord],
    active_entities: list[dict[str, Any]],
) -> EvidenceRecord | None:
    """Pick the evidence record matching the last active entity (anaphora)."""
    names = [
        (e.get("name") or "").lower()
        for e in active_entities or []
        if e.get("name")
    ]
    if not names:
        return None
    for r in reversed(records):
        n = (r.entity_name or "").lower()
        if n in names:
            return r
    return None


def _schema_fields(rec: EvidenceRecord) -> list[dict[str, Any]]:
    return list((rec.structured or {}).get("schema_fields") or [])


def _field_norm(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def _evidence_for_field(
    records: list[EvidenceRecord], field: str,
) -> EvidenceRecord | None:
    """Most recent evidence whose schema actually contains ``field``."""
    f = _field_norm(field)
    if not f:
        return None
    for r in reversed(records):
        for entry in _schema_fields(r):
            if _field_norm(entry.get("name")) == f:
                return r
    return None


def _evidence_for_keyword(
    records: list[EvidenceRecord], keyword: str,
) -> EvidenceRecord | None:
    """Most recent evidence whose schema mentions ``keyword`` in field name/desc."""
    kw = (keyword or "").strip().lower().replace(" ", "_")
    if not kw:
        return None
    for r in reversed(records):
        for entry in _schema_fields(r):
            blob = (
                _field_norm(entry.get("name")) + " "
                + _field_norm(entry.get("description"))
            )
            if kw in blob:
                return r
    return None


def resolve_context(
    question: str,
    evidence: list[dict[str, Any]],
    active_entities: list[dict[str, Any]] | None = None,
) -> ContextResolution:
    """Resolve what ``question`` refers to in the conversation's evidence.

    ``evidence`` is the list of recorded EvidenceRecord dicts (E1, E2, ...).
    ``active_entities`` is the coreference list the pipeline already tracks.
    """
    res = ContextResolution()
    q = question or ""
    records = [EvidenceRecord.from_dict(e) for e in (evidence or [])]
    if not q or not records:
        return res

    res.context_only = has_context_only_constraint(q)
    ref = has_context_reference(q)
    anaphora = has_anaphora(q) and not extract_field_refs(q)

    # A bare field-level question ("warehouse_id có kiểu dữ liệu gì?",
    # "field nào liên quan đến warehouse?") carries no explicit evidence
    # reference and no pronoun, but when the conversation already collected a
    # schema containing that field it must be resolved against THAT evidence —
    # never a fresh silent semantic re-search.
    known_fields = frozenset(
        _field_norm(f)
        for r in records
        for f in ((r.structured or {}).get("fields") or [])
        if f
    )
    field_op: FieldOp | None = parse_field_operation(q, known_fields)
    field_followup = False
    if field_op is not None and not ref and not anaphora:
        if field_op.op == "get_property" and field_op.field:
            field_followup = _evidence_for_field(records, field_op.field) is not None
        elif field_op.op == "find_field" and field_op.keyword:
            field_followup = _evidence_for_keyword(records, field_op.keyword) is not None

    if not ref and not anaphora and not field_followup and not res.context_only:
        return res

    table, field = extract_target_ref(q)
    res.target_entity = table
    res.target_field = field
    res.field_refs = extract_field_refs(q)
    res.intent_hint = detect_evidence_intent(q)
    res.scope_all = _scope_all(q)
    if field_op is not None:
        res.operation = field_op.op
        res.property_name = field_op.property
        res.search_keyword = field_op.keyword
    elif detect_field_property(q):
        # A property is named but no field token is present ("field đó có mô tả
        # gì?"): keep the property so the evidence layer can apply it to the
        # focus field resolved below.
        res.property_name = detect_field_property(q)

    # Pick the referenced evidence record.
    referenced: EvidenceRecord | None = None
    if ref or (field_followup and not anaphora):
        if _scope_all(q):
            referenced = records[-1]
            res.referenced_evidence_ids = [r.evidence_id for r in records]
        elif "schema" in q.lower() or "field" in q.lower() or "trường" in q.lower() \
                or "truong" in q.lower():
            referenced = _last_schema(records) or records[-1]
        elif field_followup and field_op is not None:
            # Resolve to the evidence that actually contains the named field.
            referenced = (
                _evidence_for_field(records, field_op.field)
                if field_op.op == "get_property" and field_op.field
                else _evidence_for_keyword(records, field_op.keyword)
                if field_op.op == "find_field" and field_op.keyword
                else _last_schema(records) or records[-1]
            )
        else:
            referenced = records[-1]
    else:
        # Anaphora: resolve through the active-entity match, else the last record.
        referenced = _match_active_evidence(records, active_entities or []) \
            or records[-1]

    if referenced is None:
        return res

    res.referenced_evidence = referenced
    if referenced.evidence_id not in res.referenced_evidence_ids:
        res.referenced_evidence_ids.append(referenced.evidence_id)
    res.entity_name = referenced.entity_name
    res.entity_urn = referenced.entity_urn
    res.entity_type = referenced.entity_type

    structured = referenced.structured or {}
    # The field being discussed: an explicit dotted field wins; otherwise the
    # most-recent field-like token named in the question; then the "focus field"
    # the turn itself identified (e.g. the join key matched); finally a noun
    # phrase before a demonstrative ("cold chain đó").
    focus: str | None = field
    if not focus and res.field_refs:
        ev_fields = {_norm(f) for f in structured.get("fields") or []}
        entity_norm = _norm(referenced.entity_name or "")
        for r in reversed(res.field_refs):
            rn = _norm(r)
            if rn == entity_norm:
                continue
            if rn in ev_fields or looks_like_a_field(r):
                focus = r
                break
        if not focus:
            focus = res.field_refs[-1]
    if not focus and field_op is not None and field_op.field:
        focus = field_op.field
    if not focus and structured.get("focus_field"):
        focus = structured.get("focus_field")
    if not focus and structured.get("join_field"):
        focus = structured.get("join_field")
    if not focus:
        focus = _named_focus(q)
    res.focus_field = focus
    # Fields listed in the referenced schema evidence.
    if structured.get("fields"):
        res.extra_fields = list(structured.get("fields") or [])

    res.is_followup = bool(res.referenced_evidence)
    return res
