"""Test /api/me endpoint."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth.jwt_provider import JWTIdentityProvider
from app.auth.models import UserContext
from app.main import app
from config.settings import settings

client = TestClient(app)


def _auth_headers(user: UserContext) -> dict[str, str]:
    provider = JWTIdentityProvider(secret_key=settings.JWT_SECRET_KEY)
    token = provider.create_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_me_endpoint():
    headers = _auth_headers(UserContext(user_id="local-developer", roles=["admin"]))
    with patch("config.settings.settings.ENABLE_DEV_ENDPOINTS", True):
        response = client.get("/api/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "local-developer"
        assert data["is_admin"] is True


def test_me_endpoint_disabled():
    headers = _auth_headers(UserContext(user_id="local-developer", roles=["admin"]))
    with patch("config.settings.settings.ENABLE_DEV_ENDPOINTS", False):
        response = client.get("/api/me", headers=headers)
        assert response.status_code == 200
