"""Run full sync from DataHub (or mock) to PostgreSQL."""
import asyncio

import structlog

from database.session import async_session_factory
from ingestion.sync import SyncOrchestrator

log = structlog.get_logger()


async def main() -> None:
    log.info("full_sync_started")
    async with async_session_factory() as session:
        orchestrator = SyncOrchestrator(session)
        results = await orchestrator.run_full_sync()
        log.info("full_sync_complete", results=results)


if __name__ == "__main__":
    asyncio.run(main())
