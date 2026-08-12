"""Field-level operation answering (schema -> field -> property).

Shared by the evidence layer (follow-ups grounded in E1, E2, ...) and the
direct field path ("warehouse_id của fact_inventory_movement có kiểu dữ liệu
gì?"): given the real ``schema_fields`` metadata, answer exactly the property
the user asked for instead of re-rendering the whole schema.

Nothing here is dataset/field specific and no expected answer is hard-coded —
it only reads whatever metadata the schema carries.
"""

from __future__ import annotations

from typing import Any

from retrieval.evidence import FieldOp

_PROP_KEY: dict[str, str] = {
    "data_type": "type",
    "native_data_type": "native_data_type",
    "description": "description",
    "glossary": "glossary_terms",
    "nullable": "nullable",
    "is_primary_key": "is_primary_key",
    "tags": "tags",
}

_PROP_LABEL: dict[str, str] = {
    "data_type": "kiểu dữ liệu",
    "native_data_type": "kiểu dữ liệu gốc (native)",
    "description": "mô tả",
    "glossary": "glossary term",
    "nullable": "nullable",
    "is_primary_key": "khóa chính",
    "tags": "tag",
}


def _field_norm(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def find_field_entry(schema_fields: list[dict[str, Any]], field: str) -> dict[str, Any] | None:
    f = _field_norm(field)
    if not f:
        return None
    return next(
        (e for e in (schema_fields or []) if _field_norm(e.get("name")) == f),
        None,
    )


def _bool_text(value: Any, yes: str, no: str) -> str:
    return yes if value else no


def answer_field_property(
    schema_fields: list[dict[str, Any]], entity_name: str,
    field: str, prop: str, citation: str | None = None,
) -> str | None:
    """Deterministic answer for ``get_property(field, prop)`` from real metadata.

    Returns ``None`` when the field does not exist in ``schema_fields`` (the
    caller then falls through to the generic pipeline).
    """
    entry = find_field_entry(schema_fields, field)
    if entry is None:
        return None
    name = entity_name or "dataset vừa lấy"
    label = _PROP_LABEL.get(prop, prop)
    cite = f" (dựa trên {citation})" if citation else ""
    value = entry.get(_PROP_KEY.get(prop, ""))

    if prop == "data_type":
        if not value:
            return None
        return (
            f"Field **{field}** của dataset **{name}** có {label}: **{value}**."
            + cite
        )
    if prop == "native_data_type":
        if not value:
            return None
        return (
            f"Field **{field}** của dataset **{name}** có {label}: **{value}**."
            + cite
        )
    if prop == "description":
        if not value:
            return (
                f"Field **{field}** của dataset **{name}** chưa có mô tả nào "
                f"trong metadata đã lấy." + cite
            )
        return f"Field **{field}** của dataset **{name}** có mô tả: “{value}”." + cite
    if prop == "glossary":
        terms = [t for t in (value or []) if t]
        if terms:
            return (
                f"Field **{field}** của dataset **{name}** được gắn glossary "
                f"term: **{', '.join(terms[:8])}**." + cite
            )
        return (
            f"Field **{field}** của dataset **{name}** chưa được gắn glossary "
            f"term nào trong metadata đã lấy." + cite
        )
    if prop == "nullable":
        return (
            f"Field **{field}** của dataset **{name}** "
            + _bool_text(value, "cho phép NULL (có thể để trống).",
                         "không cho phép NULL (bắt buộc).")
            + cite
        )
    if prop == "is_primary_key":
        return (
            f"Field **{field}** của dataset **{name}** "
            + _bool_text(value, "là khóa chính (primary key).",
                         "không phải khóa chính (primary key).")
            + cite
        )
    if prop == "tags":
        tags = [t for t in (value or []) if t]
        if tags:
            return (
                f"Field **{field}** của dataset **{name}** có tag: "
                f"**{', '.join(tags[:8])}**." + cite
            )
        return (
            f"Field **{field}** của dataset **{name}** chưa có tag nào trong "
            f"metadata đã lấy." + cite
        )
    return None


def answer_find_field(
    schema_fields: list[dict[str, Any]], entity_name: str,
    keyword: str, citation: str | None = None,
) -> str | None:
    """Deterministic answer for ``find_field(keyword)`` within a schema."""
    kw = _field_norm(keyword)
    if not kw:
        return None
    matches: list[str] = []
    for entry in schema_fields or []:
        name = entry.get("name") or ""
        desc = entry.get("description") or ""
        if kw in _field_norm(name) or kw in _field_norm(desc):
            matches.append(name)
    if not matches:
        return None
    name = entity_name or "dataset vừa lấy"
    cite = f" (dựa trên {citation})" if citation else ""
    return (
        f"Theo schema đã lấy của **{name}**, field liên quan đến “{keyword}”: "
        f"**{', '.join(matches)}**." + cite
    )


def answer_field_op(
    schema_fields: list[dict[str, Any]], entity_name: str, op: FieldOp,
    citation: str | None = None,
) -> str | None:
    """Dispatch a parsed :class:`FieldOp` against real schema metadata."""
    if op is None:
        return None
    if op.op == "get_property" and op.field:
        return answer_field_property(
            schema_fields, entity_name, op.field, op.property or "", citation,
        )
    if op.op == "find_field" and op.keyword:
        return answer_find_field(schema_fields, entity_name, op.keyword, citation)
    return None
