import asyncio

import structlog

from config.settings import settings
from database.session import async_session_factory

log = structlog.get_logger()


class DocumentWorker:
    async def run(self) -> None:
        log.info("document_worker_started")
        while True:
            try:
                async with async_session_factory() as session:
                    from database.repositories.entity_repository import EntityRepository
                    repo = EntityRepository(session)
                    docs = await repo.list_by_type("document")
                    for doc in docs:
                        if doc.content_hash:
                            continue
                        log.info("document_needs_processing", urn=doc.urn)
                    log.info("document_worker_idle", documents=len(docs))
                await asyncio.sleep(settings.INDEX_POLL_INTERVAL_SECONDS or 60)
            except asyncio.CancelledError:
                log.info("document_worker_stopped")
                break
            except Exception:
                log.exception("document_worker_error")
                await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(DocumentWorker().run())
