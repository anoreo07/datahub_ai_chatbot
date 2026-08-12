from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_auth_service, get_current_user, require_role
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.repositories.entity_repository import EntityRepository
from database.session import get_session

router = APIRouter()


class GlossaryTermItem(BaseModel):
    urn: str = ""
    name: str = ""
    description: str | None = None
    domain: str | None = None


class GlossaryResponse(BaseModel):
    terms: list[GlossaryTermItem] = []


@router.get("/terms")
async def list_terms(
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> GlossaryResponse:
    repo = EntityRepository(session)
    entities = await repo.list_by_type("glossary_term")
    entities = await auth_service.filter_entities_by_domain(current_user, entities)
    terms = [
        GlossaryTermItem(urn=e.urn, name=e.display_name or e.name, description=e.description, domain=e.domain)
        for e in entities
    ]
    return GlossaryResponse(terms=terms)


@router.get("/terms/{urn}")
async def get_term(
    urn: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> GlossaryTermItem | None:
    repo = EntityRepository(session)
    entity = await repo.get_by_urn(urn)
    if not entity:
        return None
    if not await auth_service.can_access_domain(current_user, entity.domain):
        return None
    return GlossaryTermItem(urn=entity.urn, name=entity.display_name or entity.name,
                            description=entity.description, domain=entity.domain)
