import pytest

from database.models import Entity, EntityChunk
from database.repositories.chunk_repository import ChunkRepository
from database.repositories.entity_repository import EntityRepository


@pytest.mark.asyncio
async def test_replace_for_entity(db_session) -> None:
    entity_repo = EntityRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    entity = Entity(urn="urn:test:chunks", entity_type="dataset", name="chunk_test")
    await entity_repo.upsert(entity)

    chunks = [
        EntityChunk(entity_urn="urn:test:chunks", chunk_type="summary", chunk_index=0, content="test", content_hash="h1"),
        EntityChunk(entity_urn="urn:test:chunks", chunk_type="schema", chunk_index=1, content="fields", content_hash="h2"),
    ]
    await chunk_repo.replace_for_entity("urn:test:chunks", chunks)

    stored = await chunk_repo.list_by_entity_urn("urn:test:chunks")
    assert len(stored) == 2
    assert stored[0].chunk_type == "summary"
    assert stored[1].chunk_type == "schema"


@pytest.mark.asyncio
async def test_replace_overwrites_old_chunks(db_session) -> None:
    chunk_repo = ChunkRepository(db_session)
    entity_repo = EntityRepository(db_session)
    await entity_repo.upsert(Entity(urn="urn:test:replace", entity_type="dataset", name="replace"))

    old = [EntityChunk(entity_urn="urn:test:replace", chunk_type="old", chunk_index=0, content="old", content_hash="h")]
    await chunk_repo.replace_for_entity("urn:test:replace", old)

    new = [EntityChunk(entity_urn="urn:test:replace", chunk_type="new", chunk_index=0, content="new", content_hash="h")]
    await chunk_repo.replace_for_entity("urn:test:replace", new)

    stored = await chunk_repo.list_by_entity_urn("urn:test:replace")
    assert len(stored) == 1
    assert stored[0].chunk_type == "new"


@pytest.mark.asyncio
async def test_delete_by_entity_urn(db_session) -> None:
    chunk_repo = ChunkRepository(db_session)
    entity_repo = EntityRepository(db_session)
    await entity_repo.upsert(Entity(urn="urn:test:delchunk", entity_type="dataset", name="del"))
    chunks = [EntityChunk(entity_urn="urn:test:delchunk", chunk_type="t", chunk_index=0, content="c", content_hash="h")]
    await chunk_repo.replace_for_entity("urn:test:delchunk", chunks)

    await chunk_repo.delete_by_entity_urn("urn:test:delchunk")
    stored = await chunk_repo.list_by_entity_urn("urn:test:delchunk")
    assert len(stored) == 0
