"""Test the data-driven domain RBAC service."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserContext
from app.auth.rbac import RbacService
from database.repositories.rbac_repository import RbacRepository

pytestmark = pytest.mark.asyncio


async def _seed(db: AsyncSession) -> None:
    repo = RbacRepository(db)
    finance = await repo.create_role("Tài chính", group_names=["finance-team"])
    logistics = await repo.create_role("Logistics", group_names=["logistics-team"])
    await repo.set_role_domains(finance.id, ["TÀI CHÍNH", "Finance"])
    await repo.set_role_domains(logistics.id, ["Logistics", "CUNG ỨNG"])
    await repo.upsert_user("user_fin", "fin@corp.com", "Finance User")
    await repo.upsert_user("user_log", "log@corp.com", "Logistics User")
    await repo.upsert_user("user_none", "none@corp.com", "No Role User")
    await repo.set_user_roles("user_fin", [finance.id])
    await repo.set_user_roles("user_log", [logistics.id])


def _u(user_id: str, groups: list[str] | None = None, is_admin: bool = False) -> UserContext:
    return UserContext(user_id=user_id, groups=groups or [], is_admin=is_admin)


async def test_finance_user_cannot_access_logistics(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    assert await svc.can_access_domain(_u("user_fin"), "Logistics") is False
    assert await svc.can_access_domain(_u("user_fin"), "TÀI CHÍNH") is True


async def test_access_message_exact_requirement(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    msg = await svc.access_message(_u("user_fin"), "Logistics")
    assert msg == "Bạn không có quyền truy cập dữ liệu thuộc lĩnh vực Logistics."


async def test_accent_insensitive_matching(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    assert await svc.can_access_domain(_u("user_log"), "Cung Ung") is True
    assert await svc.can_access_domain(_u("user_log"), "Logistic") is True
    assert await svc.can_access_domain(_u("user_fin"), "tài chính") is True


async def test_user_with_no_roles_denied(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    assert await svc.can_access_domain(_u("user_none"), "TÀI CHÍNH") is False
    assert await svc.can_access_domain(_u("user_none"), "Logistics") is False


async def test_admin_access_everything(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    assert await svc.can_access_domain(_u("admin", is_admin=True), "Logistics") is True
    assert await svc.allowed_domains(_u("admin", is_admin=True)) == {"*"}


async def test_role_domain_update_takes_effect_without_restart(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    assert await svc.can_access_domain(_u("user_log"), "Sales") is False
    repo = RbacRepository(db_session)
    roles = await repo.list_roles()
    logistics = next(r for r in roles if r.name == "Logistics")
    await repo.set_role_domains(logistics.id, ["Sales"])
    await svc.refresh()
    assert await svc.can_access_domain(_u("user_log"), "Sales") is True
    assert await svc.can_access_domain(_u("user_log"), "Logistics") is False


async def test_group_fallback(db_session: AsyncSession) -> None:
    await _seed(db_session)
    svc = RbacService(db_session)
    assert await svc.can_access_domain(_u("ghost", groups=["finance-team"]), "TÀI CHÍNH") is True
    assert await svc.can_access_domain(_u("ghost", groups=["finance-team"]), "Logistics") is False


async def test_domain_utils() -> None:
    from app.auth.domain_utils import domains_match, norm_vn
    assert norm_vn("TÀI CHÍNH") == "tai chinh"
    assert domains_match("Logistics", "logistic") is True
    assert domains_match("Finance", "Logistics") is False
