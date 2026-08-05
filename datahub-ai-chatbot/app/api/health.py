from fastapi import APIRouter, Query

from app.services.health_service import get_logs, run_healthcheck

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    entry = await run_healthcheck()
    return {"status": entry["status"], **entry["services"]}


@router.get("/ready/logs")
async def ready_logs(limit: int = Query(default=20, ge=1, le=200)) -> dict:
    logs = await get_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}
