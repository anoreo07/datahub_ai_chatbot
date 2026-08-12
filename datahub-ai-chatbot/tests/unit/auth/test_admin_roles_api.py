"""API tests for the admin role-management module (data-driven RBAC)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.models import UserContext
from app.main import app

_ASYNC_CLIENT: AsyncClient | None = None


async def _client() -> AsyncClient:
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is None:
        transport = ASGITransport(app=app)
        _ASYNC_CLIENT = AsyncClient(transport=transport, base_url="http://test")
    return _ASYNC_CLIENT


@pytest.mark.asyncio
async def test_roles_crud_flow(db_session) -> None:
    from app.api.dependencies.auth import get_current_user
    from database.session import get_session

    async def _current_user():
        return UserContext(user_id="admin", is_admin=True)

    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    app.dependency_overrides[get_current_user] = _current_user

    c = await _client()
    try:
        resp = await c.post(
            "/api/v1/admin/roles",
            json={"name": "Kinh Doanh R", "domains": ["KINH DOANH"]},
        )
        assert resp.status_code == 201, resp.text
        role = resp.json()
        assert role["domains"] == ["KINH DOANH"]
        rid = role["id"]

        resp = await c.get("/api/v1/admin/roles")
        assert resp.status_code == 200
        assert any(r["id"] == rid for r in resp.json())

        resp = await c.put(
            f"/api/v1/admin/roles/{rid}/domains",
            json={"domains": ["Sales", "HẬU MÃI"]},
        )
        assert resp.status_code == 200
        assert sorted(resp.json()["domains"]) == sorted(["Sales", "HẬU MÃI"])

        resp = await c.post(
            "/api/v1/admin/users",
            json={"user_id": "warehouse", "username": "warehouse", "role_ids": [rid]},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["role_ids"] == [rid]

        resp = await c.delete(f"/api/v1/admin/roles/{rid}")
        assert resp.status_code == 204

        resp = await c.get("/api/v1/admin/roles")
        assert all(r["id"] != rid for r in resp.json())
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permission_cache_refreshes_after_role_change(db_session) -> None:
    """Admin updates a role's domains -> RbacService reflects it immediately."""
    from app.api.dependencies.auth import get_current_user
    from app.auth.authorization import AuthorizationService
    from database.session import get_session

    async def _current_user():
        return UserContext(user_id="admin", is_admin=True)

    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    app.dependency_overrides[get_current_user] = _current_user

    c = await _client()
    try:
        resp = await c.post(
            "/api/v1/admin/roles",
            json={"name": "TempRole", "domains": ["Sales"]},
        )
        assert resp.status_code == 201
        rid = resp.json()["id"]

        await c.post(
            "/api/v1/admin/users",
            json={"user_id": "tempuser", "username": "tempuser", "role_ids": [rid]},
        )

        auth = AuthorizationService(session=db_session)
        user = UserContext(user_id="tempuser")
        assert await auth.can_access_domain(user, "Sales") is True
        assert await auth.can_access_domain(user, "LOGISTIC") is False

        # Admin grants LOGISTIC to the role. Each request builds a fresh
        # AuthorizationService, so the next evaluation reads the new grant —
        # no restart required.
        await c.put(
            f"/api/v1/admin/roles/{rid}/domains",
            json={"domains": ["LOGISTIC"]},
        )
        fresh = AuthorizationService(session=db_session)
        assert await fresh.can_access_domain(user, "LOGISTIC") is True
        assert await fresh.can_access_domain(user, "Sales") is False
    finally:
        app.dependency_overrides.clear()
