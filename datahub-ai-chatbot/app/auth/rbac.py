import time
import unicodedata

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserContext
from database.repositories.rbac_repository import RbacRepository

log = structlog.get_logger()

# Cache validity window for the domain-permission snapshot.
_RBAC_CACHE_TTL_SECONDS = 5


def _norm_vn(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


class RbacService:
    """Data-driven domain RBAC evaluation.

    Permission evaluation reads roles and their granted domains from the
    database and caches a normalized snapshot for a short window. When an
    administrator updates a role/domain/user assignment, ``refresh()`` is
    invoked so the next evaluation uses the fresh snapshot immediately — no
    application restart required.

    Semantics:
    - ``is_admin`` users (or users holding an admin role) can access everything.
    - Every other user is allowed exactly the union of domains granted to the
      roles they hold (either via direct user-role assignment or via the
      role's ``group_names`` fallback for users that carry LDAP-style groups).
    - A user with **no** role grants is restricted to nothing (deny-by-default
      for domains), which is the safe default.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._repo: RbacRepository | None = None
        # snapshot_version is bumped on every refresh; the cache stores the
        # version it was built from so stale in-flight snapshots are rebuilt.
        self._snapshot_version = 0
        self._cached_version = -1
        self._cache: dict[str, object] = {}
        self._cache_ts = 0.0

    def _get_repo(self) -> RbacRepository | None:
        if self._session is None:
            return None
        if self._repo is None:
            self._repo = RbacRepository(self._session)
        return self._repo

    async def refresh(self) -> None:
        """Force reload of the role/domain snapshot from the database."""
        self._snapshot_version += 1
        self._cache.clear()
        self._cached_version = -1
        repo = self._get_repo()
        if repo is None:
            return
        try:
            roles = await repo.list_roles()
            snapshot: dict[str, object] = {}
            admin_role_ids: list[int] = []
            for role in roles:
                domains = await repo.list_role_domains(role.id)
                entry = {
                    "id": role.id,
                    "name": role.name,
                    "is_admin": bool(role.is_admin),
                    "group_names": list(role.group_names or []),
                    "domains": domains,
                }
                snapshot[str(role.id)] = entry
                if role.is_admin:
                    admin_role_ids.append(role.id)
            snapshot["_admin_roles"] = admin_role_ids
            self._cache = snapshot
            self._cached_version = self._snapshot_version
            log.info("rbac_cache_refreshed",
                     roles=len(roles), version=self._snapshot_version)
        except Exception:  # noqa: BLE001
            log.exception("rbac_cache_refresh_failed")

    async def _ensure_cache(self) -> None:
        repo = self._get_repo()
        if repo is None:
            return
        if self._cached_version == self._snapshot_version:
            # Cache is current w.r.t. the last explicit refresh, but may still
            # be stale w.r.t. time — self-heal so long-lived instances pick up
            # admin changes without a restart.
            if self._cache and time.monotonic() - self._cache_ts <= _RBAC_CACHE_TTL_SECONDS:
                return
        await self.refresh()
        self._cache_ts = time.monotonic()

    async def _user_role_snapshot(self, user: UserContext) -> list[dict[str, object]]:
        """Resolve the roles a user holds, from the cached role snapshot."""
        repo = self._get_repo()
        await self._ensure_cache()
        roles: list[dict[str, object]] = []
        if repo is None or not self._cache:
            return roles

        user_role_ids = await repo.list_user_role_ids(user.user_id)
        user_groups = {_norm_vn(g) for g in (user.groups or [])}
        for role_id, entry in self._cache.items():
            if role_id == "_admin_roles":
                continue
            if not isinstance(entry, dict):
                continue
            if int(entry["id"]) in user_role_ids:
                roles.append(entry)
                continue
            raw_groups = entry.get("group_names") or []
            if not isinstance(raw_groups, list):
                continue
            group_names = {_norm_vn(g) for g in raw_groups if isinstance(g, str)}
            if group_names and user_groups.intersection(group_names):
                roles.append(entry)
        return roles

    async def _user_admin_roles(self, user: UserContext) -> list[int]:
        repo = self._get_repo()
        if repo is None:
            return []
        await self._ensure_cache()
        admin_ids = self._cache.get("_admin_roles", [])
        if isinstance(admin_ids, list):
            return list(admin_ids)
        return []

    async def is_admin_role(self, user: UserContext) -> bool:
        if user.is_admin:
            return True
        repo = self._get_repo()
        if repo is None:
            return False
        admin_ids = await self._user_admin_roles(user)
        if not admin_ids:
            return False
        user_role_ids = await repo.list_user_role_ids(user.user_id)
        return any(rid in user_role_ids for rid in admin_ids)

    async def allowed_domains(self, user: UserContext) -> set[str]:
        """Normalized set of domains the user may access. Admin = wildcard sentinel.

        Returns ``{"*"}`` for administrators. Normalization strips accents/case
        so "TÀI CHÍNH", "Tài Chính" and "tai chinh" compare equal.
        """
        if user.is_admin or await self.is_admin_role(user):
            return {"*"}
        roles = await self._user_role_snapshot(user)
        domains: set[str] = set()
        for role in roles:
            raw = role.get("domains")
            if not isinstance(raw, list):
                continue
            for d in raw:
                if not isinstance(d, str):
                    continue
                normalized = _norm_vn(d)
                if normalized:
                    domains.add(normalized)
        return domains

    async def can_access_domain(self, user: UserContext, domain: str | None) -> bool:
        """Whether ``user`` may access an entity belonging to ``domain``."""
        if not domain or not domain.strip():
            return True
        allowed = await self.allowed_domains(user)
        if "*" in allowed:
            return True
        target = _norm_vn(domain)
        if not target:
            return True
        if target in allowed:
            return True
        # Substring agreement: "LOGISTIC" in "LOGISTIC (TT)" etc.
        for a in allowed:
            if a in target or target in a:
                return True
        return False

    async def can_access_any(self, user: UserContext, domains: list[str | None]) -> bool:
        if "*" in await self.allowed_domains(user):
            return True
        for d in domains:
            if await self.can_access_domain(user, d):
                return True
        return False

    async def access_message(self, user: UserContext, domain: str | None) -> str | None:
        """Return a localized authorization message if the domain is off-limits."""
        if await self.can_access_domain(user, domain):
            return None
        label = (domain or "").strip()
        return (
            f"Bạn không có quyền truy cập dữ liệu thuộc lĩnh vực {label}."
        )

    async def refresh_if_stale(self, force: bool = False) -> None:
        repo = self._get_repo()
        if repo is None:
            return
        now = time.monotonic()
        if force or now - self._cache_ts > _RBAC_CACHE_TTL_SECONDS:
            await self.refresh()
            self._cache_ts = now
