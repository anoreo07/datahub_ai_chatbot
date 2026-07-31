import pytest

from database.repositories.index_job_repository import IndexJobRepository


@pytest.mark.asyncio
async def test_create_and_get_pending(db_session) -> None:
    repo = IndexJobRepository(db_session)
    job = await repo.create("urn:test:job1")
    assert job.entity_urn == "urn:test:job1"
    assert job.status == "pending"

    pending = await repo.get_pending()
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_mark_running(db_session) -> None:
    repo = IndexJobRepository(db_session)
    job = await repo.create("urn:test:run")
    updated = await repo.mark_running(job.id)
    assert updated is not None
    assert updated.status == "processing"
    assert updated.attempts == 1


@pytest.mark.asyncio
async def test_mark_completed(db_session) -> None:
    repo = IndexJobRepository(db_session)
    job = await repo.create("urn:test:complete")
    await repo.mark_running(job.id)
    updated = await repo.mark_completed(job.id)
    assert updated is not None
    assert updated.status == "completed"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_mark_failed(db_session) -> None:
    repo = IndexJobRepository(db_session)
    job = await repo.create("urn:test:fail")
    await repo.mark_running(job.id)
    updated = await repo.mark_failed(job.id, "test error")
    assert updated is not None
    assert updated.status == "failed"
    assert updated.error == "test error"


@pytest.mark.asyncio
async def test_get_pending_respects_limit(db_session) -> None:
    repo = IndexJobRepository(db_session)
    for i in range(5):
        await repo.create(f"urn:test:limit:{i}")

    pending = await repo.get_pending(limit=3)
    assert len(pending) == 3


@pytest.mark.asyncio
async def test_count_pending(db_session) -> None:
    repo = IndexJobRepository(db_session)
    for i in range(3):
        await repo.create(f"urn:test:cnt:{i}")

    count = await repo.count_pending()
    assert count == 3
