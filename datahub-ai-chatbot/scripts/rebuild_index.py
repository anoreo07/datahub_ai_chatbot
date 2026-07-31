"""Rebuild OpenSearch index from PostgreSQL data."""
import asyncio

import structlog

from database.session import async_session_factory
from indexing.pipeline import IndexingPipeline
from indexing.vector_store import OpenSearchVectorStore

log = structlog.get_logger()


async def main() -> None:
    log.info("rebuild_index_started")
    vs = OpenSearchVectorStore()
    await vs.ensure_index()

    async with async_session_factory() as session:
        pipeline = IndexingPipeline(session)
        processed = await pipeline.process_pending_jobs(max_jobs=100)
        log.info("rebuild_index_complete", processed=processed)


if __name__ == "__main__":
    asyncio.run(main())
