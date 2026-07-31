import pytest

from database.repositories.sync_repository import SyncRepository


@pytest.mark.asyncio
async def test_save_and_get_checkpoint(db_session) -> None:
    repo = SyncRepository(db_session)
    cp = await repo.save_success(source="mock", entity_type="dataset", cursor="abc")
    assert cp.source == "mock"
    assert cp.entity_type == "dataset"
    assert cp.status == "completed"

    fetched = await repo.get_checkpoint("mock", "dataset")
    assert fetched is not None
    assert fetched.cursor == "abc"


@pytest.mark.asyncio
async def test_save_success_updates_existing(db_session) -> None:
    repo = SyncRepository(db_session)
    await repo.save_success(source="mock", entity_type="dashboard", cursor="v1")
    await repo.save_success(source="mock", entity_type="dashboard", cursor="v2")
    fetched = await repo.get_checkpoint("mock", "dashboard")
    assert fetched is not None
    assert fetched.cursor == "v2"


@pytest.mark.asyncio
async def test_save_failure(db_session) -> None:
    repo = SyncRepository(db_session)
    cp = await repo.save_failure(source="mock", entity_type="dataset", error="connection error")
    assert cp.status == "failed"
    assert cp.checkpoint_metadata == {"error": "connection error"}


@pytest.mark.asyncio
async def test_checkpoint_not_found(db_session) -> None:
    repo = SyncRepository(db_session)
    cp = await repo.get_checkpoint("unknown", "unknown")
    assert cp is None
