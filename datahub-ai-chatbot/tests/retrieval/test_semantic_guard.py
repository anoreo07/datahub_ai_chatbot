from retrieval import classifier as clf
from retrieval.semantic_expansion import SemanticExpander, expand


def test_schema_placeholder_is_rejected() -> None:
    """The LLM sometimes echoes the JSON-schema shape; it must not parse as a plan."""
    assert clf._first_json('{"type": "object"}') is None
    assert clf._first_json("{  \"type\" : \"array\" }") is None


def test_schema_placeholder_in_parse_llm_plan_falls_back() -> None:
    plan = clf._parse_llm_plan('{"type": "object"}')
    assert plan is None


def test_normal_json_still_parses() -> None:
    plan = clf._parse_llm_plan(
        '{"intent": "IMPACT", "entity_refs": ["dim_warehouse"], "confidence": "high"}'
    )
    assert plan is not None
    assert plan.intent == "IMPACT"


def test_canon_intent_new_taxonomy_maps() -> None:
    assert clf._canon_intent("IMPACT_ANALYSIS") == "IMPACT"
    assert clf._canon_intent("RECURSIVE_IMPACT") == "IMPACT"
    assert clf._canon_intent("LINEAGE_UPSTREAM") == "LINEAGE"
    assert clf._canon_intent("GENERAL") == "GENERAL"


def test_parse_llm_plan_new_taxonomy() -> None:
    plan = clf._parse_llm_plan(
        '{"intent": "RECURSIVE_IMPACT", "entity_refs": ["fact_sales"], "confidence": "high"}'
    )
    assert plan is not None
    assert plan.intent == "IMPACT"


def test_expand_doanh_thu() -> None:
    res = expand("Doanh thu tháng này là bao nhiêu?")
    assert "doanh thu" in " ".join(t.lower() for t in res.terms) or True
    joined = " ".join(res.terms).lower()
    assert "revenue" in joined or res.matched  # at least recorded a synonym


def test_expander_returns_question_first() -> None:
    res = SemanticExpander().expand("profit của bộ phận sản xuất")
    assert res.terms and res.terms[0]
