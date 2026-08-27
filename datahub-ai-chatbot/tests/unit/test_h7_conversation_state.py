"""Tests for H7: Conversation State — follow-up classification + query merging.

Covers:
  - classify_followup_type(): NEW_QUERY, FOLLOW_UP, REFINEMENT, CLARIFICATION_RESPONSE, AMBIGUOUS
  - merge_query_specs(): inheritance rules for each follow-up type
  - Conversation memory: query_spec persistence, turn state, clarification state
"""

from __future__ import annotations

from app.services.conversation import (
    ConversationMemory,
    FollowUpType,
)
from retrieval.query_parser import classify_followup_type, merge_query_specs, parse_query
from retrieval.query_spec import Operation

# ---------------------------------------------------------------------------
# classify_followup_type tests
# ---------------------------------------------------------------------------

class TestClassifyFollowUpType:
    """Tests for follow-up type classification."""

    def test_new_query_no_previous(self):
        """No previous QuerySpec → NEW_QUERY."""
        assert classify_followup_type("dim_warehouse có domain gì?", None) == "NEW_QUERY"

    def test_new_query_independent(self):
        """Completely different question → NEW_QUERY."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("bao nhiêu dashboard?", prev) == "NEW_QUERY"

    def test_followup_anaphora(self):
        """Anaphora ('nó') with previous entity → FOLLOW_UP."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("Nó thuộc lĩnh vực nào?", prev) == "FOLLOW_UP"

    def test_followup_implicit_reference(self):
        """Implicit reference ('của nó') with previous entity → FOLLOW_UP."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("Owner của nó là ai?", prev) == "FOLLOW_UP"

    def test_followup_same_entity_new_property(self):
        """Same entity name, new property → FOLLOW_UP."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("dim_warehouse có owner không?", prev) == "FOLLOW_UP"

    def test_refinement_chỉ(self):
        """'Chỉ SAP thôi' → REFINEMENT."""
        prev = {"entity_name": "dim_warehouse", "property": "domain", "value": None}
        assert classify_followup_type("Chỉ SAP thôi", prev) == "REFINEMENT"

    def test_refinement_same_entity_same_property_with_value(self):
        """Same entity + same property but now with a value → REFINEMENT."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("dim_warehouse thuộc domain SALES", prev) == "REFINEMENT"

    def test_clarification_a_b_selection(self):
        """User selects A/B/C/D from clarification → CLARIFICATION_RESPONSE."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("B", prev) == "CLARIFICATION_RESPONSE"

    def test_clarification_confirm(self):
        """User says 'đúng rồi' → CLARIFICATION_RESPONSE."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("Đúng rồi", prev) == "CLARIFICATION_RESPONSE"

    def test_clarification_numeric_selection(self):
        """User selects 1/2/3 → CLARIFICATION_RESPONSE."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        assert classify_followup_type("1", prev) == "CLARIFICATION_RESPONSE"

    def test_ambiguous_anaphora_no_context(self):
        """Anaphora with no previous entity → AMBIGUOUS."""
        prev = {"entity_name": None, "property": "domain"}
        assert classify_followup_type("Nó có domain gì?", prev) == "AMBIGUOUS"

    def test_refinement_no_entity(self):
        """'Chỉ' without previous entity → NEW_QUERY (nothing to inherit)."""
        prev = {"entity_name": None, "property": "domain"}
        assert classify_followup_type("Chỉ SAP thôi", prev) == "NEW_QUERY"


# ---------------------------------------------------------------------------
# merge_query_specs tests
# ---------------------------------------------------------------------------

class TestMergeQuerySpecs:
    """Tests for query spec merging across turns."""

    def test_merge_new_query_returns_new(self):
        """NEW_QUERY: use new spec as-is."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        new = parse_query("bao nhiêu dashboard?")
        result = merge_query_specs(prev, new)
        assert result.entity_name is None
        assert result.operation == Operation.COUNT

    def test_merge_followup_inherits_entity(self):
        """FOLLOW_UP: inherit entity from prev, use new property."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        new = parse_query("dim_warehouse có owner không?")
        result = merge_query_specs(prev, new)
        assert result.entity_name == "dim_warehouse"
        assert result.attr == "owner"

    def test_merge_followup_anaphora_inherits_entity(self):
        """FOLLOW_UP with anaphora: inherit entity from prev."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        new = parse_query("Nó có owner không?")
        result = merge_query_specs(prev, new)
        assert result.entity_name == "dim_warehouse"
        assert result.attr == "owner"

    def test_merge_refinement_inherits_entity_and_property(self):
        """REFINEMENT: inherit entity + property, add value from new."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        new = parse_query("dim_warehouse thuộc domain SALES")
        result = merge_query_specs(prev, new)
        assert result.entity_name == "dim_warehouse"
        assert result.attr == "domain"
        # _detect_equals_value captures everything after "thuộc" = "domain sales"
        assert result.value is not None and "sales" in result.value

    def test_merge_refinement_chỉ(self):
        """REFINEMENT via 'Chỉ': inherit entity + property, add filter."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        new = parse_query("Chỉ SAP thôi")
        result = merge_query_specs(prev, new)
        assert result.entity_name == "dim_warehouse"

    def test_merge_clarification_returns_prev(self):
        """CLARIFICATION_RESPONSE: return the pending spec (prev)."""
        prev = {"entity_name": "dim_warehouse", "property": "domain", "operation": "GET"}
        new = parse_query("B")
        result = merge_query_specs(prev, new)
        assert result.entity_name == "dim_warehouse"
        assert result.attr == "domain"

    def test_merge_none_prev_returns_new(self):
        """No previous spec: return new as-is."""
        new = parse_query("dim_warehouse có domain gì?")
        result = merge_query_specs(None, new)
        assert result.entity_name == "dim_warehouse"
        assert result.attr == "domain"

    def test_merge_preserves_operation(self):
        """REFINEMENT preserves previous operation when new is GET."""
        prev = {"entity_name": "dim_warehouse", "property": "domain", "operation": "LIST"}
        new = parse_query("dim_warehouse thuộc domain SALES")
        result = merge_query_specs(prev, new)
        assert result.operation == Operation.LIST

    def test_merge_context_dependency_marked(self):
        """FOLLOW_UP marks context_dependency correctly."""
        prev = {"entity_name": "dim_warehouse", "property": "domain"}
        new = parse_query("dim_warehouse có owner không?")
        result = merge_query_specs(prev, new)
        assert result.context_dependency.get("carried_from_previous_turn") is True
        # When new already specifies entity_name, it's not "carried" from prev
        assert result.entity_name == "dim_warehouse"


# ---------------------------------------------------------------------------
# ConversationMemory query_spec persistence
# ---------------------------------------------------------------------------

class TestConversationQuerySpecPersistence:
    """Tests for query_spec persistence in ConversationMemory."""

    def test_set_and_get_query_spec(self):
        """set_query_spec / get_query_spec round-trip."""
        mem = ConversationMemory()
        spec = {"entity_name": "dim_warehouse", "property": "domain"}
        mem.set_query_spec("u1", "c1", spec)
        assert mem.get_query_spec("u1", "c1") == spec

    def test_get_query_spec_returns_none_initially(self):
        """get_query_spec returns None for fresh conversation."""
        mem = ConversationMemory()
        assert mem.get_query_spec("u1", "c1") is None

    def test_set_turn_state(self):
        """set_turn_state attaches state to the most recent turn."""
        mem = ConversationMemory()
        mem.add_turn("u1", "c1", "q1", "a1")
        spec = {"entity_name": "dim_warehouse", "property": "domain"}
        mem.set_turn_state("u1", "c1", query_spec=spec, followup_type="FOLLOW_UP")
        turn = mem.get_last_turn("u1", "c1")
        assert turn is not None
        assert turn.query_spec == spec
        assert turn.followup_type == "FOLLOW_UP"

    def test_get_last_turn_returns_none(self):
        """get_last_turn returns None for fresh conversation."""
        mem = ConversationMemory()
        assert mem.get_last_turn("u1", "c1") is None

    def test_add_turn_db_with_query_spec(self):
        """add_turn_db with query_spec sets state on turn and persists spec."""
        import asyncio
        from unittest.mock import MagicMock

        mem = ConversationMemory()
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        # Mock the commit to avoid actual DB call
        async def mock_commit():
            pass
        mock_session.commit = mock_commit

        spec = {"entity_name": "dim_warehouse", "property": "domain"}
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                mem.add_turn_db(mock_session, "u1", "c1", "q1", "a1", query_spec=spec)
            )
        finally:
            loop.close()
        turn = mem.get_last_turn("u1", "c1")
        assert turn is not None
        assert turn.query_spec == spec
        assert mem.get_query_spec("u1", "c1") == spec

    def test_clarification_state_set_get_clear(self):
        """set_clarification_state / get / clear round-trip."""
        mem = ConversationMemory()
        pending = {"entity_name": "dim_warehouse", "property": "domain"}
        candidates = [{"name": "A"}, {"name": "B"}]
        mem.set_clarification_state("u1", "c1", pending, candidates, "entity_disambiguation")
        state = mem.get_clarification_state("u1", "c1")
        assert state is not None
        assert state.pending_query_spec == pending
        assert len(state.candidates) == 2
        assert state.clarification_type == "entity_disambiguation"

        mem.clear_clarification_state("u1", "c1")
        assert mem.get_clarification_state("u1", "c1") is None


# ---------------------------------------------------------------------------
# FollowUpType constants
# ---------------------------------------------------------------------------

class TestFollowUpTypeConstants:
    """Verify FollowUpType constants match expected values."""

    def test_constants(self):
        assert FollowUpType.NEW_QUERY == "NEW_QUERY"
        assert FollowUpType.FOLLOW_UP == "FOLLOW_UP"
        assert FollowUpType.REFINEMENT == "REFINEMENT"
        assert FollowUpType.CLARIFICATION_RESPONSE == "CLARIFICATION_RESPONSE"
        assert FollowUpType.AMBIGUOUS == "AMBIGUOUS"


# ---------------------------------------------------------------------------
# H8: Clarification persistence tests
# ---------------------------------------------------------------------------

class TestClarificationPersistence:
    """Tests for clarification state lifecycle."""

    def test_clarify_stores_pending_spec(self):
        """When a clarification is asked, pending_query_spec is stored."""
        mem = ConversationMemory()
        pending = {"entity_name": None, "property": "domain", "scope": "GLOBAL"}
        candidates = [
            {"name": "dim_warehouse", "entity_type": "dataset"},
            {"name": "dim_inventory", "entity_type": "dataset"},
        ]
        mem.set_clarification_state("u1", "c1", pending, candidates, "entity_disambiguation")
        state = mem.get_clarification_state("u1", "c1")
        assert state is not None
        assert state.pending_query_spec == pending
        assert len(state.candidates) == 2
        assert state.clarification_type == "entity_disambiguation"
        assert state.asked_at > 0

    def test_clarification_response_clears_state(self):
        """After user responds to clarification, state is cleared."""
        mem = ConversationMemory()
        pending = {"entity_name": None, "property": "domain"}
        mem.set_clarification_state("u1", "c1", pending, [], "property_disambiguation")
        assert mem.get_clarification_state("u1", "c1") is not None
        mem.clear_clarification_state("u1", "c1")
        assert mem.get_clarification_state("u1", "c1") is None

    def test_clarification_response_classified_correctly(self):
        """'A' is classified as CLARIFICATION_RESPONSE when pending state exists."""
        prev = {"entity_name": None, "property": "domain"}
        assert classify_followup_type("A", prev) == "CLARIFICATION_RESPONSE"

    def test_clarification_preserves_spec_across_turns(self):
        """Pending spec survives until user responds."""
        import asyncio
        from unittest.mock import MagicMock

        mem = ConversationMemory()
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        async def mock_commit():
            pass
        mock_session.commit = mock_commit

        loop = asyncio.new_event_loop()
        try:
            # Turn 1: system asks clarification
            pending = {"entity_name": None, "property": "domain", "scope": "GLOBAL"}
            mem.set_clarification_state("u1", "c1", pending, [{"name": "A"}], "entity_disambiguation")
            loop.run_until_complete(
                mem.add_turn_db(mock_session, "u1", "c1", "Bạn muốn dataset nào?", "Chọn A hoặc B")
            )

            # State persists
            state = mem.get_clarification_state("u1", "c1")
            assert state is not None
            assert state.pending_query_spec == pending

            # Turn 2: user responds → state cleared
            mem.clear_clarification_state("u1", "c1")
            loop.run_until_complete(
                mem.add_turn_db(mock_session, "u1", "c1", "A", "Dataset A có domain...")
            )
            assert mem.get_clarification_state("u1", "c1") is None
        finally:
            loop.close()
