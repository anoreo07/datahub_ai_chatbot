"""API endpoint for document ingestion."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.auth.models import UserContext
from app.dependencies import get_db_session
from ingestion.document_ingestion import DocumentIngestionService

router = APIRouter(tags=["documents"])


@router.post("/api/v1/documents/import")
async def import_document(
    url: str = "",
    title: str = "",
    session: AsyncSession = Depends(get_db_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward")),
) -> dict:
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    service = DocumentIngestionService(session)
    try:
        result = await service.ingest_from_url(url, title=title)
        if result.success:
            return {"success": True, "urn": result.entity_urn, "chunks": result.chunks_count, "title": result.title}
        raise HTTPException(status_code=422, detail=result.error)
    finally:
        await service.close()
