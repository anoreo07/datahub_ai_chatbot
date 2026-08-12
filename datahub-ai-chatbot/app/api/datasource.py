import time

import structlog
from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_admin_user
from app.auth.models import UserContext
from config.settings import settings
from ingestion import create_datahub_source

log = structlog.get_logger()

router = APIRouter()


@router.get("/datahub/health")
async def datahub_health(
    _: UserContext = Depends(get_admin_user),
) -> dict:
    """Check connectivity to the DataHub GMS API (GraphQL)."""
    started = time.time()
    source = create_datahub_source()
    try:
        ok = await source.healthcheck()
    except Exception:  # noqa: BLE001
        log.exception("datahub_health_check_failed")
        ok = False
    finally:
        await source.close()
    latency_ms = int((time.time() - started) * 1000)
    return {
        "status": "ok" if ok else "error",
        "mode": "mock" if settings.USE_MOCK_DATAHUB else "graphql",
        "gms_url": "" if settings.USE_MOCK_DATAHUB else settings.DATAHUB_GMS_URL,
        "latency_ms": latency_ms,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
