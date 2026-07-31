"""Error handling middleware."""
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

log = structlog.get_logger()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception:
            log.exception("unhandled_error", path=str(request.url.path), method=request.method)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. Please try again later."},
            )
