"""Integration tests for ACL filter builders (AGENTS.md critical #4).

These exercise ``build_database_acl_filter`` / ``build_opensearch_acl_filter``
against the real Postgres ARRAY columns, which cannot run on aiosqlite.
"""
import pytest

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.models import Entity, EntityAclDB


@pytest.fixture
def admin_user() -> UserContext:
    return UserContext(user_id="admin", roles=["admin"], is_admin=True)


@pytest.fixture
def viewer_user() -> UserContext:
    return UserContext(
        user_id="user_a",
        email="user_a@company.com",
        groups=["team_analytics"],
        roles=["viewer"],
    )


async def _seed_acls(session, *acls: EntityAclDB) -> None:
    for acl in acls:
        session.add(acl)
    await session.commit()


async def _seed_entities(session, urns: list[str]) -> None:
    for urn in urns:
        session.add(Entity(urn=urn, entity_type="dataset", name=urn, content_hash="h1"))
    await session.commit()


async def test_db_filter_admin_returns_none(db_session, admin_user) -> None:
    service = AuthorizationService(session=db_session)
    assert await service.build_database_acl_filter(admin_user) is None


async def test_db_filter_non_admin_denied(db_session, viewer_user) -> None:
    urn = "urn:li:dataset:finance.secret"
    await _seed_entities(db_session, [urn])
    await _seed_acls(db_session, EntityAclDB(entity_urn=urn, denied_user_ids=["user_a"]))

    service = AuthorizationService(session=db_session)
    expr = await service.build_database_acl_filter(viewer_user)
    assert expr is not None


async def test_db_filter_accessible_includes(db_session, viewer_user) -> None:
    allowed_urn = "urn:li:dataset:allowed"
    denied_urn = "urn:li:dataset:denied"
    await _seed_entities(db_session, [allowed_urn, denied_urn])
    await _seed_acls(
        db_session,
        EntityAclDB(entity_urn=allowed_urn, allowed_user_ids=["user_a"]),
        EntityAclDB(entity_urn=denied_urn, denied_user_ids=["user_a"]),
    )

    service = AuthorizationService(session=db_session)
    expr = await service.build_database_acl_filter(viewer_user)

    from sqlalchemy import select

    result = await db_session.execute(select(Entity.urn).where(expr))
    urns = {row[0] for row in result.all()}
    assert allowed_urn in urns
    assert denied_urn not in urns


async def test_os_filter_admin_returns_none(db_session, admin_user) -> None:
    service = AuthorizationService(session=db_session)
    assert await service.build_opensearch_acl_filter(admin_user) is None


async def test_os_filter_public_only(db_session, viewer_user) -> None:
    public_urn = "urn:li:dataset:public"
    private_urn = "urn:li:dataset:private"
    await _seed_entities(db_session, [public_urn, private_urn])
    await _seed_acls(
        db_session,
        EntityAclDB(entity_urn=public_urn, is_public=True),
        EntityAclDB(entity_urn=private_urn, allowed_user_ids=["other_user"]),
    )

    service = AuthorizationService(session=db_session)
    query = await service.build_opensearch_acl_filter(viewer_user)
    assert query is not None
    assert "terms" in query
    assert query["terms"]["entity_urn"] == [public_urn]


async def test_os_filter_denied_excluded(db_session, viewer_user) -> None:
    denied_urn = "urn:li:dataset:secret"
    public_urn = "urn:li:dataset:open"
    await _seed_entities(db_session, [denied_urn, public_urn])
    await _seed_acls(
        db_session,
        EntityAclDB(entity_urn=denied_urn, denied_user_ids=["user_a"]),
        EntityAclDB(entity_urn=public_urn, is_public=True),
    )

    service = AuthorizationService(session=db_session)
    query = await service.build_opensearch_acl_filter(viewer_user)
    assert query is not None
    must = query["bool"]["must"]
    assert any("must_not" in clause["bool"] for clause in must)
    must_not = next(
        clause["bool"]["must_not"]["terms"]["entity_urn"]
        for clause in must
        if "must_not" in clause["bool"]
    )
    assert denied_urn in must_not
