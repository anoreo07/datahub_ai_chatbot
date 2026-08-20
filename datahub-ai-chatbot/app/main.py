import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.actions import router as actions_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.datasource import router as datasource_router
from app.api.documents import router as documents_router
from app.api.glossary import router as glossary_router
from app.api.health import router as health_router
from app.api.index import router as index_router
from app.api.me import router as me_router
from app.api.metrics import router as metrics_router
from app.api.roles import router as roles_router
from app.api.search import router as search_router
from app.api.sync import router as sync_router
from app.api.storage import router as storage_router
from app.middleware.error_handler import ErrorHandlingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.action_service import PermissionDeniedError
from config.settings import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database.session import init_db
    await init_db()
    log.info("db_initialized")

    from database.session import async_session_factory
    from ingestion.sync import SyncOrchestrator
    async with async_session_factory() as session:
        orchestrator = SyncOrchestrator(session)
        # DATAHUB_SKIP_STARTUP_SYNC=1 boots from the already-loaded local DB
        # (the corporate DataHub is WAF-blocked; the sync would time out for
        # minutes and fail anyway). Data loaded via scripts/load_pulled_data.py
        # is still served normally.
        if os.environ.get("DATAHUB_SKIP_STARTUP_SYNC") != "1":
            try:
                results = await orchestrator.run_full_sync()
                log.info("initial_sync_complete", results=results)
            except Exception:
                log.exception("initial_sync_failed", msg="tiếp tục chạy với dữ liệu đã có trong DB")

        from app.api.dependencies.acl_seed import seed_acls, seed_rbac_roles
        await seed_acls(session)
        await seed_rbac_roles(session)
        log.info("acls_seeded")

    if not settings.USE_FAKE_OPENSEARCH:
        from indexing.pipeline import IndexingPipeline
        async with async_session_factory() as session:
            pipeline = IndexingPipeline(session)
            processed = await pipeline.process_pending_jobs(max_jobs=100)
            log.info("initial_indexing_complete", processed=processed)

    from app.services.health_service import healthcheck_loop
    health_task = asyncio.create_task(healthcheck_loop())
    log.info("periodic_healthcheck_started",
             interval_seconds=settings.HEALTHCHECK_INTERVAL_SECONDS)

    yield

    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="DataHub AI Chatbot",
    lifespan=lifespan,
)

app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(MetricsMiddleware)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)


@app.exception_handler(PermissionDeniedError)
async def _permission_denied_handler(request, exc: PermissionDeniedError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message, "code": "domain_access_denied"},
    )


app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(actions_router, prefix="/api/v1/actions", tags=["actions"])
app.include_router(health_router, tags=["health"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(conversations_router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(glossary_router, prefix="/api/v1/glossary", tags=["glossary"])
app.include_router(sync_router, prefix="/api/v1/sync", tags=["sync"])
app.include_router(roles_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(metrics_router, tags=["metrics"])
app.include_router(index_router, prefix="/api/v1/index", tags=["index"])
app.include_router(documents_router, tags=["documents"])
app.include_router(datasource_router, prefix="/api/v1/datasources", tags=["datasources"])
app.include_router(me_router, prefix="/api", tags=["dev"])
app.include_router(storage_router, prefix="/api/v1/storage", tags=["storage"])

