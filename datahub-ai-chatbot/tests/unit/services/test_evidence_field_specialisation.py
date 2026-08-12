"""Unit tests for the evidence-layer field-specialisation (over-answer fix).

Covers:
1. ``evidence_focus_field_answer`` answers a "which/what field" follow-up with
   the focused field (description + type) instead of the whole schema, re-records
   the field focus, and returns ``None`` for property / join / location asks.
2. ``evidence_quality_answer`` renders a recorded quality report deterministically
   and returns ``None`` when the evidence holds no quality payload.
3. ``evidence_field_answer`` falls back to the recorded ``focus_field`` for
   property-only anaphora ("Còn kiểu dữ liệu của nó?").
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.chat.evidence import EvidenceService
from retrieval.context_resolver import ContextResolution
from retrieval.evidence import EvidenceRecord

SCHEMA = [
    {"name": "movement_id", "type": "bigint", "description": "Mã định danh giao dịch"},
    {"name": "movement_date", "type": "date", "description": "Ngày giao dịch"},
    {"name": "quantity", "type": "decimal", "description": "Số lượng"},
]

RECORD = EvidenceRecord(
    evidence_id="E1", kind="schema", entity_name="fact_inventory_movement",
    entity_urn="urn:li:dataset:(urn:li:dataPlatform:redshift,fact_inventory_movement,PROD)",
    entity_type="dataset", tool_name="schema_lookup",
    query="lấy schema", structured={"fields": [f["name"] for f in SCHEMA],
                                     "schema_fields": SCHEMA},
)


def _svc():
    recorded = []
    svc = EvidenceService.__new__(EvidenceService)
    svc._ctx = SimpleNamespace(memory=SimpleNamespace(
        record_evidence=lambda *a, **k: recorded.append((a, k)),
    ))
    svc.record_evidence = lambda *a, **k: recorded.append((a, k))  # type: ignore[method-assign]
    svc.evidence_finish = AsyncMock(return_value="FINISHED")
    return svc, recorded


def _res(question: str, focus: str | None = None, prop: str | None = None,
         op: str | None = None, context_only: bool = False) -> ContextResolution:
    return ContextResolution(
        is_followup=True, context_only=context_only,
        referenced_evidence=RECORD, referenced_evidence_ids=["E1"],
        entity_name="fact_inventory_movement",
        entity_urn=RECORD.entity_urn, entity_type="dataset",
        focus_field=focus, property_name=prop, operation=op,
    )


@pytest.mark.asyncio
async def test_focus_field_answer_returns_field_not_schema() -> None:
    svc, recorded = _svc()
    res = _res("movement_date là field nào trong schema vừa lấy?",
               focus="movement_date")
    out = await svc.evidence_focus_field_answer(
        "uid", "cid", "movement_date là field nào trong schema vừa lấy?", res,
        "fact_inventory_movement", RECORD.structured)
    assert out == "FINISHED"
    text = svc.evidence_finish.await_args.args[3]
    assert "movement_date" in text
    assert "date" in text
    assert "Ngày giao dịch" in text
    assert "các trường:" not in text
    # Focus must be re-recorded so property-only follow-ups resolve the field.
    assert recorded, "expected a focus re-record"
    structured = recorded[-1][1]["structured"]
    assert structured["focus_field"] == "movement_date"


@pytest.mark.asyncio
async def test_focus_field_answer_skips_property_ask() -> None:
    svc, _ = _svc()
    res = _res("warehouse_id có kiểu dữ liệu gì?", focus="movement_date",
               prop="data_type", op="get_property")
    out = await svc.evidence_focus_field_answer(
        "uid", "cid", "warehouse_id có kiểu dữ liệu gì?", res,
        "fact_inventory_movement", RECORD.structured)
    assert out is None


@pytest.mark.asyncio
async def test_focus_field_answer_skips_unknown_field() -> None:
    svc, _ = _svc()
    res = _res("not_a_real_field là field nào?", focus="not_a_real_field")
    out = await svc.evidence_focus_field_answer(
        "uid", "cid", "not_a_real_field là field nào?", res,
        "fact_inventory_movement", RECORD.structured)
    assert out is None


@pytest.mark.asyncio
async def test_focus_field_answer_skips_location() -> None:
    svc, _ = _svc()
    res = _res("warehouse_id nằm ở bảng nào?", focus="warehouse_id")
    out = await svc.evidence_focus_field_answer(
        "uid", "cid", "warehouse_id nằm ở bảng nào?", res,
        "fact_inventory_movement", RECORD.structured)
    assert out is None


def test_quality_answer_renders_report() -> None:
    svc, _ = _svc()
    structured = {
        "overall_score": 72.5, "rating": "C",
        "sections": [{"name": "Completeness", "score": 80.0},
                     {"name": "Freshness", "score": 60.0}],
    }
    text = svc.evidence_quality_answer("fact_sales", structured)
    assert text is not None
    assert "72.5" in text
    assert "Completeness" in text and "80.0" in text
    assert "fact_sales" in text


def test_quality_answer_none_when_no_payload() -> None:
    svc, _ = _svc()
    assert svc.evidence_quality_answer("fact_sales", {"description": "x"}) is None
    assert svc.evidence_quality_answer("fact_sales", {}) is None


@pytest.mark.asyncio
async def test_field_answer_falls_back_to_recorded_focus() -> None:
    svc, _ = _svc()
    res = _res("Còn kiểu dữ liệu của nó?", focus=None, prop="data_type")
    # The referenced evidence carries the focus recorded by the previous turn.
    structured = {**RECORD.structured, "focus_field": "movement_date"}
    out = await svc.evidence_field_answer(
        "uid", "cid", "Còn kiểu dữ liệu của nó?", res,
        "fact_inventory_movement", structured)
    assert out == "FINISHED"
    text = svc.evidence_finish.await_args.args[3]
    assert "movement_date" in text
    assert "date" in text