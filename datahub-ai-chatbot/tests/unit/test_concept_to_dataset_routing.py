"""Tests for Concept-to-Dataset discovery routing and intent preservation."""
from __future__ import annotations

from app.services.chat.question_analysis import extract_concept_phrase
from retrieval.metadata_query import normalize_attribute
from retrieval.metadata_query_parser import parse_metadata_query


def test_normalize_attribute_no_false_positives():
    """Ensure short words like 'lien' or 'quan' never fuzzy-match to domain or other attributes."""
    assert normalize_attribute("lien") is None
    assert normalize_attribute("quan") is None
    assert normalize_attribute("lien quan") is None
    assert normalize_attribute("khai") is None
    assert normalize_attribute("niem") is None
    # Valid exact synonyms must work
    assert normalize_attribute("domain") == "domain"
    assert normalize_attribute("linh vuc") == "domain"
    assert normalize_attribute("owner") == "owner"
    assert normalize_attribute("lineage") == "lineage"
    # Valid fuzzy match on longer words must work
    assert normalize_attribute("linage") == "lineage"


def test_parse_metadata_query_excludes_concept_queries():
    """Concept discovery queries must NOT be parsed as metadata attribute listings."""
    concept_queries = [
        "Có dataset nào liên quan đến khái niệm BOM COST OPTIMIZATION (BCO) không?",
        "Những dataset nào liên quan đến EBOM?",
        "Dataset nào phục vụ nhu cầu linh kiện?",
        "Có bảng nào chứa thông tin về product cost không?",
        "Tìm dataset liên quan đến BOM cost",
        "Dataset nào có thể dùng để phân tích chi phí BOM?",
        "BOM COST OPTIMIZATION (BCO) được sử dụng trong dataset nào?",
    ]
    for q in concept_queries:
        res = parse_metadata_query(q)
        assert res is None, f"Query '{q}' should NOT be parsed as metadata listing but got: {res}"


def test_parse_metadata_query_preserves_legitimate_listings():
    """Legitimate metadata listing queries must still be correctly parsed."""
    res = parse_metadata_query("dataset nào có lineage?")
    assert res is not None
    assert res.entity_type == "dataset"
    assert any(f.attribute == "lineage" for f in res.filters)

    res_owner = parse_metadata_query("dataset nào không có owner?")
    assert res_owner is not None
    assert any(f.attribute == "owner" for f in res_owner.filters)


def test_extract_concept_phrase():
    """Test accurate concept extraction across various phrasing formats."""
    cases = [
        (
            "Có dataset nào liên quan đến khái niệm BOM COST OPTIMIZATION (BCO) không?",
            "BOM COST OPTIMIZATION (BCO)",
        ),
        ("Những dataset nào liên quan đến EBOM?", "EBOM"),
        ("Dataset nào phục vụ nhu cầu linh kiện?", "nhu cầu linh kiện"),
        ("Có bảng nào chứa thông tin về product cost không?", "product cost"),
        ("Tìm dataset liên quan đến BOM cost", "BOM cost"),
        ("Dataset nào có thể dùng để phân tích chi phí BOM?", "chi phí BOM"),
        (
            "BOM COST OPTIMIZATION (BCO) được sử dụng trong dataset nào?",
            "BOM COST OPTIMIZATION (BCO)",
        ),
        (
            "Những dataset nào liên quan đến BOM COST OPTIMIZATION?",
            "BOM COST OPTIMIZATION",
        ),
        ("Có dataset nào liên quan đến khái niệm doanh thu không?", "doanh thu"),
    ]
    for question, expected in cases:
        extracted = extract_concept_phrase(question)
        assert extracted == expected, (
            f"Failed for '{question}': expected '{expected}', got '{extracted}'"
        )


def test_concept_regex_negative_cases():
    """Non-concept queries must not match concept regex."""
    negatives = [
        "Liệt kê dataset thuộc domain SẢN XUẤT",
        "Có bao nhiêu dataset thuộc domain SẢN XUẤT?",
        "EBOM là gì?",
        "Schema của dataset dim_customer gồm những cột nào?",
        "Lineage của fact_sales là gì?",
        "Ai là owner của bảng dim_sales?",
    ]
    for q in negatives:
        extracted = extract_concept_phrase(q)
        assert extracted is None, (
            f"Query '{q}' should NOT extract concept but got '{extracted}'"
        )
