"""Tests for the Generic Metadata Listing Engine.

Covers:
  - MetadataQueryParser: 22+ test cases for NLP → structured query
  - MetadataFilterEngine: SQL generation, JSON checks
  - AttributeRegistry: synonym matching, typo normalization
  - Edge cases: entity-specific queries, entity type overlap, false positives
"""

from __future__ import annotations

import pytest

from retrieval.metadata_query import (
    ATTRIBUTE_REGISTRY,
    FilterOperation,
    GenericMetadataQuery,
    MetadataFilter,
    _edit_distance,
    normalize_attribute,
)
from retrieval.metadata_query_parser import (
    _detect_entity_type,
    _detect_operations,
    _extract_limit,
    parse_metadata_query,
)

# ---------------------------------------------------------------------------
# AttributeRegistry tests
# ---------------------------------------------------------------------------

class TestAttributeRegistry:
    def test_registry_has_expected_attributes(self):
        expected = {
            "owner", "lineage", "domain", "description", "tags",
            "glossary", "schema", "platform", "environment",
            "documentation", "deprecation",
        }
        assert set(ATTRIBUTE_REGISTRY.keys()) == expected

    def test_each_attribute_has_synonyms(self):
        for name, spec in ATTRIBUTE_REGISTRY.items():
            assert len(spec.synonyms) > 0, f"{name} has no synonyms"

    def test_each_attribute_has_entity_types(self):
        for name, spec in ATTRIBUTE_REGISTRY.items():
            assert len(spec.entity_types) > 0, f"{name} has no entity_types"


# ---------------------------------------------------------------------------
# normalize_attribute tests
# ---------------------------------------------------------------------------

class TestNormalizeAttribute:
    def test_exact_synonym(self):
        assert normalize_attribute("owner") == "owner"
        assert normalize_attribute("lineage") == "lineage"
        assert normalize_attribute("tags") == "tags"

    def test_vietnamese_synonym(self):
        assert normalize_attribute("chủ sở hữu") == "owner"
        assert normalize_attribute("dòng dữ liệu") == "lineage"
        assert normalize_attribute("nhãn") == "tags"

    def test_ascii_normalization(self):
        assert normalize_attribute("chu so huu") == "owner"

    def test_typo_fuzzy_match(self):
        # "linage" → "lineage" (1 edit distance)
        assert normalize_attribute("linage") == "lineage"

    def test_no_match(self):
        assert normalize_attribute("xyz") is None
        assert normalize_attribute("a") is None


# ---------------------------------------------------------------------------
# _edit_distance tests
# ---------------------------------------------------------------------------

class TestEditDistance:
    def test_identical(self):
        assert _edit_distance("abc", "abc") == 0

    def test_one_edit(self):
        assert _edit_distance("abc", "axc") == 1

    def test_different_lengths(self):
        d = _edit_distance("kitten", "sitting")
        assert d == 3


# ---------------------------------------------------------------------------
# Parser: positive detection tests
# ---------------------------------------------------------------------------

class TestParserPositive:
    def test_exists_lineage(self):
        q = parse_metadata_query("dataset nào có lineage?")
        assert q is not None
        assert q.entity_type == "dataset"
        assert len(q.filters) == 1
        assert q.filters[0].attribute == "lineage"
        assert q.filters[0].operation == FilterOperation.EXISTS

    def test_missing_owner(self):
        q = parse_metadata_query("dataset nào không có owner?")
        assert q is not None
        assert q.filters[0].attribute == "owner"
        assert q.filters[0].operation == FilterOperation.MISSING

    def test_exists_schema(self):
        q = parse_metadata_query("dataset nào có schema?")
        assert q is not None
        assert q.filters[0].attribute == "schema"
        assert q.filters[0].operation == FilterOperation.EXISTS

    def test_missing_description(self):
        q = parse_metadata_query("dataset nào thiếu description?")
        assert q is not None
        assert q.filters[0].attribute == "description"
        assert q.filters[0].operation == FilterOperation.MISSING

    def test_exists_tags(self):
        q = parse_metadata_query("show datasets có tags")
        assert q is not None
        assert q.filters[0].attribute == "tags"
        assert q.filters[0].operation == FilterOperation.EXISTS

    def test_exists_glossary(self):
        q = parse_metadata_query("dataset nào có glossary?")
        assert q is not None
        assert q.filters[0].attribute == "glossary"
        assert q.filters[0].operation == FilterOperation.EXISTS

    def test_exists_platform(self):
        q = parse_metadata_query("dataset nào có platform?")
        assert q is not None
        assert q.filters[0].attribute == "platform"

    def test_exists_environment(self):
        q = parse_metadata_query("dataset nào có environment?")
        assert q is not None
        assert q.filters[0].attribute == "environment"

    def test_exists_documentation(self):
        q = parse_metadata_query("dataset nào có documentation?")
        assert q is not None
        assert q.filters[0].attribute == "documentation"

    def test_count_with_exists(self):
        q = parse_metadata_query("co bao nhieu dataset co owner?")
        assert q is not None
        assert q.include_count is True
        assert q.filters[0].attribute == "owner"
        assert q.filters[0].operation == FilterOperation.EXISTS

    def test_multi_filter(self):
        q = parse_metadata_query("dataset nào có lineage và owner?")
        assert q is not None
        assert len(q.filters) == 2
        attrs = {f.attribute for f in q.filters}
        assert "lineage" in attrs
        assert "owner" in attrs

    def test_limit_extraction(self):
        q = parse_metadata_query("list 10 datasets có schema")
        assert q is not None
        assert q.limit == 10

    def test_limit_capped_at_100(self):
        q = parse_metadata_query("list 200 datasets có tags")
        assert q is not None
        assert q.limit == 100

    def test_entity_type_dashboard(self):
        q = parse_metadata_query("dashboard nào có lineage?")
        assert q is not None
        assert q.entity_type == "dashboard"

    def test_entity_type_document_vietnamese(self):
        q = parse_metadata_query("tài liệu nào có description?")
        assert q is not None
        assert q.entity_type == "document"

    def test_vietnamese_synonym_owner(self):
        q = parse_metadata_query("dataset nào có chủ sở hữu?")
        assert q is not None
        assert q.filters[0].attribute == "owner"

    def test_equals_domain(self):
        q = parse_metadata_query("dataset nào thuộc domain SALES?")
        assert q is not None
        assert q.filters[0].attribute == "domain"
        assert q.filters[0].operation == FilterOperation.EQUALS
        assert q.filters[0].value is not None


# ---------------------------------------------------------------------------
# Parser: negative detection tests (should return None)
# ---------------------------------------------------------------------------

class TestParserNegative:
    def test_entity_specific_schema(self):
        assert parse_metadata_query("Dataset sales.orders có những field nào?") is None

    def test_entity_specific_exists(self):
        assert parse_metadata_query("Dataset abc.xyz có tồn tại không?") is None

    def test_pure_listing_vietnamese(self):
        assert parse_metadata_query("Có những dataset nào?") is None

    def test_pure_listing_system(self):
        assert parse_metadata_query("dataset nào trong hệ thống?") is None

    def test_term_to_datasets(self):
        assert parse_metadata_query("Dataset nào gắn term Customer?") is None

    def test_domain_count_with_value(self):
        assert parse_metadata_query("Lĩnh vực tài chính có bao nhiêu datasets?") is None

    def test_glossary_listing(self):
        assert parse_metadata_query("Có những glossary terms nào?") is None

    def test_liet_ke_no_attribute(self):
        assert parse_metadata_query("liệt kê datasets") is None

    def test_danh_sach(self):
        assert parse_metadata_query("danh sách datasets") is None

    def test_entity_type_only_no_metadata_signal(self):
        assert parse_metadata_query("có những datasets nào trong hệ thống?") is None


# ---------------------------------------------------------------------------
# Parser: entity type detection
# ---------------------------------------------------------------------------

class TestEntityTypeDetection:
    def test_dataset(self):
        assert _detect_entity_type("dataset nào có lineage?") == "dataset"

    def test_dashboard(self):
        assert _detect_entity_type("dashboard nào có lineage?") == "dashboard"

    def test_glossary_term(self):
        assert _detect_entity_type("glossary term nào có description?") == "glossary_term"

    def test_document_vietnamese(self):
        assert _detect_entity_type("tài liệu nào có description?") == "document"

    def test_default_is_dataset(self):
        assert _detect_entity_type("nào có lineage?") == "dataset"


# ---------------------------------------------------------------------------
# Parser: operation detection
# ---------------------------------------------------------------------------

class TestOperationDetection:
    def test_exists(self):
        op, val = _detect_operations("có lineage")
        assert op == FilterOperation.EXISTS

    def test_missing(self):
        op, val = _detect_operations("không có owner")
        assert op == FilterOperation.MISSING

    def test_thieu(self):
        op, val = _detect_operations("thiếu description")
        assert op == FilterOperation.MISSING

    def test_equals(self):
        op, val = _detect_operations("thuộc domain SALES")
        assert op == FilterOperation.EQUALS
        assert val == "domain sales"


# ---------------------------------------------------------------------------
# Parser: limit extraction
# ---------------------------------------------------------------------------

class TestLimitExtraction:
    def test_number(self):
        assert _extract_limit("liệt kê 10 datasets") == 10

    def test_no_number(self):
        assert _extract_limit("có những dataset nào?") == 10

    def test_capped(self):
        assert _extract_limit("liệt kê 500 datasets") == 100


# ---------------------------------------------------------------------------
# MetadataFilterEngine SQL generation tests
# ---------------------------------------------------------------------------

class TestSQLGeneration:
    def test_exists_owner(self):
        from retrieval.metadata_filter_engine import _build_filter_clause
        f = MetadataFilter(attribute="owner", operation=FilterOperation.EXISTS)
        clause = _build_filter_clause(f)
        assert clause is not None
        assert "IS NOT NULL" in clause
        assert "jsonb_array_length" in clause

    def test_missing_owner(self):
        from retrieval.metadata_filter_engine import _build_filter_clause
        f = MetadataFilter(attribute="owner", operation=FilterOperation.MISSING)
        clause = _build_filter_clause(f)
        assert clause is not None
        assert "IS NULL" in clause

    def test_exists_domain(self):
        from retrieval.metadata_filter_engine import _build_filter_clause
        f = MetadataFilter(attribute="domain", operation=FilterOperation.EXISTS)
        clause = _build_filter_clause(f)
        assert clause is not None
        assert "domain" in clause
        assert "IS NOT NULL" in clause

    def test_equals_domain(self):
        from retrieval.metadata_filter_engine import _build_filter_clause
        f = MetadataFilter(attribute="domain", operation=FilterOperation.EQUALS, value="SALES")
        clause = _build_filter_clause(f)
        assert clause is not None
        assert "LOWER" in clause
        assert "val_domain" in clause

    def test_exists_lineage_edges(self):
        from retrieval.metadata_filter_engine import _build_filter_clause
        f = MetadataFilter(attribute="lineage", operation=FilterOperation.EXISTS)
        clause = _build_filter_clause(f)
        assert clause is not None
        assert "upstreams" in clause
        assert "downstreams" in clause

    def test_unknown_attribute(self):
        from retrieval.metadata_filter_engine import _build_filter_clause
        f = MetadataFilter(attribute="nonexistent", operation=FilterOperation.EXISTS)
        clause = _build_filter_clause(f)
        assert clause is None


# ---------------------------------------------------------------------------
# JSON check builders tests
# ---------------------------------------------------------------------------

class TestJSONChecks:
    def test_json_exists_not_null(self):
        from retrieval.metadata_filter_engine import _json_exists_check
        clause = _json_exists_check("payload", "owners", "not_null")
        assert "IS NOT NULL" in clause
        assert "payload->'owners'" in clause

    def test_json_exists_array(self):
        from retrieval.metadata_filter_engine import _json_exists_check
        clause = _json_exists_check("payload", "tags", "array_not_empty")
        assert "jsonb_array_length" in clause
        assert "::jsonb" in clause

    def test_json_missing_array(self):
        from retrieval.metadata_filter_engine import _json_missing_check
        clause = _json_missing_check("payload", "tags", "array_not_empty")
        assert "jsonb_array_length" in clause
        assert "IS NULL" in clause

    def test_json_exists_lineage(self):
        from retrieval.metadata_filter_engine import _json_exists_check
        clause = _json_exists_check("payload", "upstreams", "lineage_edges")
        assert "upstreams" in clause
        assert "downstreams" in clause
        assert "::jsonb" in clause

    def test_json_missing_lineage(self):
        from retrieval.metadata_filter_engine import _json_missing_check
        clause = _json_missing_check("payload", "upstreams", "lineage_edges")
        assert "upstreams" in clause
        assert "downstreams" in clause


# ---------------------------------------------------------------------------
# MetadataQueryResult tests
# ---------------------------------------------------------------------------

class TestMetadataQueryResult:
    def test_to_dict(self):
        mq = GenericMetadataQuery(
            entity_type="dataset",
            filters=[MetadataFilter(attribute="lineage", operation=FilterOperation.EXISTS)],
            limit=10,
        )
        d = mq.to_dict()
        assert d["entity_type"] == "dataset"
        assert len(d["filters"]) == 1
        assert d["filters"][0]["attribute"] == "lineage"
        assert d["filters"][0]["operation"] == "EXISTS"
        assert d["limit"] == 10

    def test_filter_description_exists(self):
        from retrieval.metadata_filter_engine import MetadataQueryResult
        mq = GenericMetadataQuery(
            entity_type="dataset",
            filters=[MetadataFilter(attribute="lineage", operation=FilterOperation.EXISTS)],
        )
        result = MetadataQueryResult(query=mq, entities=[], total_count=0, returned_count=0)
        desc = result._filter_description(mq.filters[0])
        assert "lineage" in desc
        assert "có" in desc

    def test_filter_description_missing(self):
        from retrieval.metadata_filter_engine import MetadataQueryResult
        mq = GenericMetadataQuery(
            entity_type="dataset",
            filters=[MetadataFilter(attribute="owner", operation=FilterOperation.MISSING)],
        )
        result = MetadataQueryResult(query=mq, entities=[], total_count=0, returned_count=0)
        desc = result._filter_description(mq.filters[0])
        assert "owner" in desc
        assert "thiếu" in desc

    def test_filter_description_equals(self):
        from retrieval.metadata_filter_engine import MetadataQueryResult
        mq = GenericMetadataQuery(
            entity_type="dataset",
            filters=[MetadataFilter(attribute="domain", operation=FilterOperation.EQUALS, value="SALES")],
        )
        result = MetadataQueryResult(query=mq, entities=[], total_count=0, returned_count=0)
        desc = result._filter_description(mq.filters[0])
        assert "domain" in desc
        assert "SALES" in desc


# ---------------------------------------------------------------------------
# Full parser integration tests (22+ required test cases)
# ---------------------------------------------------------------------------

class TestFullParserIntegration:
    """All 22+ required test cases from the spec."""

    REQUIRED_QUERIES = [
        ("dataset nào có lineage?", "lineage", "EXISTS"),
        ("dataset nào có linage?", "lineage", "EXISTS"),  # typo
        ("dataset nào có lineage graph?", "lineage", "EXISTS"),
        ("dataset nào không có owner?", "owner", "MISSING"),
        ("dataset nào thiếu owner?", "owner", "MISSING"),
        ("dataset nào chưa có owner?", "owner", "MISSING"),
        ("dataset nào có owner?", "owner", "EXISTS"),
        ("dataset nào có schema?", "schema", "EXISTS"),
        ("dataset nào có tags?", "tags", "EXISTS"),
        ("dataset nào có glossary?", "glossary", "EXISTS"),
        ("dataset nào có domain?", "domain", "EXISTS"),
        ("dataset nào có description?", "description", "EXISTS"),
        ("dataset nào có platform?", "platform", "EXISTS"),
        ("dataset nào có environment?", "environment", "EXISTS"),
        ("dataset nào có documentation?", "documentation", "EXISTS"),
        ("dataset nào có business description?", "description", "EXISTS"),
        ("dataset nào có business term?", "glossary", "EXISTS"),
        ("dataset nào có data flow?", "lineage", "EXISTS"),
    ]

    @pytest.mark.parametrize("query,expected_attr,expected_op", REQUIRED_QUERIES,
                             ids=[q[0] for q in REQUIRED_QUERIES])
    def test_required_queries(self, query, expected_attr, expected_op):
        q = parse_metadata_query(query)
        assert q is not None, f"Parser returned None for: {query}"
        assert q.entity_type == "dataset"
        assert len(q.filters) >= 1
        assert q.filters[0].attribute == expected_attr
        assert q.filters[0].operation.value == expected_op

    NEGATIVE_QUERIES = [
        "Dataset abc.xyz có tồn tại không?",
        "Dashboard sales_report có lineage không?",
        "Dataset nào gắn term Customer?",
        "Có những glossary terms nào?",
        "Dataset sales.orders có những field nào?",
        "Lĩnh vực tài chính có bao nhiêu datasets?",
        "Có những dataset nào?",
        "Có những document nào trong hệ thống?",
    ]

    @pytest.mark.parametrize("query", NEGATIVE_QUERIES,
                             ids=[q[:30] for q in NEGATIVE_QUERIES])
    def test_negative_queries(self, query):
        q = parse_metadata_query(query)
        assert q is None, f"Parser should return None for: {query}"
