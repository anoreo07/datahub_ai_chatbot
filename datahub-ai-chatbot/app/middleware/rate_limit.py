import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from config.settings import settings
from infrastructure.redis import get_redis


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def is_allowed(self, key: str) -> bool:
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        super().__init__(max_requests, window_seconds)
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._window_seconds
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if t > window_start]
        if len(bucket) >= self._max_requests:
            return False
        bucket.append(now)
        return True


class RedisRateLimiter(RateLimiter):
    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        super().__init__(max_requests, window_seconds)
        self._redis: object | None = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = get_redis()
            await self._redis.connect()
        return self._redis

    async def is_allowed(self, key: str) -> bool:
        redis = await self._get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self._window_seconds)
        return count <= self._max_requests


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)
        if settings.USE_IN_MEMORY_DATABASE:
            self._limiter: RateLimiter = InMemoryRateLimiter(
                max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            )
        else:
            self._limiter = RedisRateLimiter(
                max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        route_key = f"rate_limit:{client_ip}:{request.url.path}"

        if not await self._limiter.is_allowed(route_key):
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

        return await call_next(request)
