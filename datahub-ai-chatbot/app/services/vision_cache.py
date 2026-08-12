"""Vision Cache — reuse past vision analysis results for identical images.

Keyed by a SHA-256 content hash of the raw image bytes, so re-uploading the same
image (or reopening a conversation) never re-calls the vision model.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.vision_cache_repository import VisionCacheRepository

log = structlog.get_logger()


class VisionCache:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = VisionCacheRepository(session)

    async def get(self, content_hash: str) -> dict[str, Any] | None:
        record = await self._repo.get_by_content_hash(content_hash)
        if record is None:
            return None
        return {
            "cache_id": record.cache_id,
            "vision_result": record.vision_result,
            "image_context": record.image_context,
            "model_id": record.model_id,
        }

    async def put(
        self,
        content_hash: str,
        *,
        model_id: str,
        vision_result: dict[str, Any] | None,
        image_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        record = await self._repo.upsert(
            content_hash,
            model_id=model_id,
            vision_result=vision_result,
            image_context=image_context,
        )
        return {
            "cache_id": record.cache_id,
            "vision_result": record.vision_result,
            "image_context": record.image_context,
            "model_id": record.model_id,
        }
