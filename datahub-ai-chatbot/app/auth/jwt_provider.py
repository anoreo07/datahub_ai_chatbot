from app.auth.identity import IdentityProvider
from app.auth.models import UserContext


class JWTIdentityProvider(IdentityProvider):
    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    async def authenticate(self, request: object) -> UserContext:
        from fastapi import Request

        auth_header = ""
        if isinstance(request, Request):
            auth_header = request.headers.get("Authorization", "")
        elif hasattr(request, "headers"):
            headers = request.headers
            if isinstance(headers, dict):
                auth_header = headers.get("Authorization", "")
            elif hasattr(headers, "get"):
                auth_header = headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return UserContext.anonymous()

        token = auth_header[7:]
        return self._decode_token(token)

    async def get_user(self, user_id: str) -> UserContext | None:
        return UserContext(user_id=user_id)

    def _decode_token(self, token: str) -> UserContext:
        import jwt as pyjwt

        try:
            payload = pyjwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            groups = payload.get("groups", []) or []
            roles = payload.get("roles", []) or []
            return UserContext(
                user_id=payload.get("sub", "anonymous"),
                email=payload.get("email", ""),
                display_name=payload.get("name", payload.get("sub", "")),
                groups=groups if isinstance(groups, list) else [],
                roles=roles if isinstance(roles, list) else [],
                is_admin="admin" in (roles if isinstance(roles, list) else []),
                tenant_id=payload.get("tenant_id"),
            )
        except Exception:
            return UserContext.anonymous()

    def create_token(self, user: UserContext) -> str:
        import datetime

        import jwt as pyjwt

        payload = {
            "sub": user.user_id,
            "email": user.email,
            "name": user.display_name,
            "groups": user.groups,
            "roles": user.roles,
            "tenant_id": user.tenant_id,
            "iat": datetime.datetime.now(datetime.UTC),
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24),
        }
        return pyjwt.encode(payload, self._secret_key, algorithm=self._algorithm)
