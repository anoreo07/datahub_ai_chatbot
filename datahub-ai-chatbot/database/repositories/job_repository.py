import datetime
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Job, JobStatus, Notification


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        type: str,
        title: str,
        message: str,
        user_id: str | None = None,
        entity_urn: str | None = None,
        job_metadata: dict | None = None,
    ) -> Job:
        job = Job(
            type=type,
            title=title,
            message=message,
            user_id=user_id,
            entity_urn=entity_urn,
            job_metadata=job_metadata or {},
        )
        self._session.add(job)
        await self._session.commit()
        return job

    async def mark_running(self, job_id: int) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.datetime.now(datetime.UTC)
            await self._session.commit()
        return job

    async def mark_success(self, job_id: int) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = JobStatus.SUCCESS
            job.completed_at = datetime.datetime.now(datetime.UTC)
            await self._session.commit()
        return job

    async def mark_failed(self, job_id: int, error: str) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = JobStatus.FAILED
            job.error = error
            job.completed_at = datetime.datetime.now(datetime.UTC)
            await self._session.commit()
        return job

    async def get_active_by_user(self, user_id: str) -> Sequence[Job]:
        stmt = select(Job).where(
            Job.user_id == user_id, Job.status.in_([JobStatus.RUNNING, JobStatus.PENDING])
        ).order_by(Job.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(self, type: str) -> Sequence[Job]:
        stmt = select(Job).where(Job.type == type).order_by(Job.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_active_by_user(self, user_id: str) -> int:
        stmt = select(func.count(Job.id)).where(
            Job.user_id == user_id, Job.status.in_([JobStatus.RUNNING, JobStatus.PENDING])
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        job_id: int,
        user_id: str,
        type: str,
        title: str,
        message: str,
        status: str = JobStatus.PENDING,
    ) -> Notification:
        notification = Notification(
            job_id=job_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            status=status,
        )
        self._session.add(notification)
        await self._session.commit()
        return notification

    async def get_unread_by_user(self, user_id: str) -> Sequence[Notification]:
        stmt = select(Notification).where(
            Notification.user_id == user_id, Notification.is_read == False
        ).order_by(Notification.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_user(self, user_id: str) -> Sequence[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(
            Notification.created_at.desc()
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_read(self, notification_id: int) -> Notification | None:
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await self._session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            notification.read_at = datetime.datetime.now(datetime.UTC)
            await self._session.commit()
        return notification

    async def mark_all_read(self, user_id: str) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id, Notification.is_read == False
            )
            .values(is_read=True, read_at=datetime.datetime.now(datetime.UTC))
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount

    async def get_by_job(self, job_id: int) -> Sequence[Notification]:
        stmt = select(Notification).where(Notification.job_id == job_id).order_by(
            Notification.created_at.desc()
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active_for_user(self, user_id: str) -> Sequence[Notification]:
        """Get active (RUNNING) notifications for a user."""
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.status == JobStatus.RUNNING,
            Notification.is_read == False,
        ).order_by(Notification.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()
