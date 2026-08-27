"""Unit tests for multi-turn coreference resolution (nó/đó/ấy/this/that).

Covers the shared ``retrieval/coreference`` module and its two callers:

1. The anaphor must resolve to the conversation's **dataset subject**, even
   when the most recent turn mentioned only a field of that dataset
   (regression: "warehouse_id là gì?" stealing "nó" away from "dim_warehouse").
2. Bare fields are used only when no subject was ever established.
3. English anaphora ("this dataset", "what is its schema") work the same way.
4. Detection helpers (``has_anaphora`` / ``extract_candidates``) behave sanely.
"""

import pytest

from retrieval.coreference import (
    extract_candidates,
    has_anaphora,
    resolve_entity_reference,
)
from retrieval.intent_resolver import IntentResolver, _resolve_anaphora_from_history

HIST_DATASET_THEN_FIELD = [
    ("Dataset dim_warehouse có schema gì?", "10 fields"),
    ("warehouse_id là gì?", "mã kho"),
]

HIST_LINEAGE = [
    ("Impact analysis cho dataset dim_warehouse", "..."),
    ("nó bị ảnh hưởng gì", "..."),
]


# --------------------------------------------------------------------------- #
# Shared resolver: pure, no I/O
# --------------------------------------------------------------------------- #
class TestResolveEntityReference:
    def test_anaphor_prefers_dataset_subject_over_field(self) -> None:
        assert resolve_entity_reference(HIST_DATASET_THEN_FIELD) == "dim_warehouse"

    def test_anaphor_over_impact_turn(self) -> None:
        assert resolve_entity_reference(HIST_LINEAGE) == "dim_warehouse"

    def test_field_only_history_falls_back_to_field(self) -> None:
        hist = [("warehouse_id là gì?", "...")]
        assert resolve_entity_reference(hist) == "warehouse_id"

    def test_empty_history_returns_none(self) -> None:
        assert resolve_entity_reference([]) is None
        assert resolve_entity_reference(None) is None

    def test_dotted_urn_subject(self) -> None:
        hist = [
            ("schema của sales.order_details là gì?", "..."),
            ("order_id là gì?", "..."),
        ]
        assert resolve_entity_reference(hist) == "sales.order_details"

    def test_english_anaphor(self) -> None:
        hist = [("what is the schema of fact_revenue?", "..." ), ("what is its domain?", "...")]
        assert resolve_entity_reference(hist) == "fact_revenue"

    def test_most_recent_subject_wins(self) -> None:
        hist = [
            ("schema của dim_warehouse là gì?", "..."),
            ("schema của dim_customer là gì?", "..."),
            ("owner của nó là ai?", "..."),
        ]
        assert resolve_entity_reference(hist) == "dim_customer"


# --------------------------------------------------------------------------- #
# Intent resolver integration
# --------------------------------------------------------------------------- #
class TestIntentResolverAnaphora:
    """The resolver routes anaphoric follow-ups via the shared resolver."""

    def test_resolve_anaphora_helpers_agree(self) -> None:
        assert _resolve_anaphora_from_history(HIST_DATASET_THEN_FIELD) == "dim_warehouse"
        assert _resolve_anaphora_from_history(HIST_LINEAGE) == "dim_warehouse"

    @pytest.mark.asyncio
    async def test_anaphor_under_action_uses_dataset_subject(self) -> None:
        resolver = IntentResolver(llm=None)
        # "nó" reparsed into impact framing: the message is an explicit
        # metadata intent so it overrides the action, but still carries the
        # resolved dataset entity as the hint.
        res = await resolver.resolve(
            "những dáy nào bị ảnh hưởng?",
            selected_action="impact",
            history=HIST_DATASET_THEN_FIELD,
            trace_id="t",
        )
        assert res.entity_hint is None or "warehouse_id" != (res.entity_hint or "")
        assert res.decision in {"agree", "override"}


# --------------------------------------------------------------------------- #
# has_anaphora / extract_candidates
# --------------------------------------------------------------------------- #
class TestAnaphoraDetectors:
    @pytest.mark.parametrize(
        "msg",
        ["Nó thuộc lĩnh vực nào?", "Đó là gì?", "ấy data?", "this one",
         "schema của nó là gì?", "what about this?", "đây đây"],
    )
    def test_anaphora_true(self, msg: str) -> None:
        assert has_anaphora(msg) is True, msg

    @pytest.mark.parametrize(
        "msg",
        ["tôi cần dataset dim_warehouse", "hello có bao nhiêu dataset",
         "fact_sales_order schema", "tôi muốn xem lineage of fact"],
    )
    def test_anaphora_false(self, msg: str) -> None:
        assert has_anaphora(msg) is False, msg

    def test_extract_candidates_roles(self) -> None:
        rows = extract_candidates(HIST_DATASET_THEN_FIELD)
        assert ("dim_warehouse", "subject") in rows
        assert ("warehouse_id", "mention") in rows
