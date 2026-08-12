import pytest

from ingestion.sync import SyncOrchestrator
from retrieval.thinking import ThinkingModeOrchestrator


async def _seed(db_session) -> None:
    orchestrator = SyncOrchestrator(db_session)
    await orchestrator.run_full_sync()


@pytest.mark.asyncio
async def test_thinking_comparison_two_datasets(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "so sánh sales.orders và raw.payments có gì khác nhau?",
        entity_mentions=["sales.orders", "raw.payments"],
    )
    assert answer is not None
    assert "sales.orders" in answer
    assert "raw.payments" in answer


@pytest.mark.asyncio
async def test_thinking_if_delete_impact(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "nếu tôi xóa sales.orders thì ảnh hưởng gì?",
        entity_mentions=["sales.orders"],
    )
    assert answer is not None
    assert "finance.monthly_revenue" in answer


@pytest.mark.asyncio
async def test_thinking_cross_reference_term_domain_dataset(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "glossary term Revenue liên quan đến dataset nào trong domain Finance?",
        entity_mentions=["Revenue", "Finance"],
    )
    assert answer is not None


@pytest.mark.asyncio
async def test_thinking_schema_join_key(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "sale_orders có field nào là join key giữa sales.orders và raw.payments?",
        entity_mentions=["sales.orders", "raw.payments"],
    )
    assert answer is not None


@pytest.mark.asyncio
async def test_thinking_ownerless_quality_usage(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "dataset nào vừa thiếu owner vừa chất lượng kém và ít được dùng?",
        entity_mentions=[],
    )
    # honest gap reporting is acceptable behaviour
    assert answer is not None


@pytest.mark.asyncio
async def test_thinking_system_overview(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "tổng quan hệ thống gồm những dataset, dashboard và glossary term nào?",
        entity_mentions=[],
    )
    assert answer is not None
    assert "dataset" in answer.lower()


@pytest.mark.asyncio
async def test_simple_question_returns_none(db_session) -> None:
    await _seed(db_session)
    orch = ThinkingModeOrchestrator(db_session)
    answer = await orch.maybe_answer(
        "chủ sở hữu của sales.orders là ai?",
        entity_mentions=["sales.orders"],
    )
    assert answer is None


@pytest.mark.asyncio
async def test_chat_service_wire_complex_uses_thinking(db_session) -> None:
    """End-to-end: the gate in ChatService.answer() must route a complex
    question that falls through to the generic intent through the thinking mode,
    and keep dedicated flows (IMPACT, TERM_TO_DATASETS...) on their handlers."""
    from app.services.chat_service import ChatService
    await _seed(db_session)
    service = ChatService(db_session)

    response = await service.answer(
        "so sánh sales.orders và raw.payments khác nhau thế nào?"
    )
    assert isinstance(response.answer, str) and response.answer
    assert response.intent == "THINKING_OVERVIEW"


@pytest.mark.asyncio
async def test_chat_service_wire_simple_falls_through(db_session) -> None:
    from app.services.chat_service import ChatService
    await _seed(db_session)
    service = ChatService(db_session)

    response = await service.answer("owner của sales.orders là ai?")
    assert isinstance(response.answer, str) and response.answer
    assert response.intent != "THINKING_OVERVIEW"


@pytest.mark.asyncio
async def test_chat_service_wire_dedicated_impact_kept(db_session) -> None:
    """Questions already handled by a dedicated flow (IMPACT) must NOT be
    hijacked by the thinking layer."""
    from app.services.chat_service import ChatService
    await _seed(db_session)
    service = ChatService(db_session)

    response = await service.answer(
        "Nếu thay đổi dataset sales.orders thì những ai bị ảnh hưởng?"
    )
    assert isinstance(response.answer, str) and response.answer
    assert response.intent != "THINKING_OVERVIEW"
