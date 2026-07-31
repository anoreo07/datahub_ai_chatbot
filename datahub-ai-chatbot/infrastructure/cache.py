"""Caching layer for search results."""
import json

import structlog

from config.settings import settings
from infrastructure.redis import get_redis

log = structlog.get_logger()


class SearchCache:
    async def get(self, key: str) -> list[dict] | None:
        if not settings.CACHE_ENABLED:
            return None
        redis = get_redis()
        await redis.connect()
        cached = await redis.get(f"search:{key}")
        if cached:
            from app.api.metrics import cache_hits_total
            cache_hits_total.labels(result="hit").inc()
            return json.loads(cached)
        from app.api.metrics import cache_hits_total
        cache_hits_total.labels(result="miss").inc()
        return None

    async def set(self, key: str, results: list[dict]) -> None:
        if not settings.CACHE_ENABLED:
            return
        redis = get_redis()
        await redis.connect()
        await redis.set(f"search:{key}", results, ttl=settings.CACHE_DEFAULT_TTL_SECONDS)

    async def invalidate(self, pattern: str = "") -> None:
        if not settings.CACHE_ENABLED:
            return
        redis = get_redis()
        await redis.connect()
        if pattern:
            await redis.delete(f"search:{pattern}")
        else:
            await redis.delete("search:*")
