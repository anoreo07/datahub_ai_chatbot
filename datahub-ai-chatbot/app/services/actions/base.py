"""Base action service providing entity resolution and authorization helpers."""
from __future__ import annotations

import re
from collections.abc import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from retrieval.entity_resolver import EntityResolver

log = structlog.get_logger()


class PermissionDeniedError(Exception):
    """Raised when a user requests metadata from a domain their roles cannot access."""

    def __init__(self, message: str, domain: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.domain = domain


class BaseActionService:
    """Shared foundation for action services requiring DataHub entity resolution and ACL checks."""

    def __init__(
        self,
        session: AsyncSession,
        auth_service: AuthorizationService | None = None,
    ) -> None:
        self._session = session
        self._repo = EntityRepository(session)
        self._resolver = EntityResolver(session)
        self._source: DataHubSource = create_datahub_source()
        self._auth_service = auth_service

    async def resolve_entity(
        self,
        query: str,
        *,
        user: UserContext | None = None,
        entity_type: str | None = None,
    ) -> Entity | None:
        if not query:
            return None
        clean_q = query.strip()
        # Strip common prefixes like 'dataset ', 'dashboard ', 'table ', 'bảng '
        clean_q = re.sub(
            r"^(?:dataset|dashboard|chart|table|bảng|bang|thực thể|entity)\s+",
            "",
            clean_q,
            flags=re.I,
        ).strip()
        resolution = await self._resolver.resolve(clean_q, entity_type=entity_type)
        if not resolution.resolved and entity_type is not None:
            # Fallback across all entity types if specific entity_type didn't match
            resolution = await self._resolver.resolve(clean_q, entity_type=None)
        if not resolution.resolved:
            return None
        entity = await self._repo.get_by_urn(resolution.resolved.urn)
        if entity is None:
            return None
        if user is not None and not await self._is_accessible(user, entity.urn):
            return None
        if user is not None and self._auth_service is not None:
            domain = (entity.domain or (entity.payload or {}).get("domain") or "").strip()
            if domain:
                message = await self._auth_service.access_message(user, domain)
                if message:
                    log.info(
                        "action_domain_denied",
                        user=user.user_id,
                        dataset=query[:100],
                        domain=domain,
                    )
                    raise PermissionDeniedError(message, domain=domain)
        return entity

    async def resolve_dataset(
        self, query: str, *, user: UserContext | None = None
    ) -> Entity | None:
        return await self.resolve_entity(query, user=user, entity_type="dataset")

    async def _is_accessible(self, user: UserContext, urn: str) -> bool:
        if self._auth_service is None:
            return True
        accessible = await self._auth_service.filter_accessible_urns(user, [urn])
        return urn in accessible

    async def _resolve_urns(self, urns: Sequence[str]) -> dict[str, Entity]:
        out: dict[str, Entity] = {}
        for e in await self._repo.list_by_urns(list(dict.fromkeys(urns))):
            out[e.urn] = e
        return out

    async def _lineage_urns(self, urn: str) -> tuple[list[str], list[str]]:
        """Live upstream/downstream URNs retrieved from the DataHub source with DB fallback."""
        upstreams: list[str] = []
        downstreams: list[str] = []
        try:
            up = await self._source.get_lineage(urn, direction="upstream")
            down = await self._source.get_lineage(urn, direction="downstream")
            upstreams = [
                r["entity"]["urn"]
                for r in up.get("relationships", [])
                if (r.get("entity") or {}).get("urn")
            ]
            downstreams = [
                r["entity"]["urn"]
                for r in down.get("relationships", [])
                if (r.get("entity") or {}).get("urn")
            ]
        except Exception:
            log.exception("action_lineage_failed", urn=urn)

        # Fallback to local DB synced payload if remote GraphQL was empty or blocked
        if not upstreams and not downstreams:
            entity = await self._repo.get_by_urn(urn)
            if entity and entity.payload:
                payload_up = entity.payload.get("upstreams") or []
                payload_down = entity.payload.get("downstreams") or []
                if isinstance(payload_up, list):
                    upstreams = [u for u in payload_up if isinstance(u, str)]
                if isinstance(payload_down, list):
                    downstreams = [d for d in payload_down if isinstance(d, str)]

        return upstreams, downstreams
