from typing import Any


class DistributedLock:
    def __init__(self, redis_url: str = "redis://localhost:6380/0", ttl_seconds: int = 1800) -> None:
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._client: Any = None
        self._lock_key = "sync:lock"

    async def acquire(self, lock_id: str = "default") -> bool:
        import redis.asyncio as aioredis

        if self._client is None:
            self._client = await aioredis.from_url(self._redis_url)
        result = await self._client.setnx(f"{self._lock_key}:{lock_id}", "locked")
        if result:
            await self._client.expire(f"{self._lock_key}:{lock_id}", self._ttl)
            return True
        return False

    async def release(self, lock_id: str = "default") -> None:
        if self._client:
            await self._client.delete(f"{self._lock_key}:{lock_id}")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class InMemoryLock:
    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl = ttl_seconds
        self._locks: dict[str, bool] = {}

    async def acquire(self, lock_id: str = "default") -> bool:
        if self._locks.get(lock_id):
            return False
        self._locks[lock_id] = True
        return True

    async def release(self, lock_id: str = "default") -> None:
        self._locks.pop(lock_id, None)

    async def close(self) -> None:
        self._locks.clear()
