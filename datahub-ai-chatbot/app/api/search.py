from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_auth_service, require_role
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.session import get_session
from retrieval.hybrid_search import HybridSearch

router = APIRouter()


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


@router.get("")
async def search(
    q: str = Query(""),
    entity_type: str | None = Query(None),
    domain: str | None = Query(None),
    platform: str | None = Query(None),
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
    items = [
        SearchItem(
            urn=r.urn, entity_type=r.entity_type, name=r.name,
            score=r.score, snippet=r.snippet[:200], datahub_url=r.datahub_url,
        )
        for r in results
    ]
    return SearchResponse(results=items, total=len(items))
