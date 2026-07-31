"""Test identity providers."""
import pytest

from app.auth.identity import HeaderIdentityProvider, MockIdentityProvider


@pytest.mark.asyncio
async def test_mock_identity_returns_developer():
    provider = MockIdentityProvider()
    user = await provider.authenticate(None)
    assert user.user_id == "local-developer"
    assert user.is_admin


@pytest.mark.asyncio
async def test_mock_get_user_developer():
    provider = MockIdentityProvider()
    user = await provider.get_user("local-developer")
    assert user is not None
    assert user.is_admin


@pytest.mark.asyncio
async def test_mock_get_user_anonymous():
    provider = MockIdentityProvider()
    user = await provider.get_user("anonymous")
    assert user is not None
    assert user.user_id == "anonymous"


@pytest.mark.asyncio
async def test_mock_get_user_unknown():
    provider = MockIdentityProvider()
    user = await provider.get_user("unknown")
    assert user is None


@pytest.mark.asyncio
async def test_header_identity_empty_request():
    provider = HeaderIdentityProvider()
    user = await provider.authenticate(None)
    assert user.user_id == "anonymous"


@pytest.mark.asyncio
async def test_header_provider_get_user():
    provider = HeaderIdentityProvider()
    user = await provider.get_user("test-user")
    assert user is not None
    assert user.user_id == "test-user"
