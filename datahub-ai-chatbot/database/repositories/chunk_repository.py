from collections.abc import Sequence

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import EntityChunk


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_entity(self, entity_urn: str, chunks: list[EntityChunk]) -> None:
        await self.delete_by_entity_urn(entity_urn)
        for chunk in chunks:
            self._session.add(chunk)
        await self._session.commit()

    async def list_by_entity_urn(self, entity_urn: str) -> Sequence[EntityChunk]:
        stmt = select(EntityChunk).where(EntityChunk.entity_urn == entity_urn).order_by(EntityChunk.chunk_index)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_by_entity_urn(self, entity_urn: str) -> None:
        stmt = sa_delete(EntityChunk).where(EntityChunk.entity_urn == entity_urn)
        await self._session.execute(stmt)
        await self._session.commit()

    async def list_by_urns(self, urns: list[str], limit: int = 100) -> Sequence[EntityChunk]:
        stmt = select(EntityChunk).where(EntityChunk.entity_urn.in_(urns)).order_by(EntityChunk.chunk_index).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
