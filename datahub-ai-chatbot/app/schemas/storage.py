"""Storage API schemas — image metadata responses (API is metadata-only)."""

from __future__ import annotations

import datetime

from pydantic import BaseModel

from database.models import ImageRecord


class ImageItem(BaseModel):
    image_id: str
    conversation_id: str | None = None
    original_filename: str = ""
    mime_type: str = ""
    size: int = 0
    storage_path: str = ""
    thumbnail_url: str | None = None
    upload_time: datetime.datetime | None = None
    updated_time: datetime.datetime | None = None
    status: str = "uploaded"
    image_type: str | None = None
    dataset_detected: str | None = None
    is_deleted: bool = False


class ImageListResponse(BaseModel):
    items: list[ImageItem]
    total: int
    offset: int = 0
    limit: int = 50


class ImageStats(BaseModel):
    total: int = 0
    total_size: int = 0
    analyzed: int = 0
    failed: int = 0
    pending: int = 0


class ImageDetail(BaseModel):
    """Full metadata for a single image (never the OCR/vision internals)."""

    item: ImageItem
    stats: ImageStats | None = None
    conversation_url: str | None = None
    dataset_name: str | None = None


class DeleteImageRequest(BaseModel):
    hard: bool = False


def image_to_item(rec: ImageRecord) -> ImageItem:
    return ImageItem(
        image_id=rec.image_id,
        conversation_id=rec.conversation_id,
        original_filename=rec.original_filename,
        mime_type=rec.mime_type,
        size=rec.size,
        storage_path=rec.storage_path,
        thumbnail_url=f"/api/v1/storage/{rec.image_id}/thumbnail",
        upload_time=rec.upload_time,
        updated_time=rec.updated_time,
        status=rec.status,
        image_type=rec.image_type,
        dataset_detected=rec.dataset_detected,
        is_deleted=rec.is_deleted,
    )
