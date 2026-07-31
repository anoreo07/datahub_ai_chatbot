import datetime
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import IndexJob


class IndexJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entity_urn: str) -> IndexJob:
        job = IndexJob(entity_urn=entity_urn, status="pending")
        self._session.add(job)
        await self._session.commit()
        return job

    async def mark_running(self, job_id: int) -> IndexJob | None:
        stmt = select(IndexJob).where(IndexJob.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = "processing"
            job.started_at = datetime.datetime.now(datetime.UTC)
            job.attempts = (job.attempts or 0) + 1
            await self._session.commit()
        return job

    async def mark_completed(self, job_id: int) -> IndexJob | None:
        stmt = select(IndexJob).where(IndexJob.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = "completed"
            job.completed_at = datetime.datetime.now(datetime.UTC)
            await self._session.commit()
        return job

    async def mark_failed(self, job_id: int, error: str) -> IndexJob | None:
        stmt = select(IndexJob).where(IndexJob.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error = error
            await self._session.commit()
        return job

    async def get_pending(self, limit: int = 20) -> Sequence[IndexJob]:
        stmt = select(IndexJob).where(IndexJob.status == "pending").order_by(IndexJob.created_at).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_pending(self) -> int:
        stmt = select(func.count(IndexJob.id)).where(IndexJob.status == "pending")
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_by_entity_urn(self, entity_urn: str) -> Sequence[IndexJob]:
        stmt = select(IndexJob).where(IndexJob.entity_urn == entity_urn).order_by(IndexJob.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()
