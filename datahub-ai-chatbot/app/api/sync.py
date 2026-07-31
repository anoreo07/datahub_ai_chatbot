from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_role
from app.auth.models import UserContext
from database.session import get_session
from ingestion.sync import SyncOrchestrator

router = APIRouter()


class SyncFullResponse(BaseModel):
    status: str = "ok"
    results: dict = {}


class SyncEntityRequest(BaseModel):
    urn: str


class SyncEntityResponse(BaseModel):
    status: str
    changed: bool = False


@router.post("/full")
async def trigger_full_sync(
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin")),
) -> SyncFullResponse:
    orchestrator = SyncOrchestrator(session)
    results = await orchestrator.run_full_sync()
    return SyncFullResponse(status="ok", results=results)


@router.post("/entity")
async def sync_entity(
    request: SyncEntityRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward")),
) -> SyncEntityResponse:
    orchestrator = SyncOrchestrator(session)
    changed = await orchestrator.sync_entity_by_urn(request.urn)
    return SyncEntityResponse(status="ok", changed=changed)
