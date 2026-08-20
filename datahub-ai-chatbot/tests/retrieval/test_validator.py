"""Unit tests for the Query Understanding Validator / Guardrail.

``retrieval/validator.py`` checks the LLM's structured contract against ground
truth the system actually holds: real schema fields and real catalog names.
Ungrounded claims are dropped (never routed), unsafe evidence checks are
flagged, and ``apply_validation`` merges the verdict into the contract the
router reads.
"""

import asyncio

from retrieval.query_understanding import parse_understanding
from retrieval.validator import (
    GroundingContext,
    apply_validation,
    build_grounding_context,
    exact_name_index,
    field_exists,
    resolve_exact,
    validate_understanding,
)

SCHEMA_FIELDS = ["movement_id", "material_code", "warehouse_id",
                 "movement_type", "quantity", "movement_date", "created_by"]
CATALOG = ["fact_inventory_movement", "dim_warehouse", "dim_material",
           "fact_goods_receipt"]


class _FakeMemory:
    def __init__(self, evidence):
        self._evidence = evidence

    def get_evidence(self, user_id, conversation_id):
        return self._evidence


class _FakeEntityRepo:
    def __init__(self, schema_fields=None, catalog=None):
        self._schema_fields = schema_fields or []
        self._catalog = catalog or []

    async def search_by_name(self, name, entity_type=None):
        class _E:
            def __init__(self, payload):
                self.payload = payload
        return [_E({"schema_fields": [
            {"name": f} for f in self._schema_fields
        ]})]

    async def list_all(self, limit=500):
        class _E:
            def __init__(self, display_name):
                self.display_name = display_name
        return [_E(n) for n in self._catalog]


def test_exact_name_index_normalizes_diacritics_upper() -> None:
    index = exact_name_index(["fact_inventory_movement", "KHO HH"])
    assert "fact_inventory_movement" in index
    assert resolve_exact("Fact_Inventory_Movement", index) == "fact_inventory_movement"
    assert resolve_exact("khó hh", index) == "KHO HH"
    assert resolve_exact("missing", index) is None


def test_field_exists_case_insensitive() -> None:
    assert field_exists("Movement_Id", SCHEMA_FIELDS) is True
    assert field_exists("not_a_field", SCHEMA_FIELDS) is False


def test_validate_drops_ungrounded_field() -> None:
    understanding = parse_understanding("""
    {"focus_field": "money_value", "property": "data_type",
     "is_field_property_question": true, "confidence": "high",
     "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS,
        catalog_names=CATALOG,
    )
    assert v.trusted_field is None
    assert v.grounded is False
    assert any("not grounded" in r for r in v.reasons)


def test_validate_keeps_grounded_field() -> None:
    understanding = parse_understanding("""
    {"focus_field": "quantity", "property": "data_type",
     "is_field_property_question": true, "confidence": "high",
     "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS,
        catalog_names=CATALOG,
    )
    assert v.trusted_field == "quantity"


def test_validate_grounds_anaphora_and_entity() -> None:
    understanding = parse_understanding("""
    {"anaphora_target": "fact_inventory_movement", "entity_refs": ["dim_warehouse"],
     "confidence": "high", "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=[], catalog_names=CATALOG,
    )
    assert v.trusted_anaphora_target == "fact_inventory_movement"
    assert v.trusted_entity == "dim_warehouse"


def test_validate_drops_invented_anaphora() -> None:
    understanding = parse_understanding("""
    {"anaphora_target": "someone_else_table", "confidence": "medium",
     "parse_confidence": "medium"}
    """)
    v = validate_understanding(
        understanding, schema_fields=[], catalog_names=CATALOG,
    )
    assert v.trusted_anaphora_target is None


def test_validate_embargoes_ungrounded_sub_question_field() -> None:
    understanding = parse_understanding("""
    {"needs_decomposition": true,
     "sub_questions": [
       {"question": "fake_col có kiểu dữ liệu gì?",
        "field_ref": "fake_col", "intent": "FIELD_PROPERTY"}
     ],
     "confidence": "high", "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS, catalog_names=CATALOG,
    )
    assert understanding.sub_question_details[0].question in v.embargoed_sub_questions


def test_validate_evidence_quality_when_no_context() -> None:
    understanding = parse_understanding("""
    {"needs_decomposition": true,
     "sub_questions": [{
       "question": "movement_date có null không?",
       "field_ref": "movement_date", "intent": "FIELD_PROPERTY",
       "evidence_quality_check_needed": true
     }],
     "confidence": "high", "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS, catalog_names=CATALOG,
        active_entity="fact_inventory_movement", has_evidence_for_active=False,
    )
    assert v.evidence_insufficient is True


def test_validate_evidence_quality_passes_with_context() -> None:
    understanding = parse_understanding("""
    {"needs_decomposition": true,
     "sub_questions": [{
       "question": "movement_date có null không?",
       "field_ref": "movement_date", "intent": "FIELD_PROPERTY",
       "evidence_quality_check_needed": true
     }],
     "confidence": "high", "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS, catalog_names=CATALOG,
        active_entity="fact_inventory_movement", has_evidence_for_active=True,
    )
    assert v.evidence_insufficient is False


def test_apply_validation_drops_ungrounded_field() -> None:
    understanding = parse_understanding("""
    {"focus_field": "invented_col", "property": "description",
     "is_field_property_question": true, "confidence": "high",
     "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS, catalog_names=CATALOG,
    )
    result = apply_validation(understanding, v)
    assert result.focus_field is None
    assert result.property is None
    assert result.is_field_property_question is False
    # The raw contract must be untouched for telemetry comparison.
    assert understanding.focus_field == "invented_col"


def test_apply_validation_removes_embargoed_sub_questions() -> None:
    understanding = parse_understanding("""
    {"needs_decomposition": true,
     "sub_questions": [
       {"question": "quantity có null không?", "field_ref": "quantity",
        "intent": "FIELD_PROPERTY"},
       {"question": "ghost_col có null không?", "field_ref": "ghost_col",
        "intent": "FIELD_PROPERTY"}
     ],
     "confidence": "high", "parse_confidence": "high"}
    """)
    v = validate_understanding(
        understanding, schema_fields=SCHEMA_FIELDS, catalog_names=CATALOG,
    )
    result = apply_validation(understanding, v)
    assert len(result.sub_question_details) == 1
    assert result.sub_question_details[0].field_ref == "quantity"


def test_build_grounding_context_assembles_facts() -> None:
    evidence = [{
        "evidence_id": "E1", "entity_name": "fact_inventory_movement",
        "kind": "schema", "structured": {"fields": ["quantity", "movement_date"]},
    }]
    memory = _FakeMemory(evidence)
    repo = _FakeEntityRepo(catalog=CATALOG)
    ctx = asyncio.run(build_grounding_context(
        memory, repo, "u", "c", active_entities=[
            {"name": "fact_inventory_movement", "entity_type": "dataset"},
        ],
    ))
    assert ctx.active_entity == "fact_inventory_movement"
    assert ctx.field_names == ["quantity", "movement_date"]
    assert ctx.has_evidence_for_active is True
    assert "fact_inventory_movement" in ctx.catalog_names
    assert ctx.evidence == evidence


def test_build_grounding_context_falls_back_to_payload_schema() -> None:
    memory = _FakeMemory([])
    repo = _FakeEntityRepo(
        schema_fields=["movement_id", "quantity"],
        catalog=["fact_inventory_movement"],
    )
    ctx = asyncio.run(build_grounding_context(
        memory, repo, "u", "c",
        active_entities=[{"name": "fact_inventory_movement"}],
    ))
    assert "movement_id" in ctx.field_names
    assert ctx.has_evidence_for_active is False


def test_build_grounding_context_empty_active_entity() -> None:
    ctx = asyncio.run(build_grounding_context(
        _FakeMemory([]), _FakeEntityRepo(catalog=CATALOG), "u", "c",
        active_entities=[],
    ))
    assert ctx.active_entity is None
    assert ctx.field_names == []
    assert ctx.has_evidence_for_active is False


def test_grounding_context_has_defaults() -> None:
    ctx = GroundingContext()
    assert ctx.evidence == []
    assert ctx.catalog_names == []
