import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SyncCheckpoint


class SyncRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_checkpoint(self, source: str, entity_type: str) -> SyncCheckpoint | None:
        stmt = select(SyncCheckpoint).where(
            SyncCheckpoint.source == source,
            SyncCheckpoint.entity_type == entity_type,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_success(
        self, source: str, entity_type: str, cursor: str | None = None, checkpoint_metadata: dict | None = None
    ) -> SyncCheckpoint:
        existing = await self.get_checkpoint(source, entity_type)
        now = datetime.datetime.now(datetime.UTC)
        if existing:
            existing.cursor = cursor
            existing.last_success_at = now
            existing.last_failure_at = None
            existing.status = "completed"
            existing.checkpoint_metadata = checkpoint_metadata
            existing.updated_at = now
        else:
            existing = SyncCheckpoint(
                source=source,
                entity_type=entity_type,
                cursor=cursor,
                last_success_at=now,
                status="completed",
                checkpoint_metadata=checkpoint_metadata,
            )
            self._session.add(existing)
        await self._session.commit()
        return existing

    async def save_failure(
        self, source: str, entity_type: str, error: str, cursor: str | None = None
    ) -> SyncCheckpoint:
        existing = await self.get_checkpoint(source, entity_type)
        now = datetime.datetime.now(datetime.UTC)
        if existing:
            existing.status = "failed"
            existing.last_failure_at = now
            existing.cursor = cursor
            existing.checkpoint_metadata = {"error": error}
            existing.updated_at = now
        else:
            existing = SyncCheckpoint(
                source=source,
                entity_type=entity_type,
                cursor=cursor,
                last_failure_at=now,
                status="failed",
                checkpoint_metadata={"error": error},
            )
            self._session.add(existing)
        await self._session.commit()
        return existing
