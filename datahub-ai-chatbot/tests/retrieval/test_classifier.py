import pytest

from retrieval import classifier as clf
from retrieval.intent import classify_intent


def test_regex_plan_impact_vietnamese() -> None:
    plan = clf.regex_plan("Nếu thay đổi sales.orders thì những ai bị ảnh hưởng?")
    assert plan.intent == "IMPACT"
    assert plan.direction == "downstream"
    assert plan.source == "regex"


def test_regex_plan_impact_english() -> None:
    plan = clf.regex_plan("what downstream consumers would be impacted by sales.orders")
    assert plan.intent == "IMPACT"
    assert plan.direction == "downstream"


def test_regex_plan_lineage_both() -> None:
    plan = clf.regex_plan("Dataset finance.monthly_revenue lấy dữ liệu từ đâu?")
    assert plan.intent == "LINEAGE"


def test_regex_plan_lineage_direction() -> None:
    plan = clf.regex_plan("downstream của sales.orders")
    assert plan.intent == "LINEAGE"
    assert plan.direction == "downstream"


def test_regex_plan_matches_keyword_router() -> None:
    plan = clf.regex_plan("Term Revenue nghĩa là gì?")
    assert plan.intent == classify_intent("Term Revenue nghĩa là gì?").value


def test_needs_semantic_triggers_on_impact() -> None:
    assert clf.needs_semantic("bị ảnh hưởng bởi X", "GENERAL")
    assert clf.needs_semantic("lineage of X", "LINEAGE")
    assert not clf.needs_semantic("có bao nhiêu datasets", "COUNT_ENTITIES")


@pytest.mark.parametrize(
    "question",
    [
        "Xóa dataset sales.orders thì sao?",
        "xóa nó thì sao",
        "delete dataset dim_customer what happens?",
        "thay đổi dim_customer thì sao",
        "Tôi xóa và đảo bảng này thì sao",
        "ảnh hưởng của việc xóa dataset sales.orders",
        "what is the effect of dropping the raw.payments table",
    ],
)
def test_regex_plan_implicit_impact(question: str) -> None:
    plan = clf.regex_plan(question)
    assert plan.intent == "IMPACT", f"expected IMPACT for {question!r}, got {plan.intent}"
    assert plan.direction == "downstream"


@pytest.mark.parametrize(
    "question",
    [
        "schema của sales.orders",
        "doanh thu là gì",
        "ai sở hữu dataset sales.orders",
        "Xóa dataset sales.orders",  # imperative, no consequence asked
    ],
)
def test_plan_not_misclassified_as_impact(question: str) -> None:
    plan = clf.regex_plan(question)
    assert plan.intent != "IMPACT"


def test_parse_llm_plan_plain_object() -> None:
    raw = (
        '{"intent": "IMPACT", "entity_refs": ["sales.orders"], '
        '"entity_type": "dataset", "filter": {"dimension": null, "value": null}, '
        '"direction": "downstream", "params": {"depth": 3}, '
        '"is_composite": false, "confidence": "high"}'
    )
    plan = clf._parse_llm_plan(raw)
    assert plan is not None
    assert plan.intent == "IMPACT"
    assert plan.primary_entity == "sales.orders"
    assert plan.direction == "downstream"
    assert plan.params.depth == 3
    assert plan.confidence == "high"
    assert plan.source == "classifier"


def test_parse_llm_plan_markdown_wrapped() -> None:
    raw = '```json\n{"intent": "SCHEMA_LOOKUP", "entity_refs": ["sales.orders"]}\n```'
    plan = clf._parse_llm_plan(raw)
    assert plan is not None
    assert plan.intent == "SCHEMA_LOOKUP"


def test_parse_llm_plan_prose_wrapped() -> None:
    raw = ('Here is the classification:\n'
           '{"intent": "OWNER_LOOKUP", "entity_refs": ["sales.orders"], '
           '"confidence": "medium"}')
    plan = clf._parse_llm_plan(raw)
    assert plan is not None
    assert plan.intent == "OWNER_LOOKUP"


def test_parse_llm_plan_invalid_intent_falls_to_general() -> None:
    raw = '{"intent": "NOT_A_REAL_INTENT", "entity_refs": []}'
    plan = clf._parse_llm_plan(raw)
    assert plan is not None
    assert plan.intent == "GENERAL"


def test_parse_llm_plan_invalid_json_returns_none() -> None:
    assert clf._parse_llm_plan("not json at all") is None
    assert clf._parse_llm_plan("") is None


def test_clean_entities_various_shapes() -> None:
    assert clf._clean_entities(["a", " b ", "", None, 5]) == ["a", "b", "5"]
    assert clf._clean_entities("single") == ["single"]
    assert clf._clean_entities(None) == []
