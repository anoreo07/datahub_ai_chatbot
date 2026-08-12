"""Reusable, grounded services for the "+" action menu.

Every feature here retrieves metadata through the DataHub source (GraphQL) or
the synced database (populated from GraphQL). No knowledge is inferred from an
LLM; anything not found in the retrieved metadata is reported as missing.
"""
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field as _dc_field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.actions import (
    ImpactItem,
    ImpactResponse,
    ReportAssessment,
    ReportResponse,
    ReportSection,
    SchemaColumn,
    SchemaCompareResponse,
    SchemaMatchItem,
    SqlJoin,
    SqlResponse,
)
from app.schemas.chat import LineageData, LineageNode
from app.schemas.quality import (
    QualityFinding,
    QualityRecommendation,
    QualityReport,
    QualitySection,
    QualityStatus,
)
from app.services.quality_report import _rating_of
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from retrieval.entity_resolver import EntityResolver

log = structlog.get_logger()

# Jaccard similarity threshold for suggesting a dataset whose schema overlaps
# an uploaded schema. Kept low so a weak match is still *suggested* and ranked.
SCHEMA_MATCH_MIN_SIMILARITY = 0.15


def _norm(s: str | None) -> str:
    """Accent- and case-insensitive normalization for column/name matching."""
    if not s:
        return ""
    s = s.lower().strip()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


def _schema_columns(payload: dict | None) -> list[dict]:
    fields = (payload or {}).get("schema_fields") or []
    return [f for f in fields if isinstance(f, dict)]


# Column-like tokens (snake_case / dotted), e.g. "warehouse_id" or "fact.sales.order_id".
_FIELD_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", re.I)
# Flattened dotted identifiers (schema.table.column) also count as field candidates.
_FIELD_TOKEN_DOTTED_RE = re.compile(r"\b[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\b", re.I)

# Stop words / connector words never treated as a column filter even if they look
# snake_case-ish (mostly no-underscore, kept for safety).
_FIELD_STOP = {
    "where", "from", "select", "having", "group", "order", "by", "limit",
    "sql", "query", "dataset", "datasets", "table", "bang", "ba?ng",
    "truy", "van", "truy van", "cau", "lenh", "do", "cho", "cua", "de",
    "trong", "theo", "voi", "la", "co", "va", "ve", "gi", "nao", "the",
    "all", "any", "is", "not", "null",
}


def extract_filter_values(question: str, columns: Sequence[str]) -> dict[str, str]:
    """Best-effort ``col = 'value'`` filters from a natural-language query.

    Returns a mapping of existing column name -> extracted value, e.g. the
    question ``truy vấn đối tượng có warehouse_name là 'ABC123'`` yields
    ``{"warehouse_name": "ABC123"}``. Only columns that actually exist in the
    schema are matched, so the filter is always grounded.
    """
    out: dict[str, str] = {}
    if not question or not columns:
        return out
    for col in columns:
        if not col:
            continue
        m = re.search(
            r"\b" + re.escape(col) + r"\b"
            + r"\s*(?:is|=|==|là|la|bang|bằng|bằng|equals)\s*"
            + r"['\"“”]?\s*([^\"\s,;.()…]+(?:\s+[^\"\s,;.()…]+)*)"
            + r"\s*['\"”]?",
            question, re.I,
        )
        if m:
            value = m.group(1).strip().strip("'\"“”")
            if value:
                out[col] = value
    return out


def extract_filter_fields(question: str) -> list[str]:
    """Best-effort column tokens from a natural-language query.

    Returns normalized (lowercase) column-like identifiers such as
    ``warehouse_id``. Used to discover which datasets actually carry the filter
    field before generating SQL.
    """
    tokens: list[str] = []
    for m in _FIELD_TOKEN_RE.finditer(question):
        tokens.append(_norm(m.group(0)))
    for m in _FIELD_TOKEN_DOTTED_RE.finditer(question):
        tokens.append(_norm(m.group(0).rsplit(".", 1)[-1]))
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t and t not in _FIELD_STOP and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _query_tokens(question: str) -> set[str]:
    """Meaningful, normalized content words from the question (excl. connectors)."""
    n = _norm(question)
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


def _entity_text(e: "Entity") -> str:
    payload = e.payload or {}
    schema_bits: list[str] = []
    for f in (_schema_columns(payload)):
        if not isinstance(f, dict):
            continue
        schema_bits.append(str(f.get("name") or ""))
        schema_bits.append(str(f.get("description") or ""))
        schema_bits.append(str(f.get("comment") or ""))
    return _norm(" ".join([
        e.name or "", e.display_name or "",
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
    entity: "Entity"
    matched_fields: list[str]
    score: float
    reasons: list[str] = _dc_field(default_factory=list)


def _owner_names(payload: dict) -> list[str]:
    out: list[str] = []
    for o in payload.get("owners") or []:
        if isinstance(o, dict) and o.get("name"):
            out.append(str(o["name"]))
    return out


def _profiling_stats(payload: dict) -> dict | None:
    """Normalise profiling data into a flat stats dict, or None if unusable.

    Accepts either a dict with explicit keys or a dict wrapping per-column
    stats. Returns None when no profiling data is available so the report can
    fall back to metadata checks.
    """
    raw = payload.get("profiling")
    if raw is None:
        return None
    if isinstance(raw, list):
        # Legacy list of profiles -> take the first usable entry.
        raw = next((p for p in raw if isinstance(p, dict)), None)
        if raw is None:
            return None
    if not isinstance(raw, dict):
        return None
    if raw.get("column_stats") is None and raw.get("duplicate_rate") is None \
            and raw.get("row_count") is None:
        return None
    return raw


def _urn_kind(urn: str) -> str:
    if ":dashboard:" in urn or ":dashboard(" in urn:
        return "dashboard"
    if ":dataJob:" in urn or ":dataJob(" in urn:
        return "job"
    if ":dataFlow:" in urn or ":dataFlow(" in urn:
        return "pipeline"
    if ":dataset:" in urn or ":dataset(" in urn:
        return "dataset"
    if ":document:" in urn:
        return "document"
    return "other"


def _rating(score: int) -> tuple[str, int]:
    if score >= 80:
        return "Excellent", 5
    if score >= 60:
        return "Good", 4
    if score >= 40:
        return "Needs Improvement", 3
    if score > 0:
        return "Needs Improvement", 2
    return "Missing", 1


class PermissionDeniedError(Exception):
    """Raised when a user requests metadata from a domain their roles cannot
    access. Carries the localized authorization message for the API layer."""

    def __init__(self, message: str, domain: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.domain = domain


class ActionService:
    def __init__(self, session: AsyncSession,
                 auth_service: AuthorizationService | None = None) -> None:
        self._repo = EntityRepository(session)
        self._resolver = EntityResolver(session)
        self._source: DataHubSource = create_datahub_source()
        self._auth_service = auth_service

    # ------------------------------------------------------------------ #
    # Shared retrieval helpers
    # ------------------------------------------------------------------ #
    async def resolve_dataset(
        self, query: str, *, user: UserContext | None = None
    ) -> Entity | None:
        if not query:
            return None
        resolution = await self._resolver.resolve(query, entity_type="dataset")
        if not resolution.resolved:
            return None
        entity = await self._repo.get_by_urn(resolution.resolved.urn)
        if entity is None:
            return None
        if user is not None and not await self._is_accessible(user, entity.urn):
            return None
        if user is not None and self._auth_service is not None:
            domain = (entity.domain or (entity.payload or {}).get("domain") or "").strip()
            if domain:
                message = await self._auth_service.access_message(user, domain)
                if message:
                    log.info("action_domain_denied", user=user.user_id,
                             dataset=query[:100], domain=domain)
                    raise PermissionDeniedError(message, domain=domain)
        return entity

    async def _is_accessible(self, user: UserContext, urn: str) -> bool:
        if self._auth_service is None:
            return True
        accessible = await self._auth_service.filter_accessible_urns(user, [urn])
        return urn in accessible

    async def _resolve_urns(self, urns: Sequence[str]) -> dict[str, Entity]:
        out: dict[str, Entity] = {}
        for e in await self._repo.list_by_urns(list(dict.fromkeys(urns))):
            out[e.urn] = e
        return out

    async def _lineage_urns(self, urn: str) -> tuple[list[str], list[str]]:
        """Live upstream/downstream URNs retrieved from the DataHub source."""
        upstreams: list[str] = []
        downstreams: list[str] = []
        try:
            up = await self._source.get_lineage(urn, direction="upstream")
            down = await self._source.get_lineage(urn, direction="downstream")
            upstreams = [r["entity"]["urn"] for r in up.get("relationships", [])
                         if (r.get("entity") or {}).get("urn")]
            downstreams = [r["entity"]["urn"] for r in down.get("relationships", [])
                           if (r.get("entity") or {}).get("urn")]
        except Exception:
            log.exception("action_lineage_failed", urn=urn)
        return upstreams, downstreams

    async def build_lineage_data(self, urn: str, name: str, url: str | None) -> LineageData | None:
        upstreams, downstreams = await self._lineage_urns(urn)
        nodes = await self._resolve_urns(upstreams + downstreams)

        def _nodes(urns: Sequence[str]) -> list[LineageNode]:
            result: list[LineageNode] = []
            for u in urns:
                if u == urn:
                    continue
                e = nodes.get(u)
                if e:
                    result.append(LineageNode(name=e.display_name or e.name, urn=e.urn,
                                              url=e.datahub_url, entity_type=e.entity_type))
                else:
                    result.append(LineageNode(name=u, urn=u))
            return result

        if not upstreams and not downstreams:
            return None
        return LineageData(entity_name=name, entity_urn=urn, entity_url=url,
                           upstreams=_nodes(upstreams), downstreams=_nodes(downstreams))

    # ------------------------------------------------------------------ #
    # 1. Upload Document -> schema comparison (Grounded RAG)
    # ------------------------------------------------------------------ #
    async def compare_schema(self, columns: Sequence[SchemaColumn],
                             preferred_query: str = "",
                             limit: int = 5,
                             user: UserContext | None = None) -> SchemaCompareResponse:
        uploaded = {_norm(c.name) for c in columns if c.name}
        if not uploaded:
            return SchemaCompareResponse(candidates=[], total=0)

        # Prefer a user-named dataset, but still compute matches for all tables
        # so the comparison list is complete.
        datasets = await self._repo.list_by_type("dataset", limit=2000)

        def _jaccard(a: set[str], b: set[str]) -> float:
            union = a | b
            if not union:
                return 0.0
            return len(a & b) / len(union)

        scored: list[tuple[float, Entity]] = []
        for ds in datasets:
            ds_cols = {_norm(f.get("name") or "") for f in _schema_columns(ds.payload)}
            if not ds_cols:
                continue
            sim = _jaccard(uploaded, ds_cols)
            if sim >= SCHEMA_MATCH_MIN_SIMILARITY:
                scored.append((sim, ds))

        scored.sort(key=lambda t: -t[0])

        # Rank an explicitly-preferred dataset first when it overlaps at all.
        preferred = None
        if preferred_query:
            preferred = await self.resolve_dataset(preferred_query, user=user)
        if preferred:
            scored.sort(key=lambda t: (t[1].urn != preferred.urn, -t[0]))

        if self._auth_service is not None and user is not None:
            accessible = await self._auth_service.filter_accessible_urns(
                user, [e.urn for _, e in scored]
            )
            allowed = [t for t in scored if t[1].urn in accessible]
        else:
            allowed = list(scored)

        items: list[SchemaMatchItem] = []
        for sim, ds in allowed[:limit]:
            ds_cols = {_norm(f.get("name") or "") for f in _schema_columns(ds.payload)}
            matched = sorted(uploaded & ds_cols)
            missing = sorted(uploaded - ds_cols)
            additional = sorted(ds_cols - uploaded)
            payload = ds.payload or {}
            items.append(SchemaMatchItem(
                urn=ds.urn, name=ds.display_name or ds.name,
                description=(payload.get("description") or ""),
                platform=(payload.get("platform") or ""),
                domain=(payload.get("domain") or ""),
                url=ds.datahub_url, similarity=round(sim, 3),
                matched_columns=matched, missing_columns=missing,
                additional_columns=additional,
            ))
        return SchemaCompareResponse(candidates=items, total=len(items))

    # ------------------------------------------------------------------ #
    # 3. SQL Generator
    # ------------------------------------------------------------------ #
    async def discover_sql_candidates(self, question: str,
                                      user: UserContext | None = None,
                                      limit: int = 5) -> list[SqlCandidate]:
        """Field-aware dataset discovery for a SQL/filter request.

        Scans every accessible dataset's schema for the filter columns mentioned
        in ``question``, then ranks the matches by schema overlap and how well the
        dataset's metadata (name, description, glossary, domain) matches the rest
        of the question. Never falls back to name-substring entity search: a
        dataset is a candidate only when its schema actually carries the field or
        its metadata is strongly relevant to the question.
        """
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
            schema = _schema_columns(payload)
            norm_to_orig: dict[str, str] = {
                _norm(f.get("name") or ""): (f.get("name") or "").strip()
                for f in schema if f.get("name")
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
                reasons.append("mô tả/domain/glossary khớp từ '" +
                           "', '".join(matched_tokens) + "'")

            if score > 0:
                candidates.append(SqlCandidate(
                    entity=ds, matched_fields=matched,
                    score=round(score, 3), reasons=reasons,
                ))

        candidates.sort(key=lambda c: -c.score)
        log.info("sql_discover_candidates", question=question[:100],
                 filter_fields=filter_fields, query_tokens=sorted(query_tokens),
                 candidate_count=len(candidates), top=[
                     (c.entity.display_name or c.entity.name, c.score)
                     for c in candidates[:3]
                 ])
        return candidates[:limit]

    async def generate_sql(self, dataset_query: str, requested_columns: Sequence[str] = (),
                           user: UserContext | None = None,
                           question: str = "") -> SqlResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return SqlResponse(dataset=dataset_query, explanation=[
                "Không tìm thấy dataset phù hợp trong metadata DataHub."
            ], valid=False)

        payload = entity.payload or {}
        cols = _schema_columns(payload)
        actual: list[str] = []
        dateless: list[str] = []
        numeric: list[str] = []
        for f in cols:
            name = (f.get("name") or "").strip()
            if not name:
                continue
            actual.append(name)
            ftype = _norm(f.get("type") or f.get("native_data_type") or "")
            if ftype in {"date", "timestamp", "datetime"}:
                dateless.append(name)
            if any(k in ftype for k in ("int", "decimal", "numeric", "float", "double", "money")):
                numeric.append(name)

        if not actual:
            return SqlResponse(dataset=entity.display_name or entity.name, urn=entity.urn,
                               explanation=[
                                   "Dataset này chưa có schema được ghi nhận trong DataHub.",
                               ],
                               valid=False)

        actual_norm = {_norm(c): c for c in actual}
        requested_norm = [_norm(c) for c in requested_columns if c]
        if requested_columns:
            unavailable = [orig for orig, n in zip(requested_columns, requested_norm)
                           if n not in actual_norm]
            if unavailable:
                return SqlResponse(
                    dataset=entity.display_name or entity.name, urn=entity.urn,
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
        main_norm = {_norm(c) for c in selected}
        for up_urn in upstreams:
            up = upstream_entities.get(up_urn)
            if up is None:
                continue
            up_cols = [_norm(f.get("name") or "") for f in _schema_columns(up.payload)]
            shared = sorted(main_norm & set(up_cols))
            if not shared:
                continue
            shared_col = shared[0]
            join_tables.append((up, shared_col))
            joins.append(SqlJoin(
                table=up.display_name or up.name, column=shared_col,
                reason=(up.payload or {}).get("description")
                        or f"Bảng nguồn upstream của {entity.display_name or entity.name}.",
            ))

        table = entity.name
        alias = "t"
        lines = ["SELECT",
                 "  " + ",\n  ".join(f"{alias}.{c}" for c in selected),
                 f"FROM {table} AS {alias}"]
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
        sql = "\n".join(lines)

        explanation: list[str] = []
        description = (payload.get("description") or "").strip()
        if description:
            explanation.append(f"Bảng {entity.display_name or entity.name}: {description}")
        else:
            explanation.append(
                f"Bảng {entity.display_name or entity.name}: không có mô tả trong DataHub.",
            )
        for j in joins:
            explanation.append(f"JOIN {j.table} (cột chung '{j.column}'). {j.reason}")
        for col, value in filters.items():
            explanation.append(
                f"Lọc theo {col} = '{value}' (trích từ câu hỏi, chỉ dùng cột có trong schema)."
            )

        if numeric and dateless:
            agg_col = next((c for c in selected if _norm(c) in {_norm(x) for x in numeric}), "")
            group_col = next((c for c in selected if _norm(c) in {_norm(x) for x in dateless}), "")
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
            dataset=entity.display_name or entity.name, urn=entity.urn,
            selected_columns=selected, unavailable_columns=[],
            sql=sql, joins=joins, explanation=explanation, valid=True,
        )

    # ------------------------------------------------------------------ #
    # 4. Impact Analysis
    # ------------------------------------------------------------------ #
    async def impact_analysis(self, dataset_query: str,
                              user: UserContext | None = None) -> ImpactResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return ImpactResponse(dataset=dataset_query,
                                  business_impact=[
                                     "Không tìm thấy dataset trong metadata DataHub.",
                                 ],
                                  valid=False)

        upstreams, downstreams = await self._lineage_urns(entity.urn)
        entities = await self._resolve_urns(downstreams)
        dashboards: list[ImpactItem] = []
        datasets: list[ImpactItem] = []
        pipelines: list[ImpactItem] = []
        jobs: list[ImpactItem] = []

        for d_urn in downstreams:
            e = entities.get(d_urn)
            name = (e.display_name or e.name) if e else d_urn
            kind = _urn_kind(d_urn)
            item = ImpactItem(urn=d_urn, name=name, url=e.datahub_url if e else None, kind=kind)
            if kind == "dashboard":
                dashboards.append(item)
            elif kind == "pipeline":
                pipelines.append(item)
            elif kind == "job":
                jobs.append(item)
            else:
                datasets.append(item)

        # Also consider dashboards that reference this dataset in their payload.
        if self._auth_service is None or user is None or user.is_admin:
            for dash in await self._repo.list_by_type("dashboard", limit=1000):
                up_urns = set((dash.payload or {}).get("upstreams") or [])
                if entity.urn in up_urns and dash.urn not in {d.urn for d in dashboards}:
                    dashboards.append(ImpactItem(urn=dash.urn,
                                                 name=dash.display_name or dash.name,
                                                 url=dash.datahub_url, kind="dashboard"))

        total = len(datasets) + len(dashboards) + len(pipelines) + len(jobs)
        risk = "low"
        if total >= 6:
            risk = "high"
        elif total >= 3:
            risk = "medium"

        business_impact: list[str] = []
        if datasets:
            business_impact.append(
                f"{len(datasets)} dataset hạ nguồn phụ thuộc vào dataset này: "
                + ", ".join(d.name for d in datasets[:5])
                + ("..." if len(datasets) > 5 else "") + "."
            )
        if dashboards:
            business_impact.append(
                f"{len(dashboards)} dashboard có thể bị ảnh hưởng: "
                + ", ".join(d.name for d in dashboards[:5])
                + ("..." if len(dashboards) > 5 else "") + "."
            )
        if pipelines:
            business_impact.append(f"{len(pipelines)} pipeline có thể bị ảnh hưởng.")
        if jobs:
            business_impact.append(f"{len(jobs)} job có thể bị ảnh hưởng.")
        if not business_impact:
            business_impact.append("Không tìm thấy phụ thuộc hạ nguồn nào từ lineage DataHub.")

        return ImpactResponse(
            dataset=entity.display_name or entity.name, urn=entity.urn,
            affected_datasets=datasets, affected_dashboards=dashboards,
            affected_pipelines=pipelines, affected_jobs=jobs,
            business_impact=business_impact, risk_level=risk, valid=True,
        )

    # ------------------------------------------------------------------ #
    # 6. Data Quality Check
    # ------------------------------------------------------------------ #
    async def quality_check(self, dataset_query: str,
                            user: UserContext | None = None) -> QualityReport:
        """Build a professional, deterministic Data Quality Report.

        When profiling data is available (``payload['profiling']``) real metrics
        are computed: NULL %, duplicate rate, record-count anomalies, schema
        drift, freshness. Otherwise the report gracefully falls back to metadata
        quality checks (description, owner, tags, glossary, domain, schema
        completeness, lineage, deprecation, assertions) and clearly lists which
        checks could not be evaluated.
        """
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return QualityReport(dataset=dataset_query, valid=False)

        payload = entity.payload or {}
        generated_at = QualityReport.now_iso()
        generated_by = ""
        if user is not None:
            generated_by = user.display_name or user.user_id or ""

        profiling = _profiling_stats(payload)
        profiling_available = profiling is not None

        description = (payload.get("description") or "").strip()
        owners = _owner_names(payload)
        tags = [str(t) for t in (payload.get("tags") or [])]
        glossary = [str(g) for g in (payload.get("glossary_terms") or [])]
        domain = (payload.get("domain") or "").strip()
        platform = (payload.get("platform") or "").strip()
        environment = (payload.get("environment") or "").strip()
        schema = _schema_columns(payload)
        deprecated = bool(payload.get("deprecated"))
        assertions = payload.get("assertions") or []
        upstreams, downstreams = await self._lineage_urns(entity.urn)
        has_lineage = bool(upstreams or downstreams)

        def section(key: str, title: str, findings: list[QualityFinding]) -> QualitySection:
            score = 100
            for f in findings:
                if f.status == QualityStatus.FAILED:
                    score -= 45
                elif f.status == QualityStatus.WARNING:
                    score -= 18
            score = max(0, min(100, score))
            status = QualityStatus.PASSED
            if any(f.status == QualityStatus.FAILED for f in findings):
                status = QualityStatus.FAILED
            elif any(f.status == QualityStatus.WARNING for f in findings):
                status = QualityStatus.WARNING
            elif any(f.status == QualityStatus.PASSED for f in findings):
                status = QualityStatus.PASSED
            else:
                status = QualityStatus.NOT_EVALUATED
            return QualitySection(key=key, title=title, score=score,
                                  status=status, findings=findings)

        sections: list[QualitySection] = []
        not_evaluated: list[str] = []

        # ---------------- Metadata ----------------
        meta: list[QualityFinding] = []
        if deprecated:
            meta.append(QualityFinding(
                name="Deprecation status", status=QualityStatus.FAILED,
                detail="Dataset bị đánh dấu deprecated, không nên dùng cho báo cáo mới."))
        else:
            meta.append(QualityFinding(
                name="Deprecation status", status=QualityStatus.PASSED,
                detail="Dataset chưa bị deprecated."))
        if not description:
            meta.append(QualityFinding(
                name="Business description", status=QualityStatus.FAILED,
                detail="Thiếu mô tả business."))
        elif len(description) < 50:
            meta.append(QualityFinding(
                name="Business description", status=QualityStatus.WARNING,
                detail=(f"Mô tả quá ngắn ({len(description)} ký tự), "
                        "nên mở rộng ngữ cảnh nghiệp vụ."),
                value=f"{len(description)} ký tự"))
        else:
            meta.append(QualityFinding(
                name="Business description", status=QualityStatus.PASSED,
                detail="Mô tả business đầy đủ.", value=f"{len(description)} ký tự"))
        if owners:
            meta.append(QualityFinding(
                name="Ownership", status=QualityStatus.PASSED,
                detail=f"Owner: {', '.join(owners)}.", value=str(len(owners))))
        else:
            meta.append(QualityFinding(
                name="Ownership", status=QualityStatus.FAILED,
                detail="Chưa gán owner — không rõ ai chịu trách nhiệm dữ liệu."))
        if tags:
            meta.append(QualityFinding(
                name="Tags", status=QualityStatus.PASSED,
                detail="Có tag phân loại.", value=str(len(tags))))
        else:
            meta.append(QualityFinding(
                name="Tags", status=QualityStatus.WARNING,
                detail="Chưa có tag — khó tìm kiếm và phân loại."))
        if glossary:
            meta.append(QualityFinding(
                name="Glossary terms", status=QualityStatus.PASSED,
                detail="Dataset được gắn glossary term nghiệp vụ.",
                value=str(len(glossary))))
        else:
            meta.append(QualityFinding(
                name="Glossary terms", status=QualityStatus.WARNING,
                detail="Chưa gắn glossary term — thiếu ngữ nghĩa chuẩn hoá."))
        if domain:
            meta.append(QualityFinding(
                name="Domain", status=QualityStatus.PASSED,
                detail=f"Thuộc domain {domain}.", value=domain))
        else:
            meta.append(QualityFinding(
                name="Domain", status=QualityStatus.WARNING,
                detail="Chưa gán domain — thiếu cơ chế quản trị theo phòng ban."))
        if platform and environment:
            meta.append(QualityFinding(
                name="Platform & environment", status=QualityStatus.PASSED,
                detail=f"Chạy trên {platform} · {environment}.",
                value=f"{platform}/{environment}"))
        else:
            meta.append(QualityFinding(
                name="Platform & environment", status=QualityStatus.WARNING,
                detail="Thiếu thông tin platform/environment."))
        sections.append(section("metadata", "Metadata", meta))

        # ---------------- Schema ----------------
        schema_findings: list[QualityFinding] = []
        if not schema:
            schema_findings.append(QualityFinding(
                name="Schema presence", status=QualityStatus.FAILED,
                detail="Dataset không có schema nào được ghi nhận trong DataHub."))
        else:
            schema_findings.append(QualityFinding(
                name="Schema presence", status=QualityStatus.PASSED,
                detail="Schema có sẵn.", value=f"{len(schema)} cột"))
            with_type = sum(1 for f in schema if (f.get("type") or f.get("native_data_type")))
            if with_type == len(schema):
                schema_findings.append(QualityFinding(
                    name="Column types", status=QualityStatus.PASSED,
                    detail="Tất cả cột đều có kiểu dữ liệu."))
            elif with_type > 0:
                schema_findings.append(QualityFinding(
                    name="Column types", status=QualityStatus.WARNING,
                    detail=f"{len(schema) - with_type} cột thiếu kiểu dữ liệu.",
                    value=f"{with_type}/{len(schema)}"))
            else:
                schema_findings.append(QualityFinding(
                    name="Column types", status=QualityStatus.FAILED,
                    detail="Không cột nào có kiểu dữ liệu."))
            documented = sum(1 for f in schema if (f.get("description") or "").strip())
            doc_ratio = documented / len(schema)
            if doc_ratio >= 0.8:
                schema_findings.append(QualityFinding(
                    name="Column documentation", status=QualityStatus.PASSED,
                    detail="Hầu hết cột có mô tả.",
                    value=f"{documented}/{len(schema)}"))
            elif doc_ratio >= 0.5:
                schema_findings.append(QualityFinding(
                    name="Column documentation", status=QualityStatus.WARNING,
                    detail="Một phần cột thiếu mô tả.",
                    value=f"{documented}/{len(schema)}"))
            else:
                schema_findings.append(QualityFinding(
                    name="Column documentation", status=QualityStatus.WARNING,
                    detail="Ít cột có mô tả — schema khó hiểu.",
                    value=f"{documented}/{len(schema)}"))
        if profiling is not None and profiling.get("schema_drift"):
            drift = profiling["schema_drift"]
            drift_status = (
                QualityStatus.PASSED if not drift.get("detected") else QualityStatus.FAILED
            )
            schema_findings.append(QualityFinding(
                name="Schema drift", status=drift_status,
                detail=(f"Schema thay đổi không khớp "
                        f"({drift.get('detail') or 'phát hiện thay đổi'})."
                        if drift.get("detected")
                        else "Không phát hiện thay đổi schema bất thường.")))
        else:
            schema_findings.append(QualityFinding(
                name="Schema drift", status=QualityStatus.NOT_EVALUATED,
                detail="Không thể đánh giá — thiếu dữ liệu profiling schema drift."))
            not_evaluated.append("Schema drift")
        sections.append(section("schema", "Schema", schema_findings))

        # ---------------- Completeness (data) ----------------
        comp_findings: list[QualityFinding] = []
        if profiling is not None and profiling.get("column_stats"):
            stats = profiling["column_stats"]
            null_rates = [float(c.get("null_rate", 0.0) or c.get("null_percentage", 0.0) or 0.0)
                          for c in stats]
            worst = sorted(stats, key=lambda c: float(c.get("null_rate", 0.0) or 0.0),
                           reverse=True)[:3]
            avg_null = sum(null_rates) / len(null_rates) if null_rates else 0.0
            comp_findings.append(QualityFinding(
                name="Record completeness (non-null)", status=(
                    QualityStatus.PASSED if avg_null < 5 else
                    QualityStatus.WARNING if avg_null < 20 else QualityStatus.FAILED),
                detail=f"Trung bình {avg_null:.1f}% giá trị NULL trên các cột.",
                value=f"{100 - avg_null:.1f}%"))
            for c in worst:
                rate = float(c.get("null_rate", 0.0) or 0.0)
                if rate > 0:
                    comp_findings.append(QualityFinding(
                        name=f"NULL rate — {c.get('name')}", status=(
                            QualityStatus.PASSED if rate < 5 else
                            QualityStatus.WARNING if rate < 20 else QualityStatus.FAILED),
                        detail=("Không có NULL." if rate == 0 else f"{rate:.1f}% giá trị NULL."),
                        value=f"{rate:.1f}%"))
        else:
            comp_findings.append(QualityFinding(
                name="Completeness (NULL %)",
                status=QualityStatus.NOT_EVALUATED,
                detail="Không thể tính NULL percentage — thiếu dữ liệu profiling."))
            not_evaluated.append("Completeness (NULL percentage)")
        sections.append(section("completeness", "Completeness", comp_findings))

        # ---------------- Uniqueness ----------------
        uni_findings: list[QualityFinding] = []
        if profiling is not None and profiling.get("duplicate_rate") is not None:
            dup = float(profiling["duplicate_rate"])
            uni_findings.append(QualityFinding(
                name="Duplicate rate", status=(
                    QualityStatus.PASSED if dup == 0 else
                    QualityStatus.WARNING if dup < 5 else QualityStatus.FAILED),
                detail=f"Tỉ lệ bản ghi trùng lặp {dup:.2f}%.", value=f"{dup:.2f}%"))
        else:
            uni_findings.append(QualityFinding(
                name="Duplicate rate",
                status=QualityStatus.NOT_EVALUATED,
                detail="Không thể tính duplicate rate — thiếu dữ liệu profiling."))
            not_evaluated.append("Duplicate rate")
        sections.append(section("uniqueness", "Uniqueness", uni_findings))

        # ---------------- Validity ----------------
        val_findings: list[QualityFinding] = []
        if assertions:
            val_findings.append(QualityFinding(
                name="Assertions", status=QualityStatus.PASSED,
                detail="Có assertions giám sát dữ liệu.", value=str(len(assertions))))
        else:
            val_findings.append(QualityFinding(
                name="Assertions", status=QualityStatus.WARNING,
                detail="Chưa có assertions — không có ràng buộc giám sát tự động."))
        if profiling is not None and profiling.get("column_stats"):
            bad_types = [c for c in profiling["column_stats"]
                         if c.get("type_validity") and float(c["type_validity"]) < 0.9]
            if bad_types:
                val_findings.append(QualityFinding(
                    name="Type validity", status=QualityStatus.FAILED,
                    detail=f"{len(bad_types)} cột có dữ liệu sai kiểu.",
                    value=str(len(bad_types))))
            else:
                val_findings.append(QualityFinding(
                    name="Type validity", status=QualityStatus.PASSED,
                    detail="Kiểu dữ liệu của cột khớp với dữ liệu lưu trữ."))
        else:
            val_findings.append(QualityFinding(
                name="Type validity (profiling)",
                status=QualityStatus.NOT_EVALUATED,
                detail="Không thể kiểm tra kiểu dữ liệu — thiếu profiling."))
            not_evaluated.append("Type validity (profiling)")
        sections.append(section("validity", "Validity", val_findings))

        # ---------------- Consistency ----------------
        con_findings: list[QualityFinding] = []
        if profiling is not None and profiling.get("row_count") is not None:
            row_count = int(profiling["row_count"])
            delta = profiling.get("row_count_delta_pct")
            if delta is None:
                con_findings.append(QualityFinding(
                    name="Record count", status=QualityStatus.PASSED,
                    detail=(f"Tổng số bản ghi {row_count} — không có dữ liệu "
                            "lịch sử để so sánh."),
                    value=str(row_count)))
            else:
                con_findings.append(QualityFinding(
                    name="Record count anomaly", status=(
                        QualityStatus.PASSED if abs(float(delta)) < 20 else QualityStatus.FAILED),
                    detail=f"Số bản ghi thay đổi {float(delta):+.1f}% so với kỳ trước.",
                    value=f"{delta:+.1f}%"))
        else:
            con_findings.append(QualityFinding(
                name="Record count anomaly",
                status=QualityStatus.NOT_EVALUATED,
                detail="Không thể đánh giá biến động số bản ghi — thiếu profiling."))
            not_evaluated.append("Record count anomaly")
        if platform and domain:
            con_findings.append(QualityFinding(
                name="Metadata consistency",
                status=QualityStatus.PASSED,
                detail="Platform và domain nhất quán trong metadata."))
        sections.append(section("consistency", "Consistency", con_findings))

        # ---------------- Freshness ----------------
        fresh_findings: list[QualityFinding] = []
        freshness = payload.get("freshness")
        if isinstance(freshness, dict) and freshness.get("last_updated"):
            last_updated = str(freshness.get("last_updated"))
            frequency = str(freshness.get("frequency") or "không rõ tần suất")
            fresh_findings.append(QualityFinding(
                name="Freshness", status=QualityStatus.PASSED,
                detail=f"Dữ liệu cập nhật lần cuối {last_updated} (tần suất {frequency}).",
                value=last_updated))
        else:
            fresh_findings.append(QualityFinding(
                name="Freshness",
                status=QualityStatus.NOT_EVALUATED,
                detail="Không thể đánh giá — thiếu thông tin freshness/profiling."))
            not_evaluated.append("Freshness")
        sections.append(section("freshness", "Freshness", fresh_findings))

        # ---------------- Lineage ----------------
        if has_lineage:
            lineage_findings = [QualityFinding(
                name="Lineage coverage", status=QualityStatus.PASSED,
                detail=f"{len(upstreams)} upstream, {len(downstreams)} downstream.",
                value=f"{len(upstreams)}↑/{len(downstreams)}↓")]
        else:
            lineage_findings = [QualityFinding(
                name="Lineage coverage", status=QualityStatus.FAILED,
                detail="Không có lineage upstream/downstream — khó truy vết nguồn dữ liệu.")]
        sections.append(section("lineage", "Lineage", lineage_findings))

        # ---------------- Recommendations ----------------
        recommendations: list[QualityRecommendation] = []
        seen = set()

        def _rec(priority: str, text: str) -> None:
            if text in seen:
                return
            seen.add(text)
            recommendations.append(QualityRecommendation(priority=priority, text=text))

        if deprecated:
            _rec("high", "Dataset đang bị deprecated. Chuyển sang dataset thay thế "
                          "và cập nhật tài liệu tiêu thụ.")
        if not description or len(description) < 50:
            _rec("high", "Bổ sung mô tả business đầy đủ (tối thiểu 50 ký tự) "
                          "để ngữ cảnh hoá dữ liệu.")
        if not owners:
            _rec("high", "Gán owner chịu trách nhiệm dữ liệu để quản trị trách nhiệm rõ ràng.")
        if not tags:
            _rec("medium", "Thêm tag phân loại (PII, Gold/Silver/Bronze, phòng ban…) "
                            "để dễ tìm kiếm.")
        if not glossary:
            _rec("medium", "Gắn glossary term tương ứng để chuẩn hoá ngữ nghĩa nghiệp vụ.")
        if not domain:
            _rec("high", "Gán dataset vào một domain để áp dụng chính sách truy cập "
                          "theo phòng ban.")
        if not assertions:
            _rec("medium", "Thiết lập assertions (freshness, NULL threshold, volume) "
                            "để giám sát tự động.")
        if not has_lineage:
            _rec("high", "Thiết lập lineage để theo dõi luồng dữ liệu và đánh giá "
                          "tác động hạ nguồn.")
        if profiling_available:
            worst_nulls = None
            if profiling and profiling.get("column_stats"):
                stats = profiling["column_stats"]
                bad = [c for c in stats
                       if float(c.get("null_rate", 0.0) or 0.0) >= 20]
                if bad:
                    worst_nulls = ", ".join(str(c.get("name")) for c in bad[:5])
                    _rec("high", f"Cột {worst_nulls} có tỉ lệ NULL cao (>=20%) — "
                                  "kiểm tra nguồn dữ liệu và quy trình nhập liệu.")
            dup = profiling.get("duplicate_rate") if profiling else None
            if dup is not None and float(dup) > 0:
                _rec("high", f"Phát hiện {float(dup):.2f}% bản ghi trùng lặp — cần "
                              "định nghĩa khoá duy nhất (PK) và thêm assertion uniqueness.")
            delta = profiling.get("row_count_delta_pct") if profiling else None
            if delta is not None and abs(float(delta)) >= 20:
                _rec("medium", f"Số bản ghi biến động {float(delta):+.1f}% so với kỳ trước "
                                "— kiểm tra pipeline ingestion.")
        else:
            _rec("medium", "Bật profiling (null %, duplicate %, row count) để đánh giá "
                            "Completeness/Uniqueness/Consistency thực tế.")

        evaluated_sections = [s for s in sections if s.status != QualityStatus.NOT_EVALUATED]
        overall = int(sum(s.score for s in evaluated_sections) / len(evaluated_sections)) \
            if evaluated_sections else 0
        rating = _rating_of(overall)

        return QualityReport(
            dataset=entity.display_name or entity.name,
            urn=entity.urn,
            url=entity.datahub_url,
            generated_at=generated_at,
            generated_by=generated_by,
            overall_score=overall,
            rating=rating,
            profiling_available=profiling_available,
            sections=sections,
            recommendations=recommendations,
            not_evaluated_checks=sorted(set(not_evaluated)),
            valid=True,
        )

    # ------------------------------------------------------------------ #
    # 7. Metadata Report
    # ------------------------------------------------------------------ #
    async def metadata_report(self, dataset_query: str,
                              user: UserContext | None = None) -> ReportResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return ReportResponse(dataset=dataset_query,
                                  recommendations=[
                             "Không tìm thấy dataset trong metadata DataHub.",
                         ],
                                  valid=False)
        payload = entity.payload or {}
        description = (payload.get("description") or "").strip()
        business_purpose = (payload.get("business_purpose") or "").strip()
        owners = _owner_names(payload)
        tags = [str(t) for t in (payload.get("tags") or [])]
        glossary = [str(g) for g in (payload.get("glossary_terms") or [])]
        domain = (payload.get("domain") or "").strip()
        platform = (payload.get("platform") or "").strip()
        environment = (payload.get("environment") or "").strip()
        certified = bool(payload.get("certified"))
        schema = _schema_columns(payload)
        upstreams, downstreams = await self._lineage_urns(entity.urn)

        sections: list[ReportSection] = []
        sections.append(ReportSection(title="Dataset Overview", lines=[
            f"- Name: {entity.display_name or entity.name}",
            f"- Platform: {platform or '(chưa có)'} · Environment: {environment or '(chưa có)'}"
            + (f" · Domain: {domain}" if domain else ""),
            f"- URN: {entity.urn}",
        ]))
        sections.append(ReportSection(title="Business Description", lines=[
            business_purpose or description or "(chưa có mô tả business)",
        ]))
        sections.append(ReportSection(title="Technical Summary", lines=[
            f"- {len(schema)} cột trong schema",
            f"- {len(upstreams)} upstream · {len(downstreams)} downstream",
            f"- Certified: {'Có' if certified else 'Không'}",
        ]))
        schema_lines = [f"- {f.get('name')} ({f.get('type') or f.get('native_data_type') or '?'})"
                        + (f": {f.get('description')}" if f.get("description") else "")
                        for f in schema]
        sections.append(ReportSection(title="Schema Summary",
                                      lines=schema_lines[:30] or ["(không có schema)"]))

        sections.append(ReportSection(title="Ownership", lines=[
            "; ".join(owners) if owners else "(chưa có owner)",
        ]))
        sections.append(ReportSection(title="Glossary", lines=[
            " · ".join(glossary) if glossary else "(chưa gắn glossary term)",
        ]))
        sections.append(ReportSection(title="Tags", lines=[
            " · ".join(tags) if tags else "(chưa có tag)",
        ]))
        lineage_lines: list[str] = []
        if upstreams:
            lineage_lines.append("Upstream:")
            lineage_lines += [f"- {u}" for u in upstreams]
        else:
            lineage_lines.append("Upstream: (không có)")
        if downstreams:
            lineage_lines.append("Downstream:")
            lineage_lines += [f"- {d}" for d in downstreams]
        else:
            lineage_lines.append("Downstream: (không có)")
        sections.append(ReportSection(title="Lineage", lines=lineage_lines))
        sections.append(ReportSection(title="Data Quality", lines=[
            f"- Assertions: {len(payload.get('assertions') or [])}",
            f"- Profiling: {'Có' if payload.get('profiling') else 'Chưa có'}",
            f"- Freshness: {'Có' if payload.get('freshness') else 'Chưa có'}",
        ]))
        sections.append(ReportSection(title="Documentation Quality", lines=[
            f"- Độ dài mô tả: {len(description)} ký tự",
        ]))

        def _pct(cond: bool) -> int:
            return 100 if cond else 0

        assessment: list[ReportAssessment] = []
        assessment.append(
            self._assess("Metadata Completeness",
                         _pct(bool(description)) + (50 if description else 0),
            ),
        )
        assessment.append(
            self._assess(
                "Documentation Quality",
                                    100 if len(description) >= 50 else (60 if description else 0),
            ),
        )
        assessment.append(
            self._assess(
                "Governance Readiness",
                                       int((sum([bool(domain), bool(owners), bool(tags),
                                                 bool(glossary)]) / 4) * 100),
            ),
        )
        assessment.append(
            self._assess(
                "Discoverability",
                int(((len(description) > 0) + bool(tags) + bool(glossary)) / 3 * 100),
            ),
        )
        assessment.append(self._assess("Lineage Completeness",
                                       _pct(bool(upstreams or downstreams))))
        assessment.append(self._assess("Overall Metadata Maturity",
                                       int(((100 if description else 0) + (100 if owners else 0)
                                            + (100 if domain else 0) + (100 if tags else 0)
                                            + (100 if bool(upstreams or downstreams) else 0)) / 5)))

        overall_score = assessment[-1].score
        overall_rating, _ = _rating(overall_score)

        recommendations: list[str] = []
        if not description:
            recommendations.append("Cải thiện mô tả (Improve Description)")
        if not owners:
            recommendations.append("Gán owner (Assign Owner)")
        if not glossary:
            recommendations.append("Thêm glossary (Add Glossary)")
        if not tags:
            recommendations.append("Cải thiện tags (Improve Tags)")
        if not payload.get("assertions"):
            recommendations.append("Thêm assertions (Add Assertions)")
        if not payload.get("profiling"):
            recommendations.append("Bật profiling (Enable Profiling)")
        if not upstreams and not downstreams:
            recommendations.append("Thêm lineage (Add Lineage)")
        if not recommendations:
            recommendations.append("Metadata đã đầy đủ. Duy trì cập nhật định kỳ.")

        return ReportResponse(
            dataset=entity.display_name or entity.name, urn=entity.urn,
            sections=sections, assessment=assessment,
            overall_score=overall_score, overall_rating=overall_rating,
            recommendations=recommendations, valid=True,
        )

    @staticmethod
    def _assess(dimension: str, score: int) -> ReportAssessment:
        rating, stars = _rating(score)
        return ReportAssessment(dimension=dimension, score=min(100, score),
                                rating=rating, stars=stars)
