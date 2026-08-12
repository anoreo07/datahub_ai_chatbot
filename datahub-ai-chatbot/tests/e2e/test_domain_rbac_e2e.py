"""E2E tests for domain RBAC gating through the ChatService pipeline."""
import pytest

from app.auth.models import UserContext
from app.schemas.chat import ChatResponse


async def _finance_user() -> UserContext:
    return UserContext(
        user_id="finance",
        email="finance@company.example",
        groups=["finance-team"],
        roles=["viewer"],
        is_admin=False,
    )


async def _admin_user() -> UserContext:
    return UserContext(user_id="admin", roles=["admin"], is_admin=True)


async def _seed_rbac(db_session) -> None:
    from database.repositories.rbac_repository import RbacRepository

    repo = RbacRepository(db_session)
    finance = await repo.create_role("Tài chính", group_names=["finance-team"])
    logistics = await repo.create_role("Logistics", group_names=["logistics-team"])
    await repo.set_role_domains(finance.id, ["TÀI CHÍNH", "Finance"])
    await repo.set_role_domains(logistics.id, ["Logistics", "LOGISTIC"])


@pytest.mark.asyncio
async def test_finance_user_denied_logistics_domain(db_session) -> None:
    from app.auth.authorization import AuthorizationService
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()
    await _seed_rbac(db_session)

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "Danh sách dataset thuộc domain Logistics.",
        user=await _finance_user(),
    )
    assert "bạn không có quyền truy cập dữ liệu thuộc lĩnh vực" in response.answer.lower()
    assert "0 dataset" not in response.answer.lower()


@pytest.mark.asyncio
async def test_admin_can_access_logistics_domain(db_session) -> None:
    from app.auth.authorization import AuthorizationService
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()
    await _seed_rbac(db_session)

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "Danh sách dataset thuộc domain Logistics.",
        user=await _admin_user(),
    )
    assert "Bạn không có quyền truy cập" not in response.answer


@pytest.mark.asyncio
async def test_finance_user_allowed_finance_domain(db_session) -> None:
    from app.auth.authorization import AuthorizationService
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()
    await _seed_rbac(db_session)

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "Danh sách dataset thuộc domain Tài chính.",
        user=await _finance_user(),
    )
    assert "Bạn không có quyền truy cập" not in response.answer


@pytest.mark.asyncio
async def test_finance_user_denied_logistics_entity(db_session) -> None:
    """Entity-level query (no domain named) must still be denied.

    Regression for the bug where a user whose role cannot access a domain
    silently received "0 datasets"/"Không tìm thấy" for a specific entity that
    belongs to an off-limits domain, instead of an authorization message.
    """
    from app.auth.authorization import AuthorizationService
    from app.services.chat_service import ChatService
    from database.models import Entity
    from database.repositories.entity_repository import EntityRepository

    await _seed_rbac(db_session)
    repo = EntityRepository(db_session)
    await repo.upsert(Entity(
        urn="urn:li:dataset:logistic_shipment",
        entity_type="dataset",
        name="logistic_shipment",
        display_name="logistic_shipment",
        domain="LOGISTIC",
    ))

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "logistic_shipment có bao nhiêu cột?",
        user=await _finance_user(),
    )
    assert "bạn không có quyền truy cập dữ liệu thuộc lĩnh vực" in response.answer.lower()
    assert "0 dataset" not in response.answer.lower()
    assert "không tìm thấy" not in response.answer.lower()
    assert "logistic_shipment có bao nhiêu cột" not in response.answer.lower()


@pytest.mark.asyncio
async def test_finance_user_allowed_finance_entity(db_session) -> None:
    """A finance user querying an entity in their own domain must not be blocked."""
    from app.auth.authorization import AuthorizationService
    from app.services.chat_service import ChatService
    from database.models import Entity
    from database.repositories.entity_repository import EntityRepository

    await _seed_rbac(db_session)
    repo = EntityRepository(db_session)
    await repo.upsert(Entity(
        urn="urn:li:dataset:cost_center", entity_type="dataset",
        name="cost_center", display_name="cost_center", domain="TÀI CHÍNH",
        payload={"schema_fields": [{"name": "id", "type": "int"}]},
    ))

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "cost_center có bao nhiêu cột?",
        user=await _finance_user(),
    )
    assert "bạn không có quyền truy cập" not in response.answer.lower()
