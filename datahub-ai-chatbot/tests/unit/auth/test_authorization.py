"""Test authorization service with ACL rules."""
import pytest

from app.auth.authorization import AuthorizationService
from app.auth.models import EntityAcl, UserContext


@pytest.fixture
def admin_user() -> UserContext:
    return UserContext(
        user_id="admin",
        roles=["admin"],
        is_admin=True,
    )


@pytest.fixture
def regular_user() -> UserContext:
    return UserContext(
        user_id="user_a",
        email="user_a@company.com",
        groups=["team_analytics"],
        roles=["viewer"],
    )


@pytest.fixture
def other_user() -> UserContext:
    return UserContext(
        user_id="user_b",
        email="user_b@company.com",
        groups=["team_engineering"],
    )


@pytest.fixture
def auth_service() -> AuthorizationService:
    return AuthorizationService()


def test_admin_can_view_anything(admin_user: UserContext, auth_service: AuthorizationService) -> None:
    import asyncio
    assert asyncio.run(auth_service.can_view_entity(admin_user, "urn:li:dataset:secret"))


def test_user_allowed_directly(regular_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        allowed_user_ids=["user_a"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert asyncio.run(auth_service.can_view_entity(regular_user, acl.entity_urn))


def test_user_denied_directly(regular_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        denied_user_ids=["user_a"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert not asyncio.run(auth_service.can_view_entity(regular_user, acl.entity_urn))


def test_group_allowed(regular_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        allowed_groups=["team_analytics"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert asyncio.run(auth_service.can_view_entity(regular_user, acl.entity_urn))


def test_group_denied(regular_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        denied_groups=["team_analytics"],
        allowed_user_ids=["user_a"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert not asyncio.run(auth_service.can_view_entity(regular_user, acl.entity_urn))


def test_tenant_mismatch_denied(auth_service: AuthorizationService) -> None:
    user = UserContext(user_id="user", tenant_id="tenant_a")
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        tenant_id="tenant_b",
        allowed_user_ids=["user"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert not asyncio.run(auth_service.can_view_entity(user, acl.entity_urn))


def test_public_entity_allowed(other_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        is_public=True,
    )
    auth_service.set_acl(acl)
    import asyncio
    assert asyncio.run(auth_service.can_view_entity(other_user, acl.entity_urn))


def test_private_entity_no_acl_is_allowed(auth_service: AuthorizationService) -> None:
    """If no ACL is set, access is allowed (default open)."""
    import asyncio
    user = UserContext(user_id="some_user")
    assert asyncio.run(auth_service.can_view_entity(user, "urn:li:dataset:no_acl"))


def test_user_allowed_by_email(regular_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:test",
        allowed_emails=["user_a@company.com"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert asyncio.run(auth_service.can_view_entity(regular_user, acl.entity_urn))


def test_admin_bypasses_even_deny(admin_user: UserContext, auth_service: AuthorizationService) -> None:
    acl = EntityAcl(
        entity_urn="urn:li:dataset:secret",
        denied_user_ids=["admin"],
    )
    auth_service.set_acl(acl)
    import asyncio
    assert asyncio.run(auth_service.can_view_entity(admin_user, acl.entity_urn))


def test_filter_entities_removes_denied(regular_user: UserContext, auth_service: AuthorizationService) -> None:
    from unittest.mock import MagicMock

    acl_denied = EntityAcl(
        entity_urn="urn:li:dataset:denied",
        denied_user_ids=["user_a"],
    )
    acl_allowed = EntityAcl(
        entity_urn="urn:li:dataset:allowed",
        allowed_user_ids=["user_a"],
    )
    auth_service.set_acl(acl_denied)
    auth_service.set_acl(acl_allowed)

    e1 = MagicMock()
    e1.urn = "urn:li:dataset:denied"
    e2 = MagicMock()
    e2.urn = "urn:li:dataset:allowed"

    import asyncio
    filtered = asyncio.run(auth_service.filter_entities(regular_user, [e1, e2]))
    assert len(filtered) == 1
    assert filtered[0].urn == "urn:li:dataset:allowed"
