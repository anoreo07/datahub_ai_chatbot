"""Unit tests for the opt-in Query Understanding layer (retrieval/query_understanding.py).

Everything here tests behaviour with ``QU_ENABLED`` boundaries:

* when disabled (the default), ``understand_query`` returns ``None`` and the
  router behaviour is unchanged;
* the JSON parser sanitises LLM payloads (unknown property values dropped,
  field-property invariants enforced, low-confidence redundancy rejected).
"""

import asyncio

import pytest

from config.settings import settings
from retrieval.query_understanding import (
    UnderstandingResult,
    parse_understanding,
    understand_query,
)


def asyncio_run(coro):
    return asyncio.run(coro)


class _FakeLLM:
    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.calls: list[tuple[str, list, str]] = []

    async def generate(self, prompt: str, *, context=None, history=None,
                       system_prompt=None) -> str:
        self.calls.append((prompt, history or [], system_prompt or ""))
        return self._payload


FORMATTED_PAYLOAD = """{
  "focus_field": "quantity",
  "property": "data_type",
  "is_field_property_question": true,
  "needs_thinking": false,
  "needs_decomposition": false,
  "sub_questions": [],
  "anaphora_target": null,
  "entity_refs": [],
  "confidence": "high"
}"""


def test_parse_understanding_field_property() -> None:
    result = parse_understanding(FORMATTED_PAYLOAD)
    assert result is not None
    assert result.focus_field == "quantity"
    assert result.property == "data_type"
    assert result.is_field_property_question is True
    assert result.confidence == "high"
    assert result.source == "llm"


def test_parse_understanding_anaphora_and_decomposition() -> None:
    payload = """{
      "needs_decomposition": true,
      "sub_questions": ["dim_warehouse có những trường nào?", "dim_warehouse thuộc lĩnh vực nào?"],
      "anaphora_target": "fact_inventory_movement",
      "entity_refs": [],
      "needs_thinking": false,
      "confidence": "medium"
    }"""
    result = parse_understanding(payload)
    assert result is not None
    assert result.needs_decomposition is True
    assert len(result.sub_questions) == 2
    assert result.anaphora_target == "fact_inventory_movement"
    assert result.entity_refs == []


def test_parse_understanding_rejects_unknown_property() -> None:
    result = parse_understanding(
        '{"focus_field": "quantity", "property": "color", '
        '"is_field_property_question": true, "confidence": "high"}'
    )
    # Unknown property value is dropped AND the question stops being a usable
    # field-property contract, so it must not be routed as one.
    assert result.property is None
    assert result.is_field_property_question is False


def test_parse_understanding_field_property_requires_field() -> None:
    result = parse_understanding(
        '{"property": "description", "is_field_property_question": true, '
        '"confidence": "high"}'
    )
    assert result is not None
    assert result.is_field_property_question is False


def test_parse_understanding_tolerates_fenced_prose() -> None:
    raw = 'Here is the json:\n```json\n{"needs_thinking": true, "sub_questions": [], ' \
          '"anaphora_target": null, "entity_refs": [], "confidence": "high"}\n```'
    result = parse_understanding(raw)
    assert result is not None
    assert result.needs_thinking is True


def test_parse_understanding_rejects_garbage() -> None:
    assert parse_understanding("not json at all") is None
    assert parse_understanding('{"intent": "GENERAL"}') is not None
    assert parse_understanding("") is None


@pytest.mark.parametrize("value,expected", [
    ("true", True), (True, True), (1, True),
    ("false", False), (None, False), (0, False),
])
def test_parse_understanding_boolean_coercion(value, expected) -> None:
    result = parse_understanding(
        f'{{"needs_thinking": {json_scalar(value)}, "confidence": "high"}}'
    )
    assert result is not None
    assert result.needs_thinking is expected


def json_scalar(value) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    if value is None:
        return "null"
    return str(value).lower()


def test_understand_query_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QU_ENABLED", False)
    llm = _FakeLLM(FORMATTED_PAYLOAD)
    assert asyncio_run(understand_query("quantity type?", llm)) is None
    assert llm.calls == []


def test_understand_query_enabled_passes_history(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QU_ENABLED", True)
    monkeypatch.setattr(settings, "USE_MOCK_LLM", False)
    llm = _FakeLLM(FORMATTED_PAYLOAD)
    history = [("lấy schema của fact_inventory_movement", "E1")]
    result = asyncio_run(understand_query("quantity có kiểu dữ liệu gì?", llm, history=history))
    assert result is not None
    assert result.focus_field == "quantity"
    # History and the QU system prompt must have been forwarded to the LLM.
    assert len(llm.calls) == 1
    prompt, seen_history, system_prompt = llm.calls[0]
    assert seen_history == history
    assert "lấy schema của fact_inventory_movement" in system_prompt
    assert "quantity có kiểu dữ liệu gì?" in system_prompt


def test_understand_query_llm_failure_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QU_ENABLED", True)
    monkeypatch.setattr(settings, "USE_MOCK_LLM", False)

    class _BoomLLM:
        async def generate(self, prompt, *, context=None, history=None,
                           system_prompt=None) -> str:
            raise RuntimeError("LLM down")

    assert asyncio_run(understand_query("anything", _BoomLLM())) is None


def test_understanding_result_to_dict() -> None:
    result = UnderstandingResult(
        focus_field="warehouse_id", property="nullable",
        is_field_property_question=True, confidence="high",
        entity_refs=["fact_inventory_movement"],
    )
    d = result.to_dict()
    assert d["focus_field"] == "warehouse_id"
    assert d["property"] == "nullable"
    assert d["needs_thinking"] is False
    assert d["entity_refs"] == ["fact_inventory_movement"]
