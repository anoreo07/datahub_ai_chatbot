import uuid
from collections.abc import Callable, Sequence
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain_utils import domain_key
from app.auth.models import (
    AuditEvent,
    EntityAcl,
    UserContext,
)
from app.auth.rbac import RbacService
from database.models import Entity, EntityAclDB

log = structlog.get_logger()


class AuthorizationService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._in_memory_acls: dict[str, EntityAcl] = {}
        self._rbac = RbacService(session=session)

    # ------------------------------------------------------------------
    # Domain RBAC — data-driven permission model
    # ------------------------------------------------------------------

    @property
    def rbac(self) -> RbacService:
        return self._rbac

    async def refresh_permissions(self) -> None:
        """Force-refresh the RBAC snapshot (called after admin role changes)."""
        await self._rbac.refresh()

    async def can_access_domain(self, user: UserContext, domain: str | None) -> bool:
        return await self._rbac.can_access_domain(user, domain)

    async def allowed_domains(self, user: UserContext) -> set[str]:
        return await self._rbac.allowed_domains(user)

    async def access_message(self, user: UserContext, domain: str | None) -> str | None:
        return await self._rbac.access_message(user, domain)

    async def filter_domains(
        self, user: UserContext, domains: list[str | None]
    ) -> list[str | None]:
        """Return only the domains the user may access (admin keeps all)."""
        allowed = await self.allowed_domains(user)
        if "*" in allowed:
            return list(domains)
        return [d for d in domains if await self.can_access_domain(user, d)]

    async def accessible_domains(self, user: UserContext) -> set[str]:
        """Set of accessible domain keys; ``{"*"}`` for admins (full access)."""
        allowed = await self.allowed_domains(user)
        if "*" in allowed:
            return {"*"}
        keys: set[str] = set()
        for d in allowed:
            keys.add(domain_key(d))
        return keys

    async def filter_results_by_domain(
        self,
        user: UserContext,
        results: Sequence[Any],
        domain_of: Callable[[Any], str | None],
    ) -> list[Any]:
        """Post-retrieval domain filter for search results.

        ``domain_of`` extracts an entity's domain from a result. Entities whose
        domain is not granted to the user are dropped. Admin keeps everything.
        """
        if user.is_admin:
            return list(results)
        allowed = await self.accessible_domains(user)
        if "*" in allowed:
            return list(results)
        kept: list[Any] = []
        for r in results:
            domain = (domain_of(r) or "").strip()
            if not domain or domain_key(domain) in allowed:
                kept.append(r)
        return kept

    async def _domain_of(self, entity_urn: str) -> str | None:
        if self._session is None:
            return None
        try:
            result = await self._session.execute(
                select(Entity).where(Entity.urn == entity_urn)
            )
            entity = result.scalar_one_or_none()
            if entity is None:
                return None
            return (entity.domain or (entity.payload or {}).get("domain") or "").strip() or None
        except Exception:
            return None

    async def filter_entities_by_domain(
        self,
        user: UserContext,
        entities: Sequence[Entity],
    ) -> list[Entity]:
        """Post-retrieval domain filtering: drop entities whose domain is not
        granted to the user. Admin and entities without a domain pass through."""
        if user.is_admin or "*" in await self.allowed_domains(user):
            return list(entities)
        result: list[Entity] = []
        for e in entities:
            domain = (e.domain or (e.payload or {}).get("domain") or "").strip()
            if not domain:
                result.append(e)
            elif await self.can_access_domain(user, domain):
                result.append(e)
        return result

    async def can_view_entity(self, user: UserContext, entity_urn: str) -> bool:
        if user.is_admin:
            return True

        acl = await self._get_acl(entity_urn)
        if not acl:
            return True

        if acl.tenant_id and user.tenant_id and acl.tenant_id != user.tenant_id:
            await self._audit(user, "view_entity", entity_urn, "denied", "tenant_mismatch")
            return False

        if user.user_id in acl.denied_user_ids:
            await self._audit(user, "view_entity", entity_urn, "denied", "user_denied")
            return False

        denied_groups = set(acl.denied_groups)
        if denied_groups.intersection(set(user.groups)):
            await self._audit(user, "view_entity", entity_urn, "denied", "group_denied")
            return False

        if acl.is_public:
            return True

        if user.user_id in acl.allowed_user_ids:
            return True

        if user.email in acl.allowed_emails:
            return True

        allowed_groups = set(acl.allowed_groups)
        if allowed_groups.intersection(set(user.groups)):
            return True

        await self._audit(user, "view_entity", entity_urn, "denied", "no_allow_rule")
        return False

    async def can_view_chunk(self, user: UserContext, entity_urn: str) -> bool:
        return await self.can_view_entity(user, entity_urn)

    async def filter_entities(
        self,
        user: UserContext,
        entities: Sequence[Entity],
    ) -> list[Entity]:
        if user.is_admin:
            return list(entities)

        result: list[Entity] = []
        for entity in entities:
            if await self.can_view_entity(user, entity.urn):
                result.append(entity)
        return result

    async def filter_accessible_urns(
        self,
        user: UserContext,
        urns: Sequence[str],
    ) -> set[str]:
        if user.is_admin:
            return set(urns)

        unique = list(dict.fromkeys(urns))
        acls: dict[str, EntityAcl] = {}
        if self._session is not None and unique:
            try:
                result = await self._session.execute(
                    select(EntityAclDB).where(EntityAclDB.entity_urn.in_(unique))
                )
                for db_acl in result.scalars().all():
                    acls[db_acl.entity_urn] = EntityAcl(
                        entity_urn=db_acl.entity_urn,
                        is_public=db_acl.is_public,
                        allowed_user_ids=list(db_acl.allowed_user_ids or []),
                        allowed_groups=list(db_acl.allowed_groups or []),
                        denied_user_ids=list(db_acl.denied_user_ids or []),
                        denied_groups=list(db_acl.denied_groups or []),
                        tenant_id=db_acl.tenant_id,
                        classification=db_acl.classification,
                    )
                    self._in_memory_acls[db_acl.entity_urn] = acls[db_acl.entity_urn]
            except Exception:
                log.warning("acl_batch_load_failed")

        user_groups = set(user.groups)
        allowed: set[str] = set()
        for urn in unique:
            acl = acls.get(urn)
            if acl is None:
                allowed.add(urn)
                continue
            if acl.tenant_id and user.tenant_id and acl.tenant_id != user.tenant_id:
                continue
            if user.user_id in acl.denied_user_ids:
                continue
            if user_groups.intersection(set(acl.denied_groups)):
                continue
            if acl.is_public:
                allowed.add(urn)
                continue
            if user.user_id in acl.allowed_user_ids or user.email in acl.allowed_emails:
                allowed.add(urn)
                continue
            if user_groups.intersection(set(acl.allowed_groups)):
                allowed.add(urn)
        return allowed

    async def build_database_acl_filter(self, user: UserContext) -> object | None:
        if user.is_admin:
            return None
        accessible = await self._get_user_accessible_urns(user)
        denied = await self._get_user_denied_urns(user)
        from sqlalchemy import and_, not_

        from database.models import Entity
        if accessible and not denied:
            return Entity.urn.in_(accessible)
        if denied and not accessible:
            return and_(Entity.urn.in_(accessible) if accessible else not_(Entity.urn.in_(denied)))
        if accessible and denied:
            return and_(Entity.urn.in_(accessible), not_(Entity.urn.in_(denied)))
        # No session or no ACL data — restrict to public entities as safe default
        if self._session is None:
            return None  # caller decides fallback
        return not_(Entity.urn.in_(denied)) if denied else None

    async def build_opensearch_acl_filter(self, user: UserContext) -> dict | None:
        if user.is_admin:
            return None
        accessible = await self._get_user_accessible_urns(user)
        denied = await self._get_user_denied_urns(user)
        should_clauses = []
        if accessible:
            should_clauses.append({"terms": {"entity_urn": accessible}})
        if denied:
            filter_clause = {"bool": {"must_not": {"terms": {"entity_urn": denied}}}}
            if should_clauses:
                return {"bool": {"must": [{"bool": {"should": should_clauses}}, filter_clause]}}
            return filter_clause
        # Non-admin with no ACL rules — restrict to public entities
        public_urns = await self._get_public_urns(user)
        if public_urns:
            return {"terms": {"entity_urn": public_urns}}
        # No ACL data at all — restrict everything for non-admin
        return {"terms": {"entity_urn": []}}

    async def _get_acl(self, entity_urn: str) -> EntityAcl | None:
        if entity_urn in self._in_memory_acls:
            return self._in_memory_acls[entity_urn]
        if self._session is not None:
            try:
                result = await self._session.execute(
                    select(EntityAclDB).where(EntityAclDB.entity_urn == entity_urn)
                )
                db_acl = result.scalar_one_or_none()
                if db_acl:
                    acl = EntityAcl(
                        entity_urn=db_acl.entity_urn,
                        is_public=db_acl.is_public,
                        allowed_user_ids=list(db_acl.allowed_user_ids or []),
                        allowed_groups=list(db_acl.allowed_groups or []),
                        denied_user_ids=list(db_acl.denied_user_ids or []),
                        denied_groups=list(db_acl.denied_groups or []),
                        tenant_id=db_acl.tenant_id,
                        classification=db_acl.classification,
                    )
                    self._in_memory_acls[entity_urn] = acl
                    return acl
            except Exception:
                log.warning("acl_db_load_failed", entity_urn=entity_urn)
        return None

    def set_acl(self, acl: EntityAcl) -> None:
        self._in_memory_acls[acl.entity_urn] = acl

    async def set_acl_db(self, acl: EntityAcl) -> None:
        self._in_memory_acls[acl.entity_urn] = acl
        if self._session is None:
            return
        try:
            result = await self._session.execute(
                select(EntityAclDB).where(EntityAclDB.entity_urn == acl.entity_urn)
            )
            db_acl = result.scalar_one_or_none()
            if db_acl:
                db_acl.is_public = acl.is_public
                db_acl.allowed_user_ids = acl.allowed_user_ids
                db_acl.allowed_groups = acl.allowed_groups
                db_acl.denied_user_ids = acl.denied_user_ids
                db_acl.denied_groups = acl.denied_groups
                db_acl.classification = acl.classification
                db_acl.tenant_id = acl.tenant_id
            else:
                db_acl = EntityAclDB(
                    entity_urn=acl.entity_urn,
                    is_public=acl.is_public,
                    allowed_user_ids=acl.allowed_user_ids,
                    allowed_groups=acl.allowed_groups,
                    denied_user_ids=acl.denied_user_ids,
                    denied_groups=acl.denied_groups,
                    classification=acl.classification,
                    tenant_id=acl.tenant_id,
                )
                self._session.add(db_acl)
            await self._session.commit()
        except Exception:
            log.exception("acl_db_save_failed", entity_urn=acl.entity_urn)

    async def _get_user_accessible_urns(self, user: UserContext) -> list[str]:
        if self._session is None:
            return []
        try:
            result = await self._session.execute(
                select(EntityAclDB.entity_urn).where(
                    EntityAclDB.is_public.is_(True)
                    | EntityAclDB.allowed_user_ids.any(user.user_id)
                    | EntityAclDB.allowed_groups.overlap(user.groups)
                )
            )
            return [row[0] for row in result.all()]
        except Exception:
            log.warning("acl_get_accessible_failed")
            return []

    async def _get_user_denied_urns(self, user: UserContext) -> list[str]:
        if self._session is None:
            return []
        try:
            result = await self._session.execute(
                select(EntityAclDB.entity_urn).where(
                    EntityAclDB.denied_user_ids.any(user.user_id)
                    | EntityAclDB.denied_groups.overlap(user.groups)
                )
            )
            return [row[0] for row in result.all()]
        except Exception:
            log.warning("acl_get_denied_failed")
            return []

    async def _get_public_urns(self, user: UserContext) -> list[str]:
        if self._session is None:
            return []
        try:
            result = await self._session.execute(
                select(EntityAclDB.entity_urn).where(EntityAclDB.is_public.is_(True))
            )
            return [row[0] for row in result.all()]
        except Exception:
            log.warning("acl_get_public_failed")
            return []

    async def _audit(
        self,
        user: UserContext,
        action: str,
        resource_urn: str,
        decision: str,
        reason: str = "",
    ) -> None:
        event = AuditEvent(
            id=uuid.uuid4().hex[:16],
            request_id=user.request_id,
            user_id=user.user_id,
            action=action,
            resource_urn=resource_urn,
            decision=decision,
            reason=reason,
        )
        log.info("auth_audit",
            request_id=event.request_id,
            user_id=event.user_id,
            action=event.action,
            resource=event.resource_urn,
            decision=event.decision,
            reason=event.reason,
        )
        if self._session is not None:
            await self._save_audit(event)

    async def _save_audit(self, event: AuditEvent) -> None:
        try:
            from database.models import AuditLog

            if self._session is None:
                return
            db_entry = AuditLog(
                request_id=event.request_id,
                user_id=event.user_id,
                action=event.action,
                resource_urn=event.resource_urn,
                decision=event.decision,
                reason=event.reason,
            )
            self._session.add(db_entry)
            await self._session.commit()
        except Exception:
            log.exception("audit_save_failed")
