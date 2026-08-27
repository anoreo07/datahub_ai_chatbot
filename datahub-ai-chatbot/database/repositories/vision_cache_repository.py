"""Vision Cache Repository — DB access for cached vision analysis results."""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import VisionCacheRecord


class VisionCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def new_cache_id(self) -> str:
        return uuid.uuid4().hex[:16]

    async def get_by_content_hash(self, content_hash: str) -> VisionCacheRecord | None:
        result = await self._session.execute(
            select(VisionCacheRecord).where(
                VisionCacheRecord.content_hash == content_hash
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        content_hash: str,
        *,
        model_id: str,
        vision_result: dict | None,
        image_context: dict | None,
    ) -> VisionCacheRecord:
        existing = await self.get_by_content_hash(content_hash)
        if existing is not None:
            await self._session.execute(
                update(VisionCacheRecord)
                .where(VisionCacheRecord.id == existing.id)
                .values(
                    model_id=model_id,
                    vision_result=vision_result,
                    image_context=image_context,
                    updated_at=datetime.datetime.now(datetime.UTC),
                )
            )
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        record = VisionCacheRecord(
            cache_id=self.new_cache_id(),
            content_hash=content_hash,
            model_id=model_id,
            vision_result=vision_result,
            image_context=image_context,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record
