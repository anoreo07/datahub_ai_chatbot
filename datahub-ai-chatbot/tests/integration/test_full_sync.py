import pytest

from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from ingestion.sync import SyncOrchestrator


@pytest.mark.asyncio
async def test_full_sync_creates_entities(db_session) -> None:
    orchestrator = SyncOrchestrator(db_session)
    results = await orchestrator.run_full_sync()
    assert results.get("dataset", 0) >= 2
    assert results.get("dashboard", 0) >= 1
    assert results.get("glossary_term", 0) >= 5
    assert results.get("document", 0) >= 1


@pytest.mark.asyncio
async def test_full_sync_creates_index_jobs(db_session) -> None:
    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()
    index_repo = IndexJobRepository(db_session)
    pending = await index_repo.count_pending()
    assert pending >= 10


@pytest.mark.asyncio
async def test_full_sync_idempotent(db_session) -> None:
    orchestrator = SyncOrchestrator(db_session)
    results1 = await orchestrator.run_full_sync()
    results2 = await orchestrator.run_full_sync()

    entity_repo = EntityRepository(db_session)
    count = await entity_repo.count_by_type()
    assert count > 0

    for entity_type, count_val in results1.items():
        if count_val > 0:
            assert results2.get(entity_type, 0) == 0, f"{entity_type} should have 0 changes on second sync"


@pytest.mark.asyncio
async def test_full_sync_stores_payload(db_session) -> None:
    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    entity_repo = EntityRepository(db_session)
    entity = await entity_repo.get_by_urn(
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)"
    )
    assert entity is not None
    assert entity.payload is not None
    assert entity.payload.get("name") == "sales.orders"
    assert entity.domain == "Sales"
    assert entity.datahub_url is not None


@pytest.mark.asyncio
async def test_full_sync_documents_persisted(db_session) -> None:
    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    entity_repo = EntityRepository(db_session)
    doc = await entity_repo.get_by_urn("urn:li:document:MonthlyRevenueMethodology")
    assert doc is not None
    assert doc.entity_type == "document"
