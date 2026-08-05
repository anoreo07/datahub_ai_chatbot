import asyncio
import datetime as dt
import json
import time
from typing import Any

import structlog

from config.settings import settings
from infrastructure.redis import get_redis

log = structlog.get_logger()

_HEALTHCHECK_KEY = "healthcheck:logs"
_HEALTHCHECK_RUNNING_KEY = "healthcheck:last_running"

# In-memory fallback when Redis is unavailable (USE_IN_MEMORY_QUEUE or down).
_memory_logs: list[dict[str, Any]] = []


def _now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _now_ts() -> float:
    return time.time()


async def _redis_available() -> bool:
    if settings.USE_IN_MEMORY_QUEUE:
        return False
    try:
        client = get_redis()
        await client.connect()
        return True
    except Exception:
        return False


async def _store_log(entry: dict[str, Any]) -> None:
    if await _redis_available():
        try:
            client = get_redis()
            await client.lpush(_HEALTHCHECK_KEY, json.dumps(entry))
            await client.ltrim(_HEALTHCHECK_KEY, 0, settings.HEALTHCHECK_MAX_LOGS - 1)
            await client.expire(_HEALTHCHECK_KEY, settings.HEALTHCHECK_LOG_TTL_SECONDS)
            return
        except Exception:
            log.warning("healthcheck_log_redis_failed")
    _memory_logs.insert(0, entry)
    del _memory_logs[settings.HEALTHCHECK_MAX_LOGS:]


async def get_logs(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, settings.HEALTHCHECK_MAX_LOGS))
    if await _redis_available():
        try:
            client = get_redis()
            raw = await client.lrange(_HEALTHCHECK_KEY, 0, limit - 1)
            entries: list[dict[str, Any]] = []
            for item in raw:
                try:
                    entries.append(json.loads(item))
                except (TypeError, json.JSONDecodeError):
                    continue
            return entries
        except Exception:
            log.warning("healthcheck_log_read_redis_failed")
    return list(_memory_logs[:limit])


async def _check_service() -> dict[str, Any]:
    from database.session import async_session_factory
    from indexing.vector_store import OpenSearchVectorStore
    from llm.client import create_llm_client

    statuses: dict[str, str] = {
        "postgres": "unknown", "redis": "unknown", "opensearch": "unknown", "llm": "unknown",
    }

    try:
        async with async_session_factory() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
            statuses["postgres"] = "ok"
    except Exception:
        statuses["postgres"] = "error"

    if settings.USE_IN_MEMORY_QUEUE:
        statuses["redis"] = "ok"
    else:
        try:
            client = get_redis()
            await client.connect()
            statuses["redis"] = "ok" if await client.healthcheck() else "error"
        except Exception:
            statuses["redis"] = "error"

    try:
        store = OpenSearchVectorStore()
        statuses["opensearch"] = "ok" if await store.healthcheck() else "error"
    except Exception:
        statuses["opensearch"] = "error"

    if settings.USE_MOCK_LLM:
        statuses["llm"] = "ok"
    else:
        try:
            llm = create_llm_client()
            statuses["llm"] = "ok" if await llm.healthcheck() else "error"
        except Exception:
            statuses["llm"] = "error"

    all_ok = all(v == "ok" for v in statuses.values())
    return {"status": "ok" if all_ok else "degraded", **statuses}


async def run_healthcheck() -> dict[str, Any]:
    """Run a full service healthcheck and return the summary dict."""
    started = _now_ts()
    result = await _check_service()
    entry = {
        "timestamp": _now_iso(),
        "duration_ms": int((_now_ts() - started) * 1000),
        "status": result["status"],
        "services": {k: v for k, v in result.items() if k != "status"},
    }
    await _store_log(entry)
    log.info("healthcheck_run", status=result["status"], duration_ms=entry["duration_ms"])
    return entry


async def healthcheck_loop() -> None:
    """Periodic healthcheck every ``HEALTHCHECK_INTERVAL_SECONDS`` seconds."""
    interval = max(30, settings.HEALTHCHECK_INTERVAL_SECONDS)
    while True:
        try:
            await run_healthcheck()
        except Exception:
            log.exception("periodic_healthcheck_failed")
        await asyncio.sleep(interval)
