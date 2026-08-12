"""Storage API — list, preview, download, rename, delete, restore and re-run
analysis for stored images. The API exposes metadata only; OCR / vision / entity
internals are never surfaced here.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.models import UserContext
from app.schemas.storage import (
    DeleteImageRequest,
    ImageDetail,
    ImageListResponse,
    ImageStats,
    image_to_item,
)
from app.services.image_storage import ImageStorageService
from app.services.image_upload import ImageUploadService
from database.repositories.image_repository import StorageRepository
from database.session import get_session

router = APIRouter()


def _repos(
    session: AsyncSession,
) -> tuple[StorageRepository, ImageUploadService, ImageStorageService]:
    return StorageRepository(session), ImageUploadService(session), ImageStorageService()


def _404(image_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Image not found: {image_id}")


@router.get("", response_model=ImageListResponse)
async def list_images(
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    search: str | None = None,
    status: str | None = None,
    image_type: str | None = None,
    conversation_id: str | None = None,
    sort_by: str = Query("upload_time"),
    sort_desc: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ImageListResponse:
    repo, _, _ = _repos(session)
    rows, total = await repo.list(
        current_user.user_id,
        search=search, status=status, image_type=image_type,
        conversation_id=conversation_id, sort_by=sort_by,
        sort_desc=sort_desc, limit=limit, offset=offset,
    )
    return ImageListResponse(
        items=[image_to_item(r) for r in rows],
        total=total, offset=offset, limit=limit,
    )


@router.get("/stats", response_model=ImageStats)
async def image_stats(
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ImageStats:
    repo, _, _ = _repos(session)
    return ImageStats(**await repo.stats(current_user.user_id))


@router.get("/{image_id}", response_model=ImageDetail)
async def get_image(
    image_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ImageDetail:
    repo, _, _ = _repos(session)
    rec = await repo.get(image_id)
    if rec is None or rec.user_id != current_user.user_id:
        raise _404(image_id)
    return ImageDetail(
        item=image_to_item(rec),
        conversation_url=f"/api/v1/conversations/{rec.conversation_id}"
        if rec.conversation_id else None,
        dataset_name=rec.dataset_detected,
    )


@router.get("/{image_id}/thumbnail")
async def thumbnail(
    image_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    repo, _, storage = _repos(session)
    rec = await repo.get(image_id)
    if rec is None or rec.user_id != current_user.user_id:
        raise _404(image_id)
    mime = rec.mime_type
    try:
        if rec.thumbnail_path:
            data = storage.read_bytes(rec.thumbnail_path)
            mime = "image/jpeg"
        else:
            data = storage.read_bytes(rec.storage_path)
    except Exception:  # noqa: BLE001
        raise _404(image_id)
    headers = {"Cache-Control": "public, max-age=3600"}
    return Response(content=data, media_type=mime, headers=headers)


@router.get("/{image_id}/download")
async def download(
    image_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    repo, _, storage = _repos(session)
    rec = await repo.get(image_id)
    if rec is None or rec.user_id != current_user.user_id:
        raise _404(image_id)
    try:
        data = storage.read_bytes(rec.storage_path)
    except Exception:  # noqa: BLE001
        raise _404(image_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=rec.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{rec.original_filename}"'
        },
    )


@router.post("/{image_id}/reanalyze", response_model=ImageDetail)
async def reanalyze(
    image_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ImageDetail:
    upload = ImageUploadService(session)
    rec = await upload.rerun_analysis(image_id, current_user.user_id)
    if rec is None:
        raise _404(image_id)
    return ImageDetail(item=image_to_item(rec), dataset_name=rec.dataset_detected)


@router.delete("/{image_id}", response_model=ImageDetail)
async def delete_image(
    image_id: str,
    body: DeleteImageRequest = Depends(lambda: DeleteImageRequest()),
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ImageDetail:
    repo, _, storage = _repos(session)
    rec = await repo.get(image_id)
    if rec is None or rec.user_id != current_user.user_id:
        raise _404(image_id)
    if body.hard:
        repo_ok = await repo.hard_delete(image_id)
        if repo_ok:
            storage.purge_directory(current_user.user_id, image_id)
        rec = await repo.get(image_id, include_deleted=True) or rec
    else:
        if rec.storage_path:
            storage.move_to_trash([rec.storage_path])
        rec = await repo.soft_delete(image_id) or rec
    return ImageDetail(item=image_to_item(rec))


@router.post("/{image_id}/restore", response_model=ImageDetail)
async def restore_image(
    image_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ImageDetail:
    repo, _, _ = _repos(session)
    rec = await repo.get(image_id, include_deleted=True)
    if rec is None or rec.user_id != current_user.user_id:
        raise _404(image_id)
    rec = await repo.restore(image_id) or rec
    return ImageDetail(item=image_to_item(rec))
