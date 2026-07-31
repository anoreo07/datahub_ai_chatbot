import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from database.repositories.sync_repository import SyncRepository
from ingestion import create_datahub_source
from ingestion.normalizer import compute_content_hash
from ingestion.source import DataHubSource
from sync.locks import InMemoryLock
from sync.models import SyncMode

log = structlog.get_logger()


class IncrementalSyncService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._source: DataHubSource = create_datahub_source()
        self._entity_repo = EntityRepository(session)
        self._sync_repo = SyncRepository(session)
        self._index_repo = IndexJobRepository(session)
        self._lock = InMemoryLock()
        self._sync_mode = SyncMode.INCREMENTAL

    async def sync_entity_type(self, entity_type: str) -> int:
        source_name = type(self._source).__name__
        checkpoint = await self._sync_repo.get_checkpoint(source_name, entity_type)

        locked = await self._lock.acquire(f"sync:{entity_type}")
        if not locked:
            log.warning("sync_locked", entity_type=entity_type)
            return 0

        try:
            cursor = checkpoint.cursor if checkpoint else None
            synced = 0
            while True:
                page = await self._source.list_entities(
                    entity_type,
                    cursor=cursor,
                    page_size=settings.DATAHUB_PAGE_SIZE,
                )
                for raw in page.items:
                    urn = raw.get("urn", "")
                    if not urn:
                        continue
                    canonical = await self._source.get_entity(urn)
                    if canonical:
                        try:
                            content_hash = compute_content_hash(canonical)
                            existing = await self._entity_repo.get_by_urn(canonical.urn)
                            if existing and existing.content_hash == content_hash:
                                continue
                            from database.models import Entity as EntityDB

                            entity = EntityDB(
                                urn=canonical.urn,
                                entity_type=canonical.entity_type,
                                name=canonical.name,
                                display_name=canonical.display_name,
                                description=canonical.description,
                                platform=canonical.platform,
                                environment=canonical.environment,
                                domain=canonical.domain,
                                datahub_url=canonical.source_url,
                                payload=canonical.model_dump(mode="json", exclude={"raw_payload"}),
                                content_hash=content_hash,
                            )
                            await self._entity_repo.upsert(entity)
                            await self._index_repo.create(canonical.urn)
                            synced += 1
                        except Exception:
                            log.exception("incremental_sync_failed", urn=urn)

                if not page.has_more or not page.next_cursor:
                    break
                cursor = page.next_cursor

            await self._sync_repo.save_success(
                source=source_name,
                entity_type=entity_type,
                cursor=cursor,
            )
            return synced
        finally:
            await self._lock.release(f"sync:{entity_type}")

    async def run_full_sync_for_type(self, entity_type: str) -> int:
        self._sync_mode = SyncMode.FULL
        return await self.sync_entity_type(entity_type)

    async def get_sync_lag(self, entity_type: str) -> float | None:
        source_name = type(self._source).__name__
        checkpoint = await self._sync_repo.get_checkpoint(source_name, entity_type)
        if checkpoint and checkpoint.last_success_at:
            now = datetime.datetime.now(datetime.UTC)
            delta = now - checkpoint.last_success_at
            return delta.total_seconds()
        return None

    async def close(self) -> None:
        if hasattr(self._source, "close"):
            await self._source.close()
