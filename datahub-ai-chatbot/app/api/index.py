from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_role
from app.auth.models import UserContext
from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from database.session import get_session
from indexing.pipeline import IndexingPipeline
from indexing.vector_store import OpenSearchVectorStore

router = APIRouter()


class IndexRebuildResponse(BaseModel):
    status: str = "ok"
    jobs_created: int = 0


@router.post("/rebuild")
async def rebuild_index(
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin")),
) -> IndexRebuildResponse:
    vector_store = OpenSearchVectorStore()
    await vector_store.ensure_index()

    entity_repo = EntityRepository(session)
    index_repo = IndexJobRepository(session)
    all_entities: list = []
    for etype in ["dataset", "dashboard", "glossary_term", "document"]:
        all_entities.extend(await entity_repo.list_by_type(etype))

    seen_urns = set()
    jobs_created = 0
    for entity in all_entities:
        if entity.urn in seen_urns:
            continue
        seen_urns.add(entity.urn)
        await index_repo.create(entity.urn)
        jobs_created += 1

    pipeline = IndexingPipeline(session)
    await pipeline.process_pending_jobs(max_jobs=100)

    return IndexRebuildResponse(status="ok", jobs_created=jobs_created)
