"""Reusable, grounded services for the "+" action menu.

Every feature here retrieves metadata through the DataHub source (GraphQL) or
the synced database (populated from GraphQL). No knowledge is inferred from an
LLM; anything not found in the retrieved metadata is reported as missing.
"""
import unicodedata
from collections.abc import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.actions import (
    ImpactItem,
    ImpactResponse,
    QualityDimension,
    QualityResponse,
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


def _owner_names(payload: dict) -> list[str]:
    out: list[str] = []
    for o in payload.get("owners") or []:
        if isinstance(o, dict) and o.get("name"):
            out.append(str(o["name"]))
    return out


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
    async def resolve_dataset(self, query: str, *, user: UserContext | None = None) -> Entity | None:
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
            ds_cols = {_norm((f.get("name") or "")) for f in _schema_columns(ds.payload)}
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
            ds_cols = {_norm((f.get("name") or "")) for f in _schema_columns(ds.payload)}
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
    async def generate_sql(self, dataset_query: str, requested_columns: Sequence[str] = (),
                           user: UserContext | None = None) -> SqlResponse:
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
                               explanation=["Dataset này chưa có schema được ghi nhận trong DataHub."],
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
            up_cols = [_norm((f.get("name") or "")) for f in _schema_columns(up.payload)]
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
        lines = ["SELECT", "  " + ",\n  ".join(f"{alias}.{c}" for c in selected), f"FROM {table} AS {alias}"]
        for i, (up, shared_col) in enumerate(join_tables):
            up_alias = f"u{i + 1}"
            up_table = up.name or up.urn
            lines.append(
                f"JOIN {up_table} AS {up_alias} ON {alias}.{shared_col} = {up_alias}.{shared_col}"
            )
        sql = "\n".join(lines)

        explanation: list[str] = []
        description = (payload.get("description") or "").strip()
        if description:
            explanation.append(f"Bảng {entity.display_name or entity.name}: {description}")
        else:
            explanation.append(f"Bảng {entity.display_name or entity.name}: không có mô tả trong DataHub.")
        for j in joins:
            explanation.append(f"JOIN {j.table} (cột chung '{j.column}'). {j.reason}")

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
                    f"Analytics đơn giản: gộp theo '{group_col}' và tính COUNT/SUM trên '{agg_col}' "
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
                                  business_impact=["Không tìm thấy dataset trong metadata DataHub."],
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
                + ", ".join(d.name for d in datasets[:5]) + ("..." if len(datasets) > 5 else "") + "."
            )
        if dashboards:
            business_impact.append(
                f"{len(dashboards)} dashboard có thể bị ảnh hưởng: "
                + ", ".join(d.name for d in dashboards[:5]) + ("..." if len(dashboards) > 5 else "") + "."
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
                            user: UserContext | None = None) -> QualityResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return QualityResponse(dataset=dataset_query,
                                   recommendations=["Không tìm thấy dataset trong metadata DataHub."],
                                   valid=False)
        payload = entity.payload or {}
        description = (payload.get("description") or "").strip()
        owners = _owner_names(payload)
        tags = [str(t) for t in (payload.get("tags") or [])]
        glossary = [str(g) for g in (payload.get("glossary_terms") or [])]
        domain = (payload.get("domain") or "").strip()
        schema = _schema_columns(payload)
        certified = bool(payload.get("certified"))
        upstreams, downstreams = await self._lineage_urns(entity.urn)
        has_lineage = bool(upstreams or downstreams)
        assertions = payload.get("assertions") or []
        profiling = payload.get("profiling") or []
        freshness = payload.get("freshness") or {}

        def _pct(cond: bool) -> int:
            return 100 if cond else 0

        dims: list[QualityDimension] = [
            QualityDimension(
                key="metadata_completeness", label="Metadata Completeness",
                score=_pct(bool(description)),
                status="Good" if description else "Missing",
                detail="mô tả đầy đủ" if description else "thiếu mô tả"),
            QualityDimension(
                key="documentation_quality", label="Documentation Quality",
                score=100 if len(description) >= 50 else (60 if description else 0),
                status="Excellent" if len(description) >= 50
                       else ("Good" if description else "Missing"),
                detail=f"{len(description)} ký tự mô tả"),
            QualityDimension(
                key="ownership", label="Ownership",
                score=100 if owners else 0,
                status="Good" if owners else "Missing",
                detail=", ".join(owners) if owners else "chưa gán owner"),
            QualityDimension(
                key="governance", label="Governance",
                score=int((sum([bool(tags), bool(glossary), bool(domain), certified]) / 4) * 100),
                status="Good" if (tags or glossary or domain) else "Missing",
                detail=f"{len(tags)} tag, {len(glossary)} glossary term, domain {domain or '(trống)'}"),
            QualityDimension(
                key="discoverability", label="Discoverability",
                score=int(((len(description) > 0) + bool(tags) + bool(glossary)) / 3 * 100),
                status="Good" if (description and (tags or glossary)) else "Needs Improvement",
                detail="mô tả/tag/glossary giúp tìm kiếm"),
            QualityDimension(
                key="lineage_coverage", label="Lineage Coverage",
                score=100 if has_lineage else 0,
                status="Good" if has_lineage else "Missing",
                detail=f"{len(upstreams)} upstream, {len(downstreams)} downstream"
                       if has_lineage else "không có lineage"),
            QualityDimension(
                key="data_quality", label="Data Quality",
                score=int((bool(assertions) + bool(profiling) + bool(freshness)) / 3 * 100),
                status="Good" if (assertions or profiling or freshness) else "Missing",
                detail=f"{len(assertions)} assertion, profiling {'có' if profiling else 'chưa có'}, freshness {'có' if freshness else 'chưa có'}"),
        ]

        highlights: list[str] = []
        if not description:
            highlights.append("Thiếu mô tả (Missing Description)")
        if not owners:
            highlights.append("Thiếu owner (Missing Owner)")
        if not tags:
            highlights.append("Thiếu tag (Missing Tags)")
        if not glossary:
            highlights.append("Thiếu glossary term (Missing Glossary)")
        if not domain:
            highlights.append("Thiếu domain (Missing Domain)")
        if not has_lineage:
            highlights.append("Chưa có lineage (No Lineage)")
        if profiling:
            highlights.append("Chưa có profiling (No Profiling)")
        if not assertions:
            highlights.append("Chưa có assertions (No Assertions)")

        recommendations: list[str] = []
        if not description:
            recommendations.append("Bổ sung mô tả business cho dataset này.")
        if not owners:
            recommendations.append("Gán owner để cải thiện governance.")
        if not tags:
            recommendations.append("Thêm tag để dễ tìm kiếm và phân loại.")
        if not glossary:
            recommendations.append("Gắn glossary term tương ứng.")
        if not domain:
            recommendations.append("Gán dataset vào một domain.")
        if not has_lineage:
            recommendations.append("Thiết lập lineage để theo dõi luồng dữ liệu.")
        if not assertions:
            recommendations.append("Thêm assertions để giám sát chất lượng dữ liệu.")
        if not profiling:
            recommendations.append("Bật profiling để có thống kê dữ liệu.")

        overall = int(sum(d.score for d in dims) / len(dims)) if dims else 0
        return QualityResponse(
            dataset=entity.display_name or entity.name, urn=entity.urn,
            dimensions=dims, overall_score=overall,
            highlights=highlights, recommendations=recommendations, valid=True,
        )

    # ------------------------------------------------------------------ #
    # 7. Metadata Report
    # ------------------------------------------------------------------ #
    async def metadata_report(self, dataset_query: str,
                              user: UserContext | None = None) -> ReportResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return ReportResponse(dataset=dataset_query,
                                  recommendations=["Không tìm thấy dataset trong metadata DataHub."],
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
        assessment.append(self._assess("Metadata Completeness", _pct(bool(description)) + (50 if description else 0)))
        assessment.append(self._assess("Documentation Quality",
                                       100 if len(description) >= 50 else (60 if description else 0)))
        assessment.append(self._assess("Governance Readiness",
                                       int((sum([bool(domain), bool(owners), bool(tags), bool(glossary)]) / 4) * 100)))
        assessment.append(self._assess("Discoverability",
                                       int(((len(description) > 0) + bool(tags) + bool(glossary)) / 3 * 100)))
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