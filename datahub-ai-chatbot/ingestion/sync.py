
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import MVP_ENTITY_TYPES
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from database.repositories.job_repository import JobRepository
from database.repositories.notification_repository import NotificationRepository
from database.repositories.sync_repository import SyncRepository
from ingestion import create_datahub_source
from ingestion.models import CanonicalEntity
from ingestion.normalizer import compute_content_hash
from ingestion.source import DataHubSource

log = structlog.get_logger()


class SyncOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._source: DataHubSource = create_datahub_source()
        self._entity_repo = EntityRepository(session)
        self._sync_repo = SyncRepository(session)
        self._index_repo = IndexJobRepository(session)
        self._job_repo = JobRepository(session)
        self._notif_repo = NotificationRepository(session)

    async def run_full_sync(self) -> dict:
        results: dict[str, int] = {}
        user_id = getattr(self._session.get_bind(), "execute") if hasattr(self._session.get_bind(), "execute") else None

        # Create full sync job
        job = await self._job_repo.create(
            type="full_sync",
            title="Full Data Sync",
            message="Starting full DataHub data synchronization...",
            user_id="system",  # full sync is admin action
            job_metadata={},
        )

        # Create notification linked to the job
        await self._notif_repo.create(
            job_id=job.id,
            user_id="system",
            type="full_sync",
            title="Full Data Sync",
            message="Starting full DataHub data synchronization...",
            status="running",
        )

        log.info("full_sync_started", job_id=job.id)

        for entity_type in MVP_ENTITY_TYPES:
            count = await self.sync_entity_type(entity_type)
            results[entity_type] = count

        # Mark job as completed
        await self._job_repo.mark_success(job.id)

        # Update notification to success
        await self._notif_repo.create(
            job_id=job.id,
            user_id="system",
            type="full_sync",
            title="Full Data Sync",
            message="Full DataSync completed",
            status="success",
        )

        log.info("full_sync_complete", job_id=job.id, results=results)
        return results

    async def sync_entity_type(self, entity_type: str) -> int:
        entities = await self._source.list_entity_type(entity_type)
        synced = 0
        for canonical in entities:
            try:
                if entity_type in ("dataset", "dashboard") and self._source.__class__.__name__ != "GraphQLDataHubSource":
                    enriched = await self._source.get_entity(canonical.urn)
                    if enriched:
                        canonical = enriched
                changed = await self._sync_single(canonical)
                if changed:
                    synced += 1
            except Exception:
                log.exception("sync_failed", urn=canonical.urn, entity_type=entity_type)
        await self._sync_repo.save_success(
            source="mock" if self._source.__class__.__name__ == "MockDataHubSource" else "graphql",
            entity_type=entity_type,
        )
        return synced

    async def sync_entity_by_urn(self, urn: str) -> bool:
        # Create entity sync job and notification
        job = await self._job_repo.create(
            type="entity_sync",
            title="Entity Sync",
            message=f"Syncing entity {urn[:50]}...",
            user_id="system",
            metadata={"urn": urn},
        )

        await self._notif_repo.create(
            job_id=job.id,
            user_id="system",
            type="entity_sync",
            title="Entity Sync",
            message=f"Syncing entity {urn[:50]}...",
            status="running",
        )

        canonical = await self._source.get_entity(urn)
        if canonical is None:
            log.warning("entity_not_found_in_source", urn=urn)
            # Mark job as failed
            await self._job_repo.mark_failed(job.id, "Entity not found in source")
            # Update notification to failed
            await self._notif_repo.create(
                job_id=job.id,
                user_id="system",
                type="entity_sync",
                title="Entity Sync",
                message=f"Entity {urn} not found",
                status="failed",
            )
            return False

        try:
            changed = await self._sync_single(canonical)

            if changed:
                await self._notif_repo.create(
                    job_id=job.id,
                    user_id="system",
                    type="entity_sync",
                    title="Entity Sync",
                    message=f"Entity {urn} synced successfully",
                    status="success",
                )
            else:
                await self._notif_repo.create(
                    job_id=job.id,
                    user_id="system",
                    type="entity_sync",
                    title="Entity Sync",
                    message=f"Entity {urn} already up to date",
                    status="success",
                )

            await self._job_repo.mark_success(job.id)
            return True
        except Exception as exc:
            log.exception("sync_failed", urn=urn, entity_type=canonical.entity_type if canonical else "unknown")
            await self._job_repo.mark_failed(job.id, str(exc))
            await self._notif_repo.create(
                job_id=job.id,
                user_id="system",
                type="entity_sync",
                title="Entity Sync",
                message=f"Sync failed for {urn}: {str(exc)[:200]}",
                status="failed",
            )
            return False

    async def _sync_single(self, canonical: CanonicalEntity) -> bool:
        content_hash = compute_content_hash(canonical)
        existing = await self._entity_repo.get_by_urn(canonical.urn)
        if existing and existing.content_hash == content_hash:
            return False

        domain_name = canonical.domain
        entity = Entity(
            urn=canonical.urn,
            entity_type=canonical.entity_type,
            name=canonical.name,
            display_name=canonical.display_name,
            description=canonical.description,
            platform=canonical.platform,
            environment=canonical.environment,
            domain=domain_name,
            datahub_url=canonical.datahub_url,
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
