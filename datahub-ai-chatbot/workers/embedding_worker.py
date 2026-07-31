import asyncio

import structlog

from config.settings import settings
from database.session import async_session_factory

log = structlog.get_logger()


class EmbeddingWorker:
    async def run(self) -> None:
        log.info("embedding_worker_started")
        while True:
            try:
                async with async_session_factory() as session:
                    from database.repositories.entity_repository import EntityRepository
                    repo = EntityRepository(session)
                    entities = await repo.list_by_type("dataset")
                    for entity in entities:
                        if not entity.content_hash:
                            continue
                        log.info("entity_ready_for_embedding", urn=entity.urn)
                    log.info("embedding_worker_idle", entities=len(entities))
                await asyncio.sleep(settings.INDEX_POLL_INTERVAL_SECONDS or 60)
            except asyncio.CancelledError:
                log.info("embedding_worker_stopped")
                break
            except Exception:
                log.exception("embedding_worker_error")
                await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(EmbeddingWorker().run())
