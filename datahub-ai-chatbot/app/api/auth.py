from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth.jwt_provider import JWTIdentityProvider
from app.auth.models import UserContext
from config.settings import settings

router = APIRouter()

_HARDCODED_USERS = {
    "admin": {
        "password": "admin123",
        "user_id": "admin",
        "email": "admin@company.example",
        "display_name": "Admin",
        "groups": ["admin-group"],
        "roles": ["admin"],
        "is_admin": True,
    },
    "finance": {
        "password": "finance123",
        "user_id": "finance",
        "email": "finance@company.example",
        "display_name": "Finance User",
        "groups": ["finance-team"],
        "roles": ["viewer"],
        "is_admin": False,
    },
    "logistics": {
        "password": "logistics123",
        "user_id": "logistics",
        "email": "logistics@company.example",
        "display_name": "Logistics User",
        "groups": ["logistics-team"],
        "roles": ["viewer"],
        "is_admin": False,
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    display_name: str
    roles: list[str]
    is_admin: bool


@router.post("/login")
async def login(req: LoginRequest) -> LoginResponse:
    user_data = _HARDCODED_USERS.get(req.username)
    if not user_data or user_data["password"] != req.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    provider = JWTIdentityProvider(
        secret_key=settings.JWT_SECRET_KEY,
    )

    user = UserContext(
        user_id=user_data["user_id"],
        email=user_data["email"],
        display_name=user_data["display_name"],
        groups=user_data["groups"],
        roles=user_data["roles"],
        is_admin=user_data["is_admin"],
    )
    token = provider.create_token(user)

    return LoginResponse(
        token=token,
        user_id=user.user_id,
        display_name=user.display_name,
        roles=user.roles,
        is_admin=user.is_admin,
    )
