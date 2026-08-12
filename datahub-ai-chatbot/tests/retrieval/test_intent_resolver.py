import pytest

from retrieval.intent_resolver import KNOWN_ACTIONS, IntentResolver

HISTORY = [
    ("Impact analysis cho dataset dim_warehouse", "..."),
    ("schema của dim_warehouse là gì", "..."),
]


def _resolve(message, action=None, history=None):
    resolver = IntentResolver(llm=None)
    return resolver.resolve(message, selected_action=action, history=history, trace_id="test")


@pytest.mark.asyncio
async def test_bare_entity_frames_action_intent() -> None:
    res = await _resolve("sales_order", action="impact", history=HISTORY)
    assert res.decision == "agree"
    assert res.intent.value == "IMPACT"
    assert res.framed is True
    assert res.entity_hint == "sales_order"
    assert res.effective_question.startswith("Impact analysis cho dataset")


@pytest.mark.asyncio
async def test_bare_entity_lineage() -> None:
    res = await _resolve("sales_order", action="lineage", history=HISTORY)
    assert res.decision == "agree"
    assert res.intent.value == "LINEAGE"
    assert res.framed is True


@pytest.mark.asyncio
async def test_explicit_conflicting_intent_overrides_action() -> None:
    res = await _resolve("sales_order có bao nhiêu cột?", action="impact", history=HISTORY)
    assert res.decision == "override"
    assert res.intent.value == "SCHEMA_LOOKUP"
    assert res.framed is False
    assert res.effective_question == "sales_order có bao nhiêu cột?"
    assert res.override_reason is not None


@pytest.mark.asyncio
async def test_greeting_overrides_action() -> None:
    res = await _resolve("hello", action="impact", history=HISTORY)
    assert res.decision == "override"
    assert res.intent.value == "GREETING"


@pytest.mark.asyncio
async def test_listing_agrees_with_search_action() -> None:
    res = await _resolve("liệt kê các dataset", action="search", history=HISTORY)
    assert res.decision == "agree"
    assert res.intent.value == "LISTING"
    assert res.chosen_tool == "list_by_type"


@pytest.mark.asyncio
async def test_bare_verbs_clarify() -> None:
    res = await _resolve("đánh giá chất lượng", action="impact", history=HISTORY)
    assert res.decision == "clarify"
    assert res.confidence == "low"
    assert res.clarification is not None


@pytest.mark.asyncio
async def test_no_action_without_selection() -> None:
    res = await _resolve("sales_order", action=None, history=None)
    assert res.decision == "no_action"
    assert res.effective_question == "sales_order"


@pytest.mark.asyncio
async def test_known_actions() -> None:
    assert KNOWN_ACTIONS == {"search", "sql", "impact", "lineage", "quality", "report"}
