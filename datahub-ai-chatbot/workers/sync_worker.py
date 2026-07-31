import asyncio

import structlog

from database.session import async_session_factory
from ingestion.sync import SyncOrchestrator

log = structlog.get_logger()


async def main() -> None:
    log.info("sync_worker_started")
    while True:
        try:
            async with async_session_factory() as session:
                orchestrator = SyncOrchestrator(session)
                results = await orchestrator.run_full_sync()
                log.info("sync_cycle_complete", results=results)
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            log.info("sync_worker_stopped")
            break
        except Exception:
            log.exception("sync_worker_error")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
