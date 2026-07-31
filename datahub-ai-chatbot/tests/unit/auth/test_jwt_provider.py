"""Test JWT identity provider."""
from unittest.mock import MagicMock

import pytest

from app.auth.jwt_provider import JWTIdentityProvider
from app.auth.models import UserContext


@pytest.fixture
def provider() -> JWTIdentityProvider:
    return JWTIdentityProvider(secret_key="test-secret-key-32-bytes-long!!!!")


@pytest.mark.asyncio
async def test_jwt_authenticate_no_header(provider: JWTIdentityProvider):
    user = await provider.authenticate(None)
    assert user.user_id == "anonymous"


@pytest.mark.asyncio
async def test_jwt_authenticate_invalid_token(provider: JWTIdentityProvider):
    mock_request = MagicMock(spec=["headers"])
    mock_request.headers = {"Authorization": "Bearer invalid-token"}

    user = await provider.authenticate(mock_request)
    assert user.user_id == "anonymous"


@pytest.mark.asyncio
async def test_jwt_create_and_decode(provider: JWTIdentityProvider):
    original = UserContext(
        user_id="test-user",
        email="test@company.com",
        display_name="Test User",
        groups=["team_analytics"],
        roles=["viewer"],
    )
    token = provider.create_token(original)
    assert isinstance(token, str)

    mock_request = MagicMock(spec=["headers"])
    mock_request.headers = {"Authorization": f"Bearer {token}"}

    decoded = await provider.authenticate(mock_request)
    assert decoded.user_id == "test-user"
    assert decoded.email == "test@company.com"
    assert "team_analytics" in decoded.groups


@pytest.mark.asyncio
async def test_jwt_admin_role(provider: JWTIdentityProvider):
    original = UserContext(
        user_id="admin-user",
        roles=["admin"],
        is_admin=True,
    )
    token = provider.create_token(original)

    mock_request = MagicMock(spec=["headers"])
    mock_request.headers = {"Authorization": f"Bearer {token}"}

    decoded = await provider.authenticate(mock_request)
    assert decoded.is_admin


@pytest.mark.asyncio
async def test_jwt_get_user(provider: JWTIdentityProvider):
    user = await provider.get_user("test")
    assert user is not None
    assert user.user_id == "test"
