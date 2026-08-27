import datetime
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import JobStatus, Notification


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
