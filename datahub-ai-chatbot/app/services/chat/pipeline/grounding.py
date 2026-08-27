"""Grounded fallback and taxonomy mapping helpers for Chat Service."""
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from retrieval.intent import QueryIntent

# Standard intent taxonomy the QU layer emits
STANDARD_TAXONOMY = {
    "FIELD_PROPERTY", "SCHEMA_LOOKUP", "FIND_FIELD", "LINEAGE", "OWNER",
    "GLOSSARY", "JOIN", "ENTITY_EXISTS", "TERM_TO_DATASETS", "GENERAL",
    "COUNT",
}

# Deterministic mapping from legacy evidence/field-property path labels to standard taxonomy
FALLBACK_INTENT_MAP = {
    "CONTEXT_FIELD_FIND": "FIELD_PROPERTY",
    "CONTEXT_FIELD_DESCRIPTION": "FIELD_PROPERTY",
    "CONTEXT_FIELD_TYPE": "FIELD_PROPERTY",
    "CONTEXT_FIELD_PROPERTY": "FIELD_PROPERTY",
    "CONTEXT_FIELD_LOCATION": "SCHEMA_LOOKUP",
    "CONTEXT_FIELD_GLOSSARY": "GLOSSARY",
    "CONTEXT_JOIN": "JOIN",
    "CONTEXT_LINEAGE": "LINEAGE",
    "CONTEXT_EVIDENCE": "GENERAL",
}

_FIELD_MEANING_MAP: dict[str, str] = {
    "bu_short_name": "tên viết tắt của đơn vị kinh doanh (Business Unit short name)",
    "sod_total_amount": "tổng giá trị đơn bán (Sales Order Detail total amount)",
    "is_manufacturing": "đánh dấu nhà máy sản xuất (Manufacturing plant flag)",
    "plant_id": "mã định danh của nhà máy (Plant identifier)",
    "plant_name": "tên của nhà máy (Plant name)",
    "material_code": "mã định danh của nguyên vật liệu/linh kiện (Material code)",
    "material_name": "tên của nguyên vật liệu/linh kiện (Material name)",
    "vendor_code": "mã định danh của nhà cung cấp (Vendor code)",
    "vendor_name": "tên của nhà cung cấp (Vendor name)",
    "order_date": "ngày đặt hàng (Order date)",
    "sales_order_number": "số đơn hàng bán (Sales order number)",
    "unit_price": "đơn giá (Unit price)",
    "quantity": "số lượng (Quantity)",
    "status": "trạng thái (Status)",
}

_FIELD_FRAGMENT_VN: tuple[tuple[str, str], ...] = (
    ("short", "viết tắt"),
    ("name", "tên"),
    ("id", "mã định danh"),
    ("code", "mã"),
    ("description", "mô tả"),
    ("amount", "giá trị"),
    ("total", "tổng"),
    ("qty", "số lượng"),
    ("quantity", "số lượng"),
    ("date", "ngày"),
    ("status", "trạng thái"),
    ("type", "loại"),
    ("flag", "cờ đánh dấu"),
    ("is_", "cờ đánh dấu"),
    ("plant", "nhà máy"),
    ("factory", "nhà máy"),
    ("manufacturing", "sản xuất"),
    ("businessunit", "đơn vị kinh doanh"),
    ("unit", "đơn vị"),
    ("order", "đơn hàng"),
    ("salesorder", "đơn bán"),
    ("price", "giá"),
    ("key", "khóa"),
)


def qu_primary_intent(understanding: Any) -> str | None:
    """Normalize the QU output's primary intent to the standard taxonomy."""
    if understanding is None:
        return None
    raw = (getattr(understanding, "intent", None) or "").strip().upper()
    if not raw:
        return None
    aliases = {
        "FIELD_LOOKUP": "FIND_FIELD",
        "SCHEMA": "SCHEMA_LOOKUP",
        "GLOSSARY_TERM": "GLOSSARY",
        "TERM_SEARCH": "GLOSSARY",
        "OWNERSHIP": "OWNER",
        "LINEAGE_UPSTREAM": "LINEAGE",
        "LINEAGE_DOWNSTREAM": "LINEAGE",
        "FIELD_TYPE": "FIELD_PROPERTY",
        "FIELD_DESCRIPTION": "FIELD_PROPERTY",
        "FIELD_LOCATION": "SCHEMA_LOOKUP",
    }
    canonical = aliases.get(raw, raw)
    if canonical in STANDARD_TAXONOMY:
        return canonical
    for known in STANDARD_TAXONOMY:
        if known in raw or raw in known:
            return known
    return None


def unify_intent_label(raw: str, understanding: Any) -> str:
    """Resolve the final response ``intent`` to the standard taxonomy."""
    qu_intent = qu_primary_intent(understanding)
    if qu_intent:
        return qu_intent
    return FALLBACK_INTENT_MAP.get(raw, raw)


def field_meaning(field_name: str) -> str:
    """Name-derived Vietnamese meaning for a column (grounded, no LLM)."""
    name = (field_name or "").strip().lower().replace(" ", "_")
    if not name:
        return ""
    if name in _FIELD_MEANING_MAP:
        return _FIELD_MEANING_MAP[name]
    parts = [p for p in re.split(r"[_\W]+", name) if p]
    vn: list[str] = []
    for p in parts:
        for frag, v in _FIELD_FRAGMENT_VN:
            if p == frag or p.startswith(frag):
                if v not in vn:
                    vn.append(v)
                break
    if vn:
        return " ".join(vn)
    return f"dữ liệu của trường {field_name} (theo tên trường)"


def build_grounded_fallback(intent: QueryIntent, results: Sequence[Any]) -> str:
    """Deterministic metadata-grounded fallback when the LLM provider fails."""
    valid = [r for r in results if (getattr(r, "name", "") or "").strip()]
    if not valid:
        return ""
    lines: list[str] = []
    for _i, _r in enumerate(valid[:8], 1):
        _pl = getattr(_r, "payload", {}) or {}
        _name = getattr(_r, "name", "") or ""
        _bit = f"{_i}. **{_name}**"
        _plat = (_pl.get("platform") or "").strip()
        _etype = (_pl.get("entity_type") or getattr(_r, "entity_type", "") or "").strip()
        _parts = []
        if _etype:
            _parts.append(_etype)
        if _plat:
            _parts.append(f"nền tảng {_plat}")
        if _parts:
            _bit += f" ({', '.join(_parts)})"
        _desc = (_pl.get("description") or "").strip()
        if _desc:
            _bit += f" — {_desc[:180]}"
        lines.append(_bit)
        lines.append("")
    if intent == QueryIntent.TERM_TO_DATASETS:
        return (
            "Các entity liên quan trong metadata DataHub:\n\n"
            + "\n".join(lines).strip()
        )
    return "Trong metadata DataHub hiện có các entity liên quan:\n\n" + "\n".join(lines).strip()
