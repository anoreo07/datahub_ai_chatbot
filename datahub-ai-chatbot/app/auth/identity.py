from abc import ABC, abstractmethod

from app.auth.models import UserContext


class IdentityProvider(ABC):
    @abstractmethod
    async def authenticate(self, request: object) -> UserContext:
        ...

    @abstractmethod
    async def get_user(self, user_id: str) -> UserContext | None:
        ...


class MockIdentityProvider(IdentityProvider):
    async def authenticate(self, request: object) -> UserContext:
        return UserContext.developer()

    async def get_user(self, user_id: str) -> UserContext | None:
        if user_id == "local-developer":
            return UserContext.developer()
        if user_id == "anonymous":
            return UserContext.anonymous()
        return None


class HeaderIdentityProvider(IdentityProvider):
    HEADER_USER_ID = "X-User-Id"
    HEADER_EMAIL = "X-User-Email"
    HEADER_GROUPS = "X-User-Groups"
    HEADER_ROLES = "X-User-Roles"

    async def authenticate(self, request: object) -> UserContext:
        from fastapi import Request

        if not isinstance(request, Request):
            return UserContext.anonymous()

        user_id = request.headers.get(self.HEADER_USER_ID, "anonymous")
        email = request.headers.get(self.HEADER_EMAIL, "")
        groups_str = request.headers.get(self.HEADER_GROUPS, "")
        roles_str = request.headers.get(self.HEADER_ROLES, "")

        groups = [g.strip() for g in groups_str.split(",") if g.strip()]
        roles = [r.strip() for r in roles_str.split(",") if r.strip()]

        return UserContext(
            user_id=user_id,
            email=email,
            display_name=user_id,
            groups=groups,
            roles=roles,
            is_admin="admin" in roles,
        )

    async def get_user(self, user_id: str) -> UserContext | None:
        return UserContext(user_id=user_id, display_name=user_id)
