import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Entity as EntityDB
from database.repositories.chunk_repository import ChunkRepository
from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from ingestion import create_datahub_source
from ingestion.normalizer import compute_content_hash
from ingestion.source import DataHubSource
from sync.dlq import DeadLetterQueue, InMemoryDeadLetterQueue
from sync.models import DeleteMode, MetadataChangeEvent
from sync.retry import RetryPolicy

log = structlog.get_logger()


class MetadataEventHandler:
    def __init__(
        self,
        session: AsyncSession,
        dlq: DeadLetterQueue | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._session = session
        self._source: DataHubSource = create_datahub_source()
        self._entity_repo = EntityRepository(session)
        self._chunk_repo = ChunkRepository(session)
        self._index_repo = IndexJobRepository(session)
        self._dlq = dlq or InMemoryDeadLetterQueue()
        self._retry = retry_policy or RetryPolicy()
        self._delete_mode = DeleteMode.SOFT

    async def handle(self, event: MetadataChangeEvent) -> bool:
        try:
            return await self._retry.execute(self._handle_single, event)
        except Exception as e:
            from guardrails.sanitizer import mask_secrets
            err = mask_secrets(str(e))
            log.error("event_handler_failed", event_id=event.event_id, error=err)
            await self._dlq.push(event, err)
            return False

    async def _handle_single(self, event: MetadataChangeEvent) -> bool:
        if event.event_type.value == "CREATE":
            return await self._handle_create(event)
        if event.event_type.value == "UPDATE":
            return await self._handle_update(event)
        if event.event_type.value == "DELETE":
            return await self._handle_delete(event)
        log.warning("unknown_event_type", event_type=event.event_type)
        return False

    async def _handle_create(self, event: MetadataChangeEvent) -> bool:
        canonical = await self._source.get_entity(event.entity_urn)
        if canonical is None:
            log.warning("create_entity_not_found", urn=event.entity_urn)
            return False

        content_hash = compute_content_hash(canonical)
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

        log.info("event_created", urn=event.entity_urn, entity_type=canonical.entity_type)
        return True

    async def _handle_update(self, event: MetadataChangeEvent) -> bool:
        canonical = await self._source.get_entity(event.entity_urn)
        if canonical is None:
            log.warning("update_entity_not_found", urn=event.entity_urn)
            return False

        content_hash = compute_content_hash(canonical)
        existing = await self._entity_repo.get_by_urn(canonical.urn)
        if existing and existing.content_hash == content_hash:
            return False

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

        log.info("event_updated", urn=event.entity_urn)
        return True

    async def _handle_delete(self, event: MetadataChangeEvent) -> bool:
        if self._delete_mode == DeleteMode.HARD:
            await self._chunk_repo.delete_by_entity_urn(event.entity_urn)
            await self._entity_repo.delete_by_urn(event.entity_urn)
        else:
            existing = await self._entity_repo.get_by_urn(event.entity_urn)
            if existing:
                existing.payload = existing.payload or {}
                existing.payload["deleted"] = True
                await self._session.merge(existing)
                await self._session.commit()

        log.info("event_deleted", urn=event.entity_urn, mode=self._delete_mode.value)
        return True

    async def close(self) -> None:
        if hasattr(self._source, "close"):
            await self._source.close()
