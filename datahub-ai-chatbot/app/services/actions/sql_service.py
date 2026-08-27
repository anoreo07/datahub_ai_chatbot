"""SQL candidate discovery and grounded query generation service."""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field as _dc_field

import structlog

from app.auth.models import UserContext
from app.schemas.actions import SqlJoin, SqlResponse
from app.services.actions.base import BaseActionService
from app.services.actions.schema_service import extract_schema_columns, normalize_column_name
from database.models import Entity

log = structlog.get_logger()

# Column-like tokens (snake_case / dotted), e.g. "warehouse_id" or "fact.sales.order_id".
_FIELD_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", re.I)
# Flattened dotted identifiers (schema.table.column) also count as field candidates.
_FIELD_TOKEN_DOTTED_RE = re.compile(r"\b[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\b", re.I)

# Stop words / connector words never treated as a column filter
_FIELD_STOP = {
    "where", "from", "select", "having", "group", "order", "by", "limit",
    "sql", "query", "dataset", "datasets", "table", "bang", "ba?ng",
    "truy", "van", "truy van", "cau", "lenh", "do", "cho", "cua", "de",
    "trong", "theo", "voi", "la", "co", "va", "ve", "gi", "nao", "the",
    "all", "any", "is", "not", "null",
}


def extract_filter_values(question: str, columns: Sequence[str]) -> dict[str, str]:
    """Best-effort ``col = 'value'`` filters from a natural-language query.

    Returns a mapping of existing column name -> extracted value.
    """
    out: dict[str, str] = {}
    if not question or not columns:
        return out
    for col in columns:
        if not col:
            continue
        m = re.search(
            r"\b" + re.escape(col) + r"\b"
            + r"\s*(?:is|=|==|là|la|bang|bằng|equals)\s*"
            + r"['\"“”]?\s*([^\"\s,;.()…]+(?:\s+[^\"\s,;.()…]+)*)"
            + r"\s*['\"”]?",
            question,
            re.I,
        )
        if m:
            value = m.group(1).strip().strip("'\"“”")
            if value:
                out[col] = value
    return out


def extract_filter_fields(question: str) -> list[str]:
    """Best-effort column tokens from a natural-language query.

    Returns normalized (lowercase) column-like identifiers such as ``warehouse_id``.
    """
    tokens: list[str] = []
    for m in _FIELD_TOKEN_RE.finditer(question):
        tokens.append(normalize_column_name(m.group(0)))
    for m in _FIELD_TOKEN_DOTTED_RE.finditer(question):
        tokens.append(normalize_column_name(m.group(0).rsplit(".", 1)[-1]))
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t and t not in _FIELD_STOP and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _query_tokens(question: str) -> set[str]:
    """Meaningful, normalized content words from the question (excl. connectors)."""
    n = normalize_column_name(question)
    words = [w for w in re.split(r"[^a-z0-9_]+", n) if len(w) > 2]
    stop = {
        "truy", "van", "cau", "lenh", "cho", "dataset", "table", "bang",
        "the", "from", "where", "select", "sql", "query", "cua", "de",
        "trong", "theo", "voi", "khong", "mot", "la", "co", "va", "ve",
        "gi", "nao", "lam", "lam the", "sinh", "tao", "viet", "tra", "ve",
        "ghi", "them", "nhung", "cac", "duoc", "ban", "toi", "em", "anh",
        "chi", "hoi", "biet", "hay", "giup", "muon", "mong",
    }
    return {w for w in words if w not in stop}


def _entity_text(e: Entity) -> str:
    payload = e.payload or {}
    schema_bits: list[str] = []
    for f in extract_schema_columns(payload):
        if not isinstance(f, dict):
            continue
        schema_bits.append(str(f.get("name") or ""))
        schema_bits.append(str(f.get("description") or ""))
        schema_bits.append(str(f.get("comment") or ""))
    return normalize_column_name(" ".join([
        e.name or "",
        e.display_name or "",
        str(payload.get("description") or ""),
        str(payload.get("business_purpose") or ""),
        str(payload.get("domain") or ""),
        str(payload.get("platform") or ""),
        " ".join(str(g) for g in (payload.get("glossary_terms") or [])),
        " ".join(str(t) for t in (payload.get("tags") or [])),
        " ".join(schema_bits),
    ]))


@dataclass
class SqlCandidate:
    """A dataset that plausibly answers a SQL/filter request, ranked."""

    entity: Entity
    matched_fields: list[str]
    score: float
    reasons: list[str] = _dc_field(default_factory=list)


class SqlActionService(BaseActionService):
    """Handles field-aware SQL candidate discovery and grounded SQL generation."""

    async def discover_sql_candidates(
        self,
        question: str,
        user: UserContext | None = None,
        limit: int = 5,
    ) -> list[SqlCandidate]:
        """Field-aware dataset discovery for a SQL/filter request."""
        filter_fields = extract_filter_fields(question)
        query_tokens = _query_tokens(question)

        datasets = await self._repo.list_by_type("dataset", limit=2000)
        if self._auth_service is not None and user is not None:
            accessible = await self._auth_service.filter_accessible_urns(
                user, [e.urn for e in datasets]
            )
            datasets = [e for e in datasets if e.urn in accessible]

        candidates: list[SqlCandidate] = []
        for ds in datasets:
            payload = ds.payload or {}
            schema = extract_schema_columns(payload)
            norm_to_orig: dict[str, str] = {
                normalize_column_name(f.get("name") or ""): (f.get("name") or "").strip()
                for f in schema
                if f.get("name")
            }
            matched = [norm_to_orig[ff] for ff in filter_fields if ff in norm_to_orig]
            if not matched and not query_tokens:
                continue

            score = 0.0
            reasons: list[str] = []
            if matched:
                score += 2.0 * len(matched)
                reasons.append(f"chứa trường '{', '.join(matched)}' trong schema")
            text = _entity_text(ds)
            matched_tokens = [t for t in query_tokens if t in text]
            if matched_tokens:
                score += 0.6 * len(matched_tokens)
                reasons.append(
                    "mô tả/domain/glossary khớp từ '" + "', '".join(matched_tokens) + "'"
                )

            if score > 0:
                candidates.append(
                    SqlCandidate(
                        entity=ds,
                        matched_fields=matched,
                        score=round(score, 3),
                        reasons=reasons,
                    )
                )

        candidates.sort(key=lambda c: -c.score)
        log.info(
            "sql_discover_candidates",
            question=question[:100],
            filter_fields=filter_fields,
            query_tokens=sorted(query_tokens),
            candidate_count=len(candidates),
            top=[
                (c.entity.display_name or c.entity.name, c.score)
                for c in candidates[:3]
            ],
        )
        return candidates[:limit]

    async def generate_sql(
        self,
        dataset_query: str,
        requested_columns: Sequence[str] = (),
        user: UserContext | None = None,
        question: str = "",
    ) -> SqlResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return SqlResponse(
                dataset=dataset_query,
                explanation=["Không tìm thấy dataset phù hợp trong metadata DataHub."],
                valid=False,
            )

        payload = entity.payload or {}
        cols = extract_schema_columns(payload)
        actual: list[str] = []
        dateless: list[str] = []
        numeric: list[str] = []
        for f in cols:
            name = (f.get("name") or "").strip()
            if not name:
                continue
            actual.append(name)
            ftype = normalize_column_name(f.get("type") or f.get("native_data_type") or "")
            if ftype in {"date", "timestamp", "datetime"}:
                dateless.append(name)
            if any(k in ftype for k in ("int", "decimal", "numeric", "float", "double", "money")):
                numeric.append(name)

        if not actual:
            return SqlResponse(
                dataset=entity.display_name or entity.name,
                urn=entity.urn,
                explanation=["Dataset này chưa có schema được ghi nhận trong DataHub."],
                valid=False,
            )

        actual_norm = {normalize_column_name(c): c for c in actual}
        requested_norm = [normalize_column_name(c) for c in requested_columns if c]
        if requested_columns:
            unavailable = [
                orig for orig, n in zip(requested_columns, requested_norm)
                if n not in actual_norm
            ]
            if unavailable:
                return SqlResponse(
                    dataset=entity.display_name or entity.name,
                    urn=entity.urn,
                    selected_columns=[],
                    unavailable_columns=[str(c) for c in unavailable],
                    explanation=[
                        "Các cột sau không tồn tại trong schema đã truy vấn từ DataHub: "
                        + ", ".join(str(c) for c in unavailable)
                        + ". Không thể sinh SQL cho cột không có trong metadata."
                    ],
                    valid=False,
                )
            selected = [actual_norm[n] for n in requested_norm]
        else:
            selected = actual

        # Joins grounded on shared column names with upstream datasets.
        upstreams, _down = await self._lineage_urns(entity.urn)
        upstream_entities = await self._resolve_urns(upstreams)
        joins: list[SqlJoin] = []
        join_tables: list[tuple[Entity, str]] = []  # (upstream entity, shared column)
        main_norm = {normalize_column_name(c) for c in selected}
        for up_urn in upstreams:
            up = upstream_entities.get(up_urn)
            if up is None:
                continue
            up_cols = [
                normalize_column_name(f.get("name") or "")
                for f in extract_schema_columns(up.payload)
            ]
            shared = sorted(main_norm & set(up_cols))
            if not shared:
                continue
            shared_col = shared[0]
            join_tables.append((up, shared_col))
            joins.append(
                SqlJoin(
                    table=up.display_name or up.name,
                    column=shared_col,
                    reason=(up.payload or {}).get("description")
                    or f"Bảng nguồn upstream của {entity.display_name or entity.name}.",
                )
            )

        table = entity.name
        alias = "t"
        lines = [
            "SELECT",
            "  " + ",\n  ".join(f"{alias}.{c}" for c in selected),
            f"FROM {table} AS {alias}",
        ]
        for i, (up, shared_col) in enumerate(join_tables):
            up_alias = f"u{i + 1}"
            up_table = up.name or up.urn
            lines.append(
                f"JOIN {up_table} AS {up_alias} ON {alias}.{shared_col} = {up_alias}.{shared_col}"
            )
        filters = extract_filter_values(question, selected)
        if filters:
            for i, (col, value) in enumerate(filters.items()):
                escaped = value.replace("'", "''")
                clause = f"{alias}.{col} = '{escaped}'"
                if i == 0:
                    lines.append(f"WHERE {clause}")
                else:
                    lines.append(f"  AND {clause}")

        order_m = re.search(
            r"(?:sắp xếp|sap xep|order by)\s+(?:theo\s+)?([a-z0-9_]+)\s*"
            r"(giảm dần|giam dan|desc|tăng dần|tang dan|asc)?",
            question,
            re.I,
        )
        if order_m:
            order_col_raw = order_m.group(1)
            order_dir = (
                "DESC"
                if order_m.group(2)
                and any(d in order_m.group(2).lower() for d in ["giảm", "giam", "desc"])
                else "ASC"
            )
            order_col_match = next(
                (
                    c
                    for c in selected
                    if normalize_column_name(c) == normalize_column_name(order_col_raw)
                ),
                None,
            )
            if order_col_match:
                lines.append(f"ORDER BY {alias}.{order_col_match} {order_dir}")

        limit_m = re.search(
            r"(?:lấy|lay|top|limit)\s*(\d+)\s*(?:dòng|dong|bản ghi|ban ghi|rows|records)?",
            question,
            re.I,
        )
        if limit_m:
            limit_n = int(limit_m.group(1))
            lines.append(f"LIMIT {limit_n}")

        sql = "\n".join(lines)

        explanation: list[str] = []
        description = (payload.get("description") or "").strip()
        if description:
            explanation.append(f"Bảng {entity.display_name or entity.name}: {description}")
        else:
            explanation.append(
                f"Bảng {entity.display_name or entity.name}: không có mô tả trong DataHub."
            )
        for j in joins:
            explanation.append(f"JOIN {j.table} (cột chung '{j.column}'). {j.reason}")
        for col, value in filters.items():
            explanation.append(
                f"Lọc theo {col} = '{value}' (trích từ câu hỏi, chỉ dùng cột có trong schema)."
            )

        if numeric and dateless:
            numeric_set = {normalize_column_name(x) for x in numeric}
            dateless_set = {normalize_column_name(x) for x in dateless}
            agg_col = next(
                (c for c in selected if normalize_column_name(c) in numeric_set),
                "",
            )
            group_col = next(
                (c for c in selected if normalize_column_name(c) in dateless_set),
                "",
            )
            if agg_col and group_col:
                analytics = (
                    f"-- Analytics\nSELECT\n  {alias}.{group_col},\n  "
                    f"COUNT(*) AS row_count,\n  SUM({alias}.{agg_col}) AS total_{agg_col}\n"
                    f"FROM {table} AS {alias}\nGROUP BY {alias}.{group_col}"
                )
                explanation.append(
                    f"Analytics đơn giản: gộp theo '{group_col}' và tính "
                    f"COUNT/SUM trên '{agg_col}' "
                    "— chỉ dùng các cột thực tế từ schema."
                )
                sql = sql + "\n\n" + analytics

        return SqlResponse(
            dataset=entity.display_name or entity.name,
            urn=entity.urn,
            selected_columns=selected,
            unavailable_columns=[],
            sql=sql,
            joins=joins,
            explanation=explanation,
            valid=True,
        )
