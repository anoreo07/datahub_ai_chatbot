import unicodedata

from fastapi import APIRouter, Depends, Query
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
    limit: int = Query(10),
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