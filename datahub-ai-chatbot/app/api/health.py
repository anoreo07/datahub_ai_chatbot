from fastapi import APIRouter

from config.settings import settings
from database.session import async_session_factory
from indexing.vector_store import OpenSearchVectorStore
from infrastructure.redis import get_redis
from llm.client import create_llm_client

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    statuses: dict[str, str] = {"postgres": "unknown", "redis": "unknown", "opensearch": "unknown", "llm": "unknown"}

    try:
        async with async_session_factory() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            statuses["postgres"] = "ok"
    except Exception:
        statuses["postgres"] = "error"

    if settings.USE_IN_MEMORY_QUEUE:
        statuses["redis"] = "ok"
    else:
        try:
            redis_client = get_redis()
            await redis_client.connect()
            if await redis_client.healthcheck():
                statuses["redis"] = "ok"
            else:
                statuses["redis"] = "error"
        except Exception:
            statuses["redis"] = "error"

    try:
        store = OpenSearchVectorStore()
        if await store.healthcheck():
            statuses["opensearch"] = "ok"
        else:
            statuses["opensearch"] = "error"
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
