"""Test incremental sync service with mock source."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from database.repositories.sync_repository import SyncRepository
from ingestion.models import CanonicalEntity
from ingestion.normalizer import compute_content_hash
from sync.incremental_sync import IncrementalSyncService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def sync_service(mock_session):
    service = IncrementalSyncService(mock_session)
    service._entity_repo = AsyncMock(spec=EntityRepository)
    service._sync_repo = AsyncMock(spec=SyncRepository)
    service._index_repo = AsyncMock(spec=IndexJobRepository)
    return service


def _make_canonical(urn: str) -> CanonicalEntity:
    return CanonicalEntity(
        urn=urn,
        entity_type="dataset",
        name=urn.split(":")[-1],
        display_name=None,
        description=None,
        platform=None,
        environment=None,
        domain=None,
        owners=[],
        glossary_terms=[],
        tags=[],
        schema_fields=[],
        upstreams=[],
        downstreams=[],
        linked_documents=[],
        source_url=None,
        raw_properties={},
    )


@pytest.mark.asyncio
async def test_sync_entity_type_resume_cursor(sync_service):
    """Sync resumes from cursor checkpoint, stops when has_more=False."""
    mock_source = AsyncMock()

    page_1 = MagicMock()
    page_1.items = [{"urn": "urn:li:dataset:1"}, {"urn": "urn:li:dataset:2"}]
    page_1.has_more = True
    page_1.next_cursor = "cursor_2"

    page_2 = MagicMock()
    page_2.items = []
    page_2.has_more = False
    page_2.next_cursor = None

    mock_source.list_entities = AsyncMock(side_effect=[page_1, page_2])
    sync_service._source = mock_source

    mock_checkpoint = MagicMock()
    mock_checkpoint.cursor = "cursor_1"
    sync_service._sync_repo.get_checkpoint = AsyncMock(return_value=mock_checkpoint)

    sync_service._entity_repo.get_by_urn = AsyncMock(return_value=None)
    mock_source.get_entity = AsyncMock(side_effect=[
        _make_canonical("urn:li:dataset:1"),
        _make_canonical("urn:li:dataset:2"),
    ])

    count = await sync_service.sync_entity_type("dataset")
    assert count == 2


@pytest.mark.asyncio
async def test_sync_entity_type_duplicate_skipped(sync_service):
    """Entity with same content_hash is skipped."""
    mock_source = AsyncMock()

    canonical = _make_canonical("urn:li:dataset:dup")
    content_hash = compute_content_hash(canonical)

    existing = MagicMock()
    existing.content_hash = content_hash
    sync_service._entity_repo.get_by_urn = AsyncMock(return_value=existing)

    mock_source.get_entity = AsyncMock(return_value=canonical)

    page = MagicMock()
    page.items = [{"urn": "urn:li:dataset:dup"}]
    page.has_more = False
    page.next_cursor = None
    mock_source.list_entities = AsyncMock(return_value=page)
    sync_service._source = mock_source

    count = await sync_service.sync_entity_type("dataset")
    assert count == 0


@pytest.mark.asyncio
async def test_distributed_lock_prevents_duplicate(sync_service):
    """Lock acquire prevents two syncs running in parallel."""
    locked = await sync_service._lock.acquire("sync:dataset")
    assert locked is True
    locked_again = await sync_service._lock.acquire("sync:dataset")
    assert locked_again is False
    await sync_service._lock.release("sync:dataset")


@pytest.mark.asyncio
async def test_sync_lag_metric(sync_service):
    sync_service._sync_repo.get_checkpoint = AsyncMock(return_value=None)
    lag = await sync_service.get_sync_lag("dataset")
    assert lag is None
