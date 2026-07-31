import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from config.settings import settings

log = structlog.get_logger()


class RedisClient:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None
        self._url = settings.REDIS_URL

    async def connect(self) -> None:
        if self._client is not None:
            return
        try:
            self._client = aioredis.from_url(self._url, decode_responses=True)
            await self._client.ping()
            log.info("redis_connected")
        except Exception:
            log.warning("redis_connection_failed")
            self._client = None

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> str | None:
        if not self._client:
            return None
        try:
            val = await self._client.get(key)
            return str(val) if val is not None else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._client:
            return
        try:
            await self._client.set(key, json.dumps(value) if not isinstance(value, str) else value, ex=ttl)
        except Exception:
            pass

    async def incr(self, key: str) -> int:
        if not self._client:
            return 0
        try:
            return await self._client.incr(key)
        except Exception:
            return 0

    async def expire(self, key: str, ttl: int) -> None:
        if not self._client:
            return
        try:
            await self._client.expire(key, ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        if not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception:
            pass

    async def enqueue(self, queue_name: str, value: str) -> None:
        if not self._client:
            return
        try:
            await self._client.lpush(queue_name, value)
        except Exception:
            pass

    async def dequeue(self, queue_name: str, timeout: int = 5) -> str | None:
        if not self._client:
            return None
        try:
            result = await self._client.brpop(queue_name, timeout=timeout)
            if result:
                val = result[1]
                return str(val) if val is not None else None
            return None
        except Exception:
            return None

    async def healthcheck(self) -> bool:
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False


_redis_client: RedisClient | None = None


def get_redis() -> RedisClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
