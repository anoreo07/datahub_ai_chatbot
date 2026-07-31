
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.identity import (
    HeaderIdentityProvider,
    IdentityProvider,
    MockIdentityProvider,
)
from app.auth.jwt_provider import JWTIdentityProvider
from app.auth.models import AuthMode, UserContext
from config.settings import settings
from database.session import get_session


def _create_identity_provider() -> IdentityProvider:
    mode = settings.AUTH_MODE
    if mode == AuthMode.JWT.value:
        return JWTIdentityProvider(
            secret_key=settings.JWT_SECRET_KEY,
        )
    if mode == AuthMode.HEADER.value:
        return HeaderIdentityProvider()
    return MockIdentityProvider()


identity_provider = _create_identity_provider()


async def get_current_user(request: Request) -> UserContext:
    user = await identity_provider.authenticate(request)
    if settings.AUTH_REQUIRED and user.user_id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


async def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthorizationService:
    return AuthorizationService(session=session)


async def get_admin_user(current_user: UserContext = Depends(get_current_user)) -> UserContext:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_role(*roles: str):
    async def _require_role(current_user: UserContext = Depends(get_current_user)) -> UserContext:
        if not any(r in current_user.roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return current_user
    return _require_role
