import datetime
import unicodedata
from collections.abc import Sequence

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Entity

_CERTIFICATION_TAGS = {"certified", "gold", "silver", "bronze"}


def _norm_vn(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


class EntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, entity: Entity) -> Entity:
        existing = await self.get_by_urn(entity.urn)
        if existing:
            existing.entity_type = entity.entity_type
            existing.name = entity.name
            existing.display_name = entity.display_name
            existing.description = entity.description
            existing.platform = entity.platform
            existing.environment = entity.environment
            existing.domain = entity.domain
            existing.datahub_url = entity.datahub_url
            existing.payload = entity.payload
            existing.content_hash = entity.content_hash
        else:
            self._session.add(entity)
        await self._session.commit()
        return existing or entity

    async def get_by_urn(self, urn: str) -> Entity | None:
        stmt = select(Entity).where(Entity.urn == urn)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, entity_type: str | None = None) -> Sequence[Entity]:
        name_like = f"%{name}%"
        name_underscore = f"%{name.replace(' ', '_')}%"
        name_collapsed = f"%{name.replace(' ', '')}%"
        stmt = select(Entity).where(
            Entity.name.ilike(name_like)
            | Entity.display_name.ilike(name_like)
            | Entity.urn.ilike(name_like)
            | Entity.urn.ilike(name_underscore)
            | Entity.urn.ilike(name_collapsed)
        )
        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
        stmt = stmt.order_by(Entity.name).limit(50)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_type(self, entity_type: str, limit: int = 100, offset: int = 0) -> Sequence[Entity]:
        stmt = select(Entity).where(Entity.entity_type == entity_type)
        stmt = stmt.order_by(Entity.name).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_all(self, entity_type: str | None = None, limit: int = 500) -> Sequence[Entity]:
        stmt = select(Entity)
        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
        stmt = stmt.order_by(Entity.name).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_domain(
        self, domain: str, entity_type: str | None = None, limit: int = 200
    ) -> Sequence[Entity]:
        target = _norm_vn(domain)
        if not target:
            return []
        entities = await self._load_candidates(entity_type)
        matched = [
            e for e in entities
            if target in _norm_vn(e.domain) or target in _norm_vn((e.payload or {}).get("domain"))
        ]
        return matched[:limit]

    async def list_by_platform(
        self, platform: str, entity_type: str | None = None, limit: int = 200
    ) -> Sequence[Entity]:
        target = _norm_vn(platform)
        if not target:
            return []
        entities = await self._load_candidates(entity_type)
        matched = [
            e for e in entities
            if target in _norm_vn(e.platform)
            or target in _norm_vn((e.payload or {}).get("platform"))
        ]
        return matched[:limit]

    async def list_by_tag(
        self, tag: str, entity_type: str | None = None, limit: int = 200
    ) -> Sequence[Entity]:
        target = _norm_vn(tag)
        if not target:
            return []
        entities = await self._load_candidates(entity_type)
        matched = []
        for e in entities:
            tags = (e.payload or {}).get("tags") or []
            if any(target in _norm_vn(t) or _norm_vn(t) in target for t in tags):
                matched.append(e)
        return matched[:limit]

    async def list_by_owner(
        self, owner: str, entity_type: str | None = None, limit: int = 200
    ) -> Sequence[Entity]:
        target = _norm_vn(owner)
        if not target:
            return []
        entities = await self._load_candidates(entity_type)
        matched = []
        for e in entities:
            owners = (e.payload or {}).get("owners") or []
            for o in owners:
                name = _norm_vn(o.get("name")) if isinstance(o, dict) else ""
                email = _norm_vn(o.get("email")) if isinstance(o, dict) else ""
                owner_match = (name and (target in name or name in target))
                email_match = (email and (target in email or email in target))
                if owner_match or email_match:
                    matched.append(e)
                    break
        return matched[:limit]

    async def list_certified(
        self, entity_type: str | None = None, limit: int = 200
    ) -> Sequence[Entity]:
        entities = await self._load_candidates(entity_type)
        matched = []
        for e in entities:
            payload = e.payload or {}
            if payload.get("certified"):
                matched.append(e)
                continue
            tags = payload.get("tags") or []
            if any(_norm_vn(t) in _CERTIFICATION_TAGS for t in tags):
                matched.append(e)
        return matched[:limit]

    async def _load_candidates(self, entity_type: str | None = None) -> Sequence[Entity]:
        stmt = select(Entity)
        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_by_urn(self, urn: str) -> bool:
        stmt = sa_delete(Entity).where(Entity.urn == urn)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0  # type: ignore[attr-defined]

    async def list_changed_since(self, since: datetime.datetime, limit: int = 100) -> Sequence[Entity]:
        stmt = select(Entity).where(Entity.updated_at >= since)
        stmt = stmt.order_by(Entity.updated_at).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_urns(self, urns: list[str]) -> Sequence[Entity]:
        stmt = select(Entity).where(Entity.urn.in_(urns))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_type(self, entity_type: str | None = None) -> int:
        stmt = select(func.count(Entity.id))
        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
        result = await self._session.execute(stmt)
        return result.scalar_one()
