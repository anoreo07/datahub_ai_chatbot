import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository


@pytest.mark.asyncio
async def test_upsert_and_get_by_urn(db_session) -> None:
    repo = EntityRepository(db_session)
    entity = Entity(
        urn="urn:test:1",
        entity_type="dataset",
        name="test_dataset",
        description="Test description",
        platform="snowflake",
        environment="PROD",
        domain="Test",
        datahub_url="http://example.com/test",
        payload={"key": "value"},
        content_hash="abc123",
    )
    created = await repo.upsert(entity)
    assert created.urn == "urn:test:1"

    fetched = await repo.get_by_urn("urn:test:1")
    assert fetched is not None
    assert fetched.name == "test_dataset"
    assert fetched.payload == {"key": "value"}


@pytest.mark.asyncio
async def test_upsert_updates_existing(db_session) -> None:
    repo = EntityRepository(db_session)
    entity = Entity(urn="urn:test:2", entity_type="dataset", name="original", content_hash="h1")
    await repo.upsert(entity)

    updated = Entity(urn="urn:test:2", entity_type="dataset", name="updated", content_hash="h2")
    result = await repo.upsert(updated)
    assert result.name == "updated"


@pytest.mark.asyncio
async def test_search_by_name(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(3):
        await repo.upsert(Entity(
            urn=f"urn:test:search:{i}", entity_type="dataset", name=f"dataset_{i}",
        ))
    results = await repo.search_by_name("dataset")
    assert len(results) >= 3


@pytest.mark.asyncio
async def test_list_by_type(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(Entity(urn="urn:d:1", entity_type="dataset", name="d1"))
    await repo.upsert(Entity(urn="urn:d:2", entity_type="dataset", name="d2"))
    await repo.upsert(Entity(urn="urn:g:1", entity_type="glossary_term", name="g1"))

    datasets = await repo.list_by_type("dataset")
    assert len(datasets) == 2

    terms = await repo.list_by_type("glossary_term")
    assert len(terms) == 1


@pytest.mark.asyncio
async def test_delete_by_urn(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(Entity(urn="urn:test:del", entity_type="dataset", name="to_delete"))
    deleted = await repo.delete_by_urn("urn:test:del")
    assert deleted is True

    fetched = await repo.get_by_urn("urn:test:del")
    assert fetched is None


@pytest.mark.asyncio
async def test_count_by_type(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(Entity(urn="urn:c:1", entity_type="dataset", name="c1"))
    await repo.upsert(Entity(urn="urn:c:2", entity_type="dataset", name="c2"))
    count = await repo.count_by_type("dataset")
    assert count == 2
