import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_auth_service, require_role
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.repositories.entity_repository import EntityRepository
from database.session import get_session
from retrieval.hybrid_search import HybridSearch, SearchResult

router = APIRouter()


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("đ", "d").replace("Đ", "d")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


class SearchItem(BaseModel):
    urn: str = ""
    entity_type: str = ""
    name: str = ""
    score: float = 0.0
    snippet: str = ""
    datahub_url: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchItem] = []
    total: int = 0


class StatsResponse(BaseModel):
    dataset: int = 0
    dashboard: int = 0
    glossary_term: int = 0
    document: int = 0
    total: int = 0


def _matches_owner(result: SearchResult, owner: str) -> bool:
    target = _norm(owner)
    if not target:
        return True
    for o in (result.payload or {}).get("owners") or []:
        if isinstance(o, dict) and target in _norm(str(o.get("name") or "")):
            return True
    return False


def _matches_tag(result: SearchResult, tag: str) -> bool:
    target = _norm(tag)
    if not target:
        return True
    for t in (result.payload or {}).get("tags") or []:
        if target in _norm(str(t)):
            return True
    return False


def _matches_column(result: SearchResult, column: str) -> bool:
    target = _norm(column)
    if not target:
        return True
    for f in (result.payload or {}).get("schema_fields") or []:
        if isinstance(f, dict) and _norm(str(f.get("name") or "")) == target:
            return True
    return False


@router.get("/stats")
async def stats(
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
) -> StatsResponse:
    repo = EntityRepository(session)
    types = ("dataset", "dashboard", "glossary_term", "document")
    counts = {t: await repo.count_by_type(t) for t in types}
    return StatsResponse(
        dataset=counts["dataset"],
        dashboard=counts["dashboard"],
        glossary_term=counts["glossary_term"],
        document=counts["document"],
        total=sum(counts.values()),
    )


@router.get("")
async def search(
    q: str = Query(""),
    entity_type: str | None = Query(None),
    domain: str | None = Query(None),
    platform: str | None = Query(None),
    owner: str | None = Query(None),
    tag: str | None = Query(None),
    column: str | None = Query(None),
    limit: int = Query(2000),
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> SearchResponse:
    searcher = HybridSearch(session)
    filters = {}
    if entity_type:
        filters["entity_type"] = entity_type
    if domain:
        filters["domain"] = domain
    if platform:
        filters["platform"] = platform

    # Domain RBAC: a user explicitly filtering by a domain outside their roles
    # gets no results at all (no counts, names or metadata from unauthorized
    # domains), rather than a misleading empty/partial dataset.
    if domain and not await auth_service.can_access_domain(current_user, domain):
        return SearchResponse(query=q, results=[], total=0)

    results = await searcher.search(q, top_k=limit, **filters)
    accessible = await auth_service.filter_accessible_urns(
        current_user, [r.urn for r in results]
    )
    results = [r for r in results if r.urn in accessible]
    results = [r for r in results if _matches_owner(r, owner or "")
               and _matches_tag(r, tag or "") and _matches_column(r, column or "")]
    items = [
        SearchItem(
            urn=r.urn, entity_type=r.entity_type, name=r.name,
            score=r.score, snippet=r.snippet[:200], datahub_url=r.datahub_url,
        )
        for r in results
    ]
    return SearchResponse(results=items, total=len(items))


class SchemaFieldItem(BaseModel):
    field_path: str = ""
    name: str = ""
    type: str = ""
    description: str | None = None
    nullable: bool = True
    is_primary_key: bool = False


class LineageNodeItem(BaseModel):
    urn: str
    name: str
    entity_type: str | None = None
    platform: str | None = None


class EntityDetailResponse(BaseModel):
    urn: str
    entity_type: str
    name: str
    display_name: str | None = None
    description: str | None = None
    platform: str | None = None
    environment: str | None = None
    domain: str | None = None
    datahub_url: str | None = None
    schema_fields: list[SchemaFieldItem] = []
    upstreams: list[LineageNodeItem] = []
    downstreams: list[LineageNodeItem] = []


def _name_from_urn(r: str) -> str:
    if not isinstance(r, str):
        return str(r)
    if "PROD" in r:
        inner = r.split("PROD")[0].rsplit("(", 1)[-1].strip().strip(",")
    else:
        inner = r
    if "," in inner:
        parts = inner.split(",")
        if len(parts) >= 2:
            return parts[1]
    return inner.split(":")[-1]


@router.get("/entity", response_model=EntityDetailResponse)
async def get_entity_detail(
    urn: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> EntityDetailResponse:
    repo = EntityRepository(session)
    entity = await repo.get_by_urn(urn)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if not await auth_service.can_access_domain(current_user, entity.domain):
        raise HTTPException(status_code=403, detail="Permission denied to access this domain")

    payload = entity.payload or {}

    # Extract schema fields
    schema_fields = []
    for f in (payload.get("schema_fields") or []):
        schema_fields.append(
            SchemaFieldItem(
                field_path=f.get("field_path") or f.get("fieldPath") or "",
                name=f.get("name") or "",
                type=f.get("type") or "",
                description=f.get("description"),
                nullable=f.get("nullable", True),
                is_primary_key=f.get("is_primary_key") or f.get("isPartOfKey", False),
            )
        )

    # Extract lineage URNs
    upstreams_raw = payload.get("upstreams") or []
    downstreams_raw = payload.get("downstreams") or []

    # Query database for all related lineage entities to resolve their names/platforms
    all_lineage_urns = list(set(upstreams_raw + downstreams_raw))
    resolved_entities = {}
    if all_lineage_urns:
        entities_list = await repo.list_by_urns(all_lineage_urns)
        for ent in entities_list:
            resolved_entities[ent.urn] = ent

    # Map related entities
    def map_lineage_node(urn_str: str) -> LineageNodeItem:
        ent = resolved_entities.get(urn_str)
        if ent:
            return LineageNodeItem(
                urn=ent.urn,
                name=ent.display_name or ent.name,
                entity_type=ent.entity_type,
                platform=ent.platform,
            )
        else:
            # Fallback when entity is not in local DB
            inferred_type = "dataset"
            if ":dashboard:" in urn_str or ":dashboard(" in urn_str:
                inferred_type = "dashboard"
            elif ":glossaryTerm:" in urn_str:
                inferred_type = "glossary_term"
            elif ":document:" in urn_str:
                inferred_type = "document"

            inferred_platform = None
            if "dataPlatform:" in urn_str:
                inferred_platform = urn_str.split("dataPlatform:")[-1].split(",")[0]

            return LineageNodeItem(
                urn=urn_str,
                name=_name_from_urn(urn_str),
                entity_type=inferred_type,
                platform=inferred_platform,
            )

    upstreams = [map_lineage_node(u) for u in upstreams_raw]
    downstreams = [map_lineage_node(d) for d in downstreams_raw]

    return EntityDetailResponse(
        urn=entity.urn,
        entity_type=entity.entity_type,
        name=entity.name,
        display_name=entity.display_name,
        description=entity.description,
        platform=entity.platform,
        environment=entity.environment,
        domain=entity.domain,
        datahub_url=entity.datahub_url,
        schema_fields=schema_fields,
        upstreams=upstreams,
        downstreams=downstreams,
    )
