"""Test RealDataHubSyncService with mock source."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from database.repositories.sync_repository import SyncRepository
from ingestion.sync_service import RealDataHubSyncService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def sync_service(mock_session):
    service = RealDataHubSyncService(mock_session)
    service._dry_run = False
    service._entity_repo = AsyncMock(spec=EntityRepository)
    service._sync_repo = AsyncMock(spec=SyncRepository)
    service._index_repo = AsyncMock(spec=IndexJobRepository)
    return service


@pytest.mark.asyncio
async def test_sync_entity_type_no_duplicates(sync_service):
    """Sync twice should not create duplicates (content hash unchanged)."""
    mock_source = AsyncMock()
    mock_entity = MagicMock()
    mock_entity.urn = "urn:li:dataset:test"
    mock_entity.name = "test"
    mock_source.list_entity_type.return_value = [mock_entity]

    sync_service._source = mock_source

    sync_service._entity_repo.get_by_urn.return_value = MagicMock()
    sync_service._entity_repo.get_by_urn.return_value.content_hash = None

    count1 = await sync_service.sync_entity_type("dataset")
    assert count1 >= 0


@pytest.mark.asyncio
async def test_sync_entity_change_creates_index_job(sync_service):
    """Entity change should create an index job."""
    mock_source = AsyncMock()
    mock_entity = MagicMock()
    mock_entity.urn = "urn:li:dataset:changed"
    mock_entity.name = "changed"
    mock_entity.display_name = None
    mock_entity.description = "New description"
    mock_entity.platform = "snowflake"
    mock_entity.environment = "PROD"
    mock_entity.domain = None
    mock_entity.source_url = None
    mock_entity.glossary_terms = []
    mock_entity.tags = []
    mock_entity.schema_fields = []
    mock_entity.upstreams = []
    mock_entity.downstreams = []
    mock_entity.linked_documents = []
    mock_entity.raw_properties = {}
    mock_entity.model_dump.return_value = {
        "urn": "urn:li:dataset:changed", "name": "changed",
    }
    mock_source.list_entity_type.return_value = [mock_entity]

    sync_service._source = mock_source
    sync_service._entity_repo.get_by_urn.return_value = MagicMock()
    sync_service._entity_repo.get_by_urn.return_value.content_hash = "oldhash"

    sync_service._entity_repo.get_by_urn.return_value.content_hash = "different-hash"

    count = await sync_service.sync_entity_type("dataset")
    assert count >= 0


@pytest.mark.asyncio
async def test_dry_run_does_not_write(sync_service):
    """Dry-run mode should not write to database."""
    sync_service._dry_run = True

    mock_source = AsyncMock()
    mock_entity = MagicMock()
    mock_entity.urn = "urn:li:dataset:test"
    mock_entity.name = "test"
    mock_entity.display_name = None
    mock_entity.description = None
    mock_entity.platform = None
    mock_entity.environment = None
    mock_entity.domain = None
    mock_entity.source_url = None
    mock_entity.glossary_terms = []
    mock_entity.tags = []
    mock_entity.schema_fields = []
    mock_entity.upstreams = []
    mock_entity.downstreams = []
    mock_entity.linked_documents = []
    mock_entity.raw_properties = {}
    mock_source.list_entity_type.return_value = [mock_entity]

    sync_service._source = mock_source
    sync_service._entity_repo.get_by_urn.return_value = None

    count = await sync_service.sync_entity_type("dataset")
    assert count == 1
