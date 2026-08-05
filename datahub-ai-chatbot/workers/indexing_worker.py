import asyncio

import structlog

from config.settings import settings
from database.session import async_session_factory
from indexing.pipeline import IndexingPipeline
from indexing.vector_store import OpenSearchVectorStore

log = structlog.get_logger()


class IndexingWorker:
    async def run(self) -> None:
        log.info("indexing_worker_started")
        vector_store = OpenSearchVectorStore()
        await vector_store.ensure_index()

        while True:
            try:
                async with async_session_factory() as session:
                    pipeline = IndexingPipeline(session)
                    count = await pipeline.process_pending_jobs(max_jobs=settings.INDEX_BATCH_SIZE)
                    if count:
                        log.info("jobs_processed", count=count)
                    else:
                        await asyncio.sleep(settings.INDEX_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                log.info("indexing_worker_stopped")
                break
            except Exception:
                log.exception("indexing_worker_error")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(IndexingWorker().run())
