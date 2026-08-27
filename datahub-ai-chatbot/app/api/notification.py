from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.models import UserContext
from database.models import Job, JobStatus
from database.repositories.job_repository import JobRepository
from database.repositories.notification_repository import NotificationRepository
from database.session import get_session

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


async def _get_repos(
    session: AsyncSession,
) -> tuple[JobRepository, NotificationRepository]:
    return JobRepository(session), NotificationRepository(session)


@router.get("")
async def list_notifications(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List notifications for the current user."""
    repo = NotificationRepository(session)
    notifes = await repo.get_by_user(user.user_id)
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "status": n.status,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "metadata": n.metadata,
        }
        for n in notifes
    ]


@router.get("/unread-count")
async def unread_count(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> int:
    """Get unread notification count for the current user."""
    repo = NotificationRepository(session)
    return await repo.mark_read.count if False else await repo.get_unread_by_user(
        user.user_id
    )


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark a single notification as read."""
    repo = NotificationRepository(session)
    notif = await repo.mark_read(notification_id)
    if not notif:
        return JSONResponse(status_code=404, content={"detail": "Notification not found"})
    return {
        "id": notif.id,
        "is_read": notif.is_read,
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


@router.post("/mark-all-read")
async def mark_all_read(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark all notifications as read for the current user."""
    repo = NotificationRepository(session)
    count = await repo.mark_all_read(user.user_id)
    return {"marked": count, "user_id": user.user_id}


@router.get("/jobs/active")
async def list_active_jobs(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List active (running/pending) jobs for the current user."""
    repo = JobRepository(session)
    jobs = await repo.get_active_by_user(user.user_id)
    return [
        {
            "id": j.id,
            "type": j.type,
            "status": j.status,
            "title": j.title,
            "message": j.message,
            "progress": j.progress,
            "error": j.error,
            "entity_urn": j.entity_urn,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "metadata": j.metadata,
        }
        for j in jobs
    ]


@router.get("/jobs/pending")
async def list_pending_jobs(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List pending jobs for the current user."""
    repo = JobRepository(session)
    stmt = select(Job).where(Job.user_id == user.user_id, Job.status == JobStatus.PENDING)
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "type": j.type,
            "status": j.status,
            "title": j.title,
            "message": j.message,
            "progress": j.progress,
            "entity_urn": j.entity_urn,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "metadata": j.metadata,
        }
        for j in jobs
    ]
