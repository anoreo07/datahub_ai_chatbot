"""Request timing and metrics middleware."""
import time

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.metrics import http_request_duration_seconds, http_requests_total

log = structlog.get_logger()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        http_request_duration_seconds.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()

        return response
