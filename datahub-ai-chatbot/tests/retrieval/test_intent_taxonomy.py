from retrieval.intent import QueryIntent, classify_intent, normalize_intent


def test_normalize_maps_new_taxonomy() -> None:
    assert normalize_intent(QueryIntent.IMPACT_ANALYSIS) == QueryIntent.IMPACT
    assert normalize_intent(QueryIntent.RECURSIVE_IMPACT) == QueryIntent.IMPACT
    assert normalize_intent(QueryIntent.LINEAGE_UPSTREAM) == QueryIntent.LINEAGE
    assert normalize_intent(QueryIntent.GENERAL) == QueryIntent.GENERAL


def test_classify_impact_analysis_vietnamese() -> None:
    intent = classify_intent("Nếu xóa dataset dim_warehouse thì ai bị ảnh hưởng?")
    assert intent == QueryIntent.IMPACT_ANALYSIS


def test_classify_recursive_impact() -> None:
    intent = classify_intent("recursive impact của fact_sales")
    assert intent == QueryIntent.RECURSIVE_IMPACT


def test_classify_graph_query() -> None:
    intent = classify_intent("đường ngắn nhất giữa fact_sales và dim_warehouse")
    assert intent == QueryIntent.GRAPH_QUERY


def test_classify_normalized_legacy_impact() -> None:
    intent = normalize_intent(classify_intent("bỏ dim_a thì ai bị ảnh hưởng?"))
    assert intent == QueryIntent.IMPACT
