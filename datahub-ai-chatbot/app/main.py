from contextlib import asynccontextmanager
from pathlib import Path

import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.actions import router as actions_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.glossary import router as glossary_router
from app.api.health import router as health_router
from app.api.index import router as index_router
from app.api.me import router as me_router
from app.api.metrics import router as metrics_router
from app.api.search import router as search_router
from app.api.sync import router as sync_router
from app.middleware.error_handler import ErrorHandlingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from config.settings import settings

import structlog

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
        results = await orchestrator.run_full_sync()
        log.info("initial_sync_complete", results=results)

        from app.api.dependencies.acl_seed import seed_acls
        await seed_acls(session)
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

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(actions_router, prefix="/api/v1/actions", tags=["actions"])
app.include_router(health_router, tags=["health"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(conversations_router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(glossary_router, prefix="/api/v1/glossary", tags=["glossary"])
app.include_router(sync_router, prefix="/api/v1/sync", tags=["sync"])
app.include_router(metrics_router, tags=["metrics"])
app.include_router(index_router, prefix="/api/v1/index", tags=["index"])
app.include_router(documents_router, tags=["documents"])
app.include_router(me_router, prefix="/api", tags=["dev"])

HERE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(HERE_DIR / "static")), name="static")


@app.get("/")
async def index() -> HTMLResponse:
    return HTMLResponse((HERE_DIR / "static" / "index.html").read_text())
