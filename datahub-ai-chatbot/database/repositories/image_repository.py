"""Storage Repository — DB access for image metadata records.

The repository only reads/writes ``ImageRecord`` metadata. Binary payloads are
managed by the Image Storage Service on disk; this layer never touches files.
"""

from __future__ import annotations

import datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ImageRecord, ImageStatus


class StorageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: ImageRecord) -> ImageRecord:
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get(self, image_id: str, include_deleted: bool = False) -> ImageRecord | None:
        stmt = select(ImageRecord).where(ImageRecord.image_id == image_id)
        if not include_deleted:
            stmt = stmt.where(ImageRecord.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_content_hash(self, content_hash: str) -> ImageRecord | None:
        result = await self._session.execute(
            select(ImageRecord).where(ImageRecord.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def list_by_conversation(
        self, user_id: str, conversation_id: str, include_deleted: bool = False
    ) -> list[ImageRecord]:
        stmt = (
            select(ImageRecord)
            .where(
                ImageRecord.user_id == user_id,
                ImageRecord.conversation_id == conversation_id,
            )
            .order_by(ImageRecord.upload_time.asc())
        )
        if not include_deleted:
            stmt = stmt.where(ImageRecord.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def _base_list_stmt(self, user_id: str):
        return select(ImageRecord).where(
            ImageRecord.user_id == user_id,
            ImageRecord.is_deleted.is_(False),
        )

    async def list(
        self,
        user_id: str,
        *,
        search: str | None = None,
        status: str | None = None,
        image_type: str | None = None,
        conversation_id: str | None = None,
        sort_by: str = "upload_time",
        sort_desc: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ImageRecord], int]:
        stmt = self._base_list_stmt(user_id)
        filters = []
        if search:
            like = f"%{search}%"
            filters.append(
                or_(
                    ImageRecord.original_filename.ilike(like),
                    ImageRecord.dataset_detected.ilike(like),
                )
            )
        if status:
            filters.append(ImageRecord.status == status)
        if image_type and image_type != "all":
            filters.append(ImageRecord.image_type == image_type)
        if conversation_id:
            filters.append(ImageRecord.conversation_id == conversation_id)
        for f in filters:
            stmt = stmt.where(f)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        col = {
            "upload_time": ImageRecord.upload_time,
            "size": ImageRecord.size,
            "status": ImageRecord.status,
            "updated_time": ImageRecord.updated_time,
        }.get(sort_by, ImageRecord.upload_time)
        stmt = stmt.order_by(col.desc() if sort_desc else col.asc())
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def stats(self, user_id: str) -> dict:
        """Aggregate stats: total count, total size, and status breakdowns."""
        stmt = self._base_list_stmt(user_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        total_size = sum(r.size for r in rows)
        counts: dict[str, int] = {
            ImageStatus.UPLOADED.value: 0,
            ImageStatus.ANALYZING.value: 0,
            ImageStatus.ANALYZED.value: 0,
            ImageStatus.FAILED.value: 0,
        }
        for r in rows:
            counts[r.status] = counts.get(r.status, 0) + 1
        return {
            "total": len(rows),
            "total_size": total_size,
            "analyzed": counts[ImageStatus.ANALYZED.value],
            "failed": counts[ImageStatus.FAILED.value],
            "pending": counts[ImageStatus.UPLOADED.value] + counts[ImageStatus.ANALYZING.value],
        }

    async def update_fields(self, image_id: str, **values) -> ImageRecord | None:
        values["updated_time"] = datetime.datetime.now(datetime.timezone.utc)
        await self._session.execute(
            update(ImageRecord).where(ImageRecord.image_id == image_id).values(**values)
        )
        await self._session.commit()
        return await self.get(image_id)

    async def soft_delete(self, image_id: str) -> ImageRecord | None:
        return await self.update_fields(
            image_id,
            is_deleted=True,
            deleted_at=datetime.datetime.now(datetime.timezone.utc),
        )

    async def restore(self, image_id: str) -> ImageRecord | None:
        record = await self.get(image_id, include_deleted=True)
        if record is None:
            return None
        return await self.update_fields(
            image_id, is_deleted=False, deleted_at=None
        )

    async def hard_delete(self, image_id: str) -> bool:
        result = await self._session.execute(
            select(ImageRecord).where(ImageRecord.image_id == image_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        await self._session.delete(record)
        await self._session.commit()
        return True