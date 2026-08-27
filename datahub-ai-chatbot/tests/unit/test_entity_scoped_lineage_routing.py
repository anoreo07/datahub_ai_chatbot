"""Tests for entity-scoped lineage query routing.

Root cause fixed: queries like "Data Lineage Dataset account có Lineage như nào?"
were incorrectly routed to global metadata listing ("list all datasets with lineage")
instead of entity-specific lineage resolution for "account".

The fix ensures:
  1. parse_metadata_query() returns None for entity-specific queries
  2. _extract_entity() correctly extracts single-word entity names after "dataset"
  3. QuerySpec gets scope=ENTITY (not GLOBAL) for entity-specific lineage queries
  4. Global queries like "dataset nào có lineage?" still work correctly
"""

from __future__ import annotations

import pytest

from retrieval.metadata_query_parser import parse_metadata_query
from retrieval.query_parser import _extract_entity, parse_query

# ---------------------------------------------------------------------------
# Entity-specific queries → must NOT be parsed as metadata listing
# (metadata_listing must be False so the LINEAGE handler gets to run)
# ---------------------------------------------------------------------------

class TestEntityScopedNotMetadataListing:
    """Entity-specific lineage queries must NOT trigger global metadata listing."""

    @pytest.mark.parametrize("query", [
        "Data Lineage Dataset account có Lineage như nào?",
        "dataset account có lineage không?",
        "lineage của dataset account",
        "dashboard revenue có lineage không?",
        "Dataset fact_sales có owner không?",
        "dataset sales.orders có schema không?",
        "Data Lineage Dataset dim_product có Lineage như nào?",
        "Lineage của dataset fact_order như thế nào?",
        "dataset category có upstream nào?",
        "dataset payment có downstream nào?",
    ])
    def test_entity_specific_not_listing(self, query: str) -> None:
        mq = parse_metadata_query(query)
        assert mq is None, (
            f"parse_metadata_query() should return None for entity-specific query: {query}"
        )

    @pytest.mark.parametrize("query,expected_entity", [
        ("Data Lineage Dataset account có Lineage như nào?", "account"),
        ("dataset account có lineage không?", "account"),
        ("lineage của dataset account", "account"),
        ("dashboard revenue có lineage không?", "revenue"),
        ("Dataset fact_sales có owner không?", "fact_sales"),
        ("dataset sales.orders có schema không?", "sales.orders"),
        ("Data Lineage Dataset dim_product có Lineage như nào?", "dim_product"),
        ("Lineage của dataset fact_order như thế nào?", "fact_order"),
        ("dataset category có upstream nào?", "category"),
        ("dataset payment có downstream nào?", "payment"),
    ])
    def test_entity_extraction(self, query: str, expected_entity: str) -> None:
        entity = _extract_entity(query)
        assert entity == expected_entity, (
            f"_extract_entity({query!r}) = {entity!r}, expected {expected_entity!r}"
        )

    @pytest.mark.parametrize("query", [
        "Data Lineage Dataset account có Lineage như nào?",
        "dataset account có lineage không?",
        "lineage của dataset account",
    ])
    def test_query_spec_entity_scope(self, query: str) -> None:
        spec = parse_query(query)
        assert spec.scope.value == "ENTITY", (
            f"QuerySpec scope should be ENTITY for {query!r}, got {spec.scope.value}"
        )
        assert spec.entity_name is not None, (
            f"QuerySpec entity_name should not be None for {query!r}"
        )
        assert "account" in (spec.entity_name or "").lower(), (
            f"QuerySpec entity_name should contain 'account' for {query!r}, "
            f"got {spec.entity_name!r}"
        )


# ---------------------------------------------------------------------------
# Global queries → must still be parsed as metadata listing
# ---------------------------------------------------------------------------

class TestGlobalLineageStillWorks:
    """Global lineage queries must still trigger metadata listing."""

    @pytest.mark.parametrize("query", [
        "dataset nào có lineage?",
        "liệt kê các dataset có lineage",
        "dataset có lineage không?",
        "show datasets có lineage",
    ])
    def test_global_lineage_is_listing(self, query: str) -> None:
        mq = parse_metadata_query(query)
        assert mq is not None, (
            f"parse_metadata_query() should return a query for global listing: {query}"
        )
        assert mq.entity_type == "dataset"
        assert len(mq.filters) >= 1
        assert mq.filters[0].attribute == "lineage"

    @pytest.mark.parametrize("query", [
        "dataset nào có lineage?",
        "liệt kê các dataset có lineage",
        "dataset có lineage không?",
    ])
    def test_global_query_no_entity(self, query: str) -> None:
        entity = _extract_entity(query)
        assert entity is None, (
            f"_extract_entity({query!r}) should be None for global query, "
            f"got {entity!r}"
        )

    @pytest.mark.parametrize("query", [
        "dataset nào có lineage?",
        "liệt kê các dataset có lineage",
    ])
    def test_global_query_spec_global_scope(self, query: str) -> None:
        spec = parse_query(query)
        assert spec.scope.value == "GLOBAL", (
            f"QuerySpec scope should be GLOBAL for {query!r}, got {spec.scope.value}"
        )


# ---------------------------------------------------------------------------
# Edge cases: other entity types with single-word names
# ---------------------------------------------------------------------------

class TestOtherEntityTypes:
    """Single-word entity names work for all entity types, not just lineage."""

    @pytest.mark.parametrize("query,expected_entity", [
        ("dashboard sales có lineage không?", "sales"),
        ("glossary term revenue có description không?", "revenue"),
        ("document policy có tags không?", "policy"),
    ])
    def test_entity_extraction_other_types(self, query: str, expected_entity: str) -> None:
        entity = _extract_entity(query)
        assert entity == expected_entity, (
            f"_extract_entity({query!r}) = {entity!r}, expected {expected_entity!r}"
        )

    @pytest.mark.parametrize("query", [
        "dashboard sales có lineage không?",
        "glossary term revenue có description không?",
        "document policy có tags không?",
    ])
    def test_not_listing_other_types(self, query: str) -> None:
        mq = parse_metadata_query(query)
        assert mq is None, (
            f"parse_metadata_query() should return None for entity-specific: {query}"
        )


# ---------------------------------------------------------------------------
# Variant queries from the bug report
# ---------------------------------------------------------------------------

class TestLineageQueryVariants:
    """All entity-scoped lineage query variants from the bug report."""

    VARIANTS = [
        ("dataset dim_warehouse có lineage không?", "dim_warehouse"),
        ("lineage của dataset fact_order là gì?", "fact_order"),
        ("dataset account có những upstream nào?", "account"),
        ("dataset payment có những downstream nào?", "payment"),
    ]

    @pytest.mark.parametrize("query,expected_entity", VARIANTS,
                             ids=[v[0] for v in VARIANTS])
    def test_variant_entity_extraction(self, query: str, expected_entity: str) -> None:
        entity = _extract_entity(query)
        assert entity == expected_entity, (
            f"_extract_entity({query!r}) = {entity!r}, expected {expected_entity!r}"
        )

    @pytest.mark.parametrize("query", [
        "dataset dim_warehouse có lineage không?",
        "lineage của dataset fact_order là gì?",
        "dataset account có những upstream nào?",
        "dataset payment có những downstream nào?",
    ])
    def test_entity_specific_not_listing(self, query: str) -> None:
        mq = parse_metadata_query(query)
        assert mq is None, (
            f"parse_metadata_query() should return None for: {query}"
        )


# ---------------------------------------------------------------------------
# Regression: snake_case and dotted entities still work
# ---------------------------------------------------------------------------

class TestExistingEntityPatterns:
    """Existing snake_case and dotted entity patterns still work correctly."""

    @pytest.mark.parametrize("query,expected_entity", [
        ("dim_warehouse có lineage không?", "dim_warehouse"),
        ("fact_sales có owner không?", "fact_sales"),
        ("sales.orders có schema không?", "sales.orders"),
        ("dms.stg.stg_contact có lineage không?", "dms.stg.stg_contact"),
    ])
    def test_snake_dotted_still_extracted(self, query: str, expected_entity: str) -> None:
        entity = _extract_entity(query)
        assert entity == expected_entity

    @pytest.mark.parametrize("query", [
        "dim_warehouse có lineage không?",
        "fact_sales có owner không?",
        "sales.orders có schema không?",
    ])
    def test_snake_dotted_not_listing(self, query: str) -> None:
        mq = parse_metadata_query(query)
        assert mq is None
