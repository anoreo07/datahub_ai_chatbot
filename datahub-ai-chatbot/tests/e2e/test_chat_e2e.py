import os

import pytest

from app.schemas.chat import ChatResponse

os.environ["LLM_PROVIDER"] = "fireworks"
os.environ["FIREWORKS_API_KEY"] = ""


@pytest.mark.asyncio
async def test_chat_term_definition(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Term Revenue nghĩa là gì?")
    assert isinstance(response, ChatResponse)
    assert response.intent == "TERM_DEFINITION"
    assert response.answer
    assert "không tìm thấy" not in response.answer.lower()
    assert not response.insufficient_context


@pytest.mark.asyncio
async def test_term_to_datasets(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Dataset nào gắn term Customer?")
    assert response.intent == "TERM_TO_DATASETS"
    assert len(response.entities) >= 1
    urns = [e.urn for e in response.entities]
    assert any("sales.orders" in u for u in urns)


@pytest.mark.asyncio
async def test_owner_lookup(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Ai sở hữu dataset sales.orders?")
    assert response.intent == "OWNER_LOOKUP"
    assert response.answer
    assert "Sales Analytics" in response.answer or "không tìm thấy" not in response.answer.lower()


@pytest.mark.asyncio
async def test_entity_not_found(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Dataset abc.xyz có tồn tại không?")
    assert response.intent == "ENTITY_EXISTS"
    assert not response.insufficient_context or "không" in response.answer.lower()


@pytest.mark.asyncio
async def test_datahub_url(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Cho tôi link DataHub của dataset sales.orders.")
    assert response.intent == "DATAHUB_URL"
    assert response.answer
    assert "localhost:9002" in response.answer or "không" in response.answer.lower()


@pytest.mark.asyncio
async def test_schema_lookup(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Dataset sales.orders có những field nào?")
    assert response.intent == "SCHEMA_LOOKUP"
    assert response.answer
    assert not response.insufficient_context


@pytest.mark.asyncio
async def test_lineage(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Dataset finance.monthly_revenue lấy dữ liệu từ đâu?")
    assert response.intent == "LINEAGE"
    assert response.answer


@pytest.mark.asyncio
async def test_no_hallucination_for_nonexistent(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Dataset does.not.exist có tồn tại không?")
    assert response.intent == "ENTITY_EXISTS"
    answer_lower = response.answer.lower()
    assert "không" in answer_lower or "không tìm thấy" in answer_lower


@pytest.mark.asyncio
async def test_owner_lookup_alternate_phrasing(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("dataset sales.orders thuộc về ai?")
    assert response.intent == "OWNER_LOOKUP"
    assert "Sales Analytics" in response.answer


@pytest.mark.asyncio
async def test_owner_lookup_typo_resolution(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("Ai sở hữu duathet sales.orders?")
    assert response.intent == "OWNER_LOOKUP"
    assert "Sales Analytics" in response.answer


@pytest.mark.asyncio
async def test_entity_domain_membership(db_session) -> None:
    from app.services.chat_service import ChatService
    from ingestion.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()

    service = ChatService(db_session)

    response = await service.answer("dataset sales.orders thuộc về domain nào?")
    assert response.intent == "ENTITY_DOMAIN"
    assert "Sales" in response.answer
