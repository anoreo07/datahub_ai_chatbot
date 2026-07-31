
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import MVP_ENTITY_TYPES
from config.settings import settings
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from database.repositories.sync_repository import SyncRepository
from ingestion import create_datahub_source
from ingestion.models import CanonicalEntity
from ingestion.normalizer import compute_content_hash
from ingestion.source import DataHubSource

log = structlog.get_logger()


class RealDataHubSyncService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._source: DataHubSource = create_datahub_source()
        self._entity_repo = EntityRepository(session)
        self._sync_repo = SyncRepository(session)
        self._index_repo = IndexJobRepository(session)
        self._dry_run = settings.DATAHUB_SYNC_DRY_RUN

    async def run_full_sync(self) -> dict[str, int]:
        results: dict[str, int] = {}
        for entity_type in MVP_ENTITY_TYPES:
            count = await self.sync_entity_type(entity_type)
            results[entity_type] = count
        return results

    async def sync_entity_type(self, entity_type: str) -> int:
        entities = await self._source.list_entity_type(entity_type)
        synced = 0
        for canonical in entities:
            try:
                changed = await self._sync_single(canonical)
                if changed:
                    synced += 1
            except Exception:
                log.exception("sync_failed", urn=canonical.urn, entity_type=entity_type)

        if not self._dry_run:
            source_name = "mock" if "Mock" in type(self._source).__name__ else "graphql"
            await self._sync_repo.save_success(
                source=source_name,
                entity_type=entity_type,
            )
        return synced

    async def sync_entity_by_urn(self, urn: str) -> bool:
        canonical = await self._source.get_entity(urn)
        if canonical is None:
            log.warning("entity_not_found_in_source", urn=urn)
            return False
        return await self._sync_single(canonical)

    async def _sync_single(self, canonical: CanonicalEntity) -> bool:
        content_hash = compute_content_hash(canonical)
        if self._dry_run:
            existing = await self._entity_repo.get_by_urn(canonical.urn)
            if existing:
                log.info("dry_run_change",
                    urn=canonical.urn,
                    entity_type=canonical.entity_type,
                    name=canonical.name,
                    changed=existing.content_hash != content_hash,
                )
            else:
                log.info("dry_run_new",
                    urn=canonical.urn,
                    entity_type=canonical.entity_type,
                    name=canonical.name,
                )
            return existing is None or existing.content_hash != content_hash

        existing = await self._entity_repo.get_by_urn(canonical.urn)
        if existing and existing.content_hash == content_hash:
            return False

        entity = Entity(
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
        return True

    async def sync_upstreams(self, urn: str) -> None:
        canonical = await self._source.get_entity(urn)
        if not canonical:
            return
        for upstream_urn in canonical.upstreams:
            await self.sync_entity_by_urn(upstream_urn)

    async def sync_entity_type_incremental(
        self,
        entity_type: str,
        cursor: str | None = None,
    ) -> int:
        source_name = type(self._source).__name__
        checkpoint = await self._sync_repo.get_checkpoint(source_name, entity_type)
        resume_cursor = cursor or (checkpoint.cursor if checkpoint else None)

        synced = 0
        while True:
            page = await self._source.list_entities(
                entity_type,
                cursor=resume_cursor,
                page_size=settings.DATAHUB_PAGE_SIZE,
            )
            for raw in page.items:
                urn = raw.get("urn", "")
                if not urn:
                    continue
                canonical = await self._source.get_entity(urn)
                if canonical:
                    try:
                        changed = await self._sync_single(canonical)
                        if changed:
                            synced += 1
                    except Exception:
                        log.exception("incremental_sync_failed", urn=urn)

            resume_cursor = page.next_cursor
            if not page.has_more or not resume_cursor:
                break

        if not self._dry_run:
            await self._sync_repo.save_success(
                source=source_name,
                entity_type=entity_type,
                cursor=resume_cursor,
            )
        return synced

    async def close(self) -> None:
        if hasattr(self._source, "close"):
            await self._source.close()
