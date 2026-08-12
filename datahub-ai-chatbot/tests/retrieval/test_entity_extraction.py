import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.entity_extraction import EntityExtractor


def _entity(urn: str, name: str, entity_type: str = "dataset") -> Entity:
    return Entity(
        urn=urn,
        entity_type=entity_type,
        name=name,
        display_name=name,
        platform="redshift",
        environment="PROD",
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload={"display_name": name, "description": f"desc {name}"},
    )


@pytest.mark.asyncio
async def test_extract_whole_sentence_not_entity(db_session) -> None:
    """A long sentence must not be returned as the entity name; the real
    catalog entity embedded in it is extracted instead."""
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:dim_warehouse", "dim_warehouse"))
    await repo.upsert(_entity("urn:fact_sales", "fact_sales"))

    extractor = EntityExtractor(db_session)
    found = await extractor.extract("xoa dim warehouse thi bi anh huong")
    assert found
    assert found[0].name == "dim_warehouse"
    assert found[0].entity_type == "dataset"


@pytest.mark.asyncio
async def test_extract_underscore_and_space_equivalent(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:dim_warehouse", "dim_warehouse"))

    extractor = EntityExtractor(db_session)
    from_underscore = await extractor.extract("Nếu xóa dim_warehouse thì sao?")
    from_space = await extractor.extract("Nếu xóa dim warehouse thì sao?")
    assert from_underscore and from_underscore[0].urn == "urn:dim_warehouse"
    assert from_space and from_space[0].urn == "urn:dim_warehouse"


@pytest.mark.asyncio
async def test_extract_primary_dataset_ignores_non_dataset(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:fact_sales", "fact_sales", "dataset"))

    extractor = EntityExtractor(db_session)
    best = await extractor.resolve_primary_dataset("fact_sales affected?")
    assert best is not None
    assert best.urn == "urn:fact_sales"


@pytest.mark.asyncio
async def test_extract_no_match_returns_empty(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:fact_sales", "fact_sales"))

    extractor = EntityExtractor(db_session)
    found = await extractor.extract("bạn là ai")
    assert found == []


@pytest.mark.asyncio
async def test_extract_phrase_before_and_after(db_session) -> None:
    """Entity should be found whether surrounded by words (impact-style Q)."""
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:dim_warehouse", "dim_warehouse"))

    extractor = EntityExtractor(db_session)
    q = "Nếu thay đổi dataset dim_warehouse thì những ai bị ảnh hưởng?"
    found = await extractor.extract(q)
    assert found and found[0].urn == "urn:dim_warehouse"
