"""Bootstrap script: run migrations, create OpenSearch index, seed data."""
import asyncio

import structlog

from config.settings import settings
from database.models import Base
from database.session import async_session_factory, engine
from indexing.vector_store import OpenSearchVectorStore
from ingestion.sync import SyncOrchestrator

log = structlog.get_logger()


async def bootstrap() -> None:
    log.info("bootstrap_started")

    log.info("checking_database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_tables_ensured")

    log.info("checking_opensearch")
    vs = OpenSearchVectorStore()
    try:
        await vs.ensure_index()
    finally:
        await vs.close()
    log.info("opensearch_index_ensured")

    if settings.USE_MOCK_DATAHUB:
        log.info("running_mock_sync")
        async with async_session_factory() as session:
            orchestrator = SyncOrchestrator(session)
            results = await orchestrator.run_full_sync()
            log.info("mock_sync_complete", results=results)

        log.info("running_initial_indexing")
        from indexing.pipeline import IndexingPipeline
        async with async_session_factory() as session:
            pipeline = IndexingPipeline(session)
            processed = await pipeline.process_pending_jobs(max_jobs=100)
            log.info("initial_indexing_complete", processed=processed)

    log.info("bootstrap_complete")


if __name__ == "__main__":
    asyncio.run(bootstrap())
