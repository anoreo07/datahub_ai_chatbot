"""Test entity type routing in GraphQLDataHubSource."""
import pytest

from ingestion.graphql_source import GraphQLDataHubSource


@pytest.mark.parametrize(
    "urn, expected",
    [
        ("urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)", "dataset"),
        ("urn:li:glossaryTerm:NetRevenue", "glossary_term"),
        ("urn:li:glossaryNode:Finance", "glossary_node"),
        ("urn:li:document:MonthlyRevenueMethodology", "document"),
        ("urn:li:dashboard:(looker,MonthlyRevenue)", "dashboard"),
        ("urn:li:chart:(looker,chart_1)", "chart"),
        ("urn:li:container:(postgres,my_schema)", "container"),
    ],
)
def test_urn_to_type(urn: str, expected: str) -> None:
    assert GraphQLDataHubSource._urn_to_type(urn) == expected


def test_search_hit_to_canonical_uses_type_field() -> None:
    source = GraphQLDataHubSource.__new__(GraphQLDataHubSource)
    hit = {
        "urn": "urn:li:document:MonthlyRevenueMethodology",
        "type": "DOCUMENT",
        "info": {"title": "Monthly Revenue Methodology"},
    }
    canonical = source._search_hit_to_canonical(hit)
    assert canonical is not None
    assert canonical.entity_type == "document"


def test_search_hit_to_canonical_falls_back_to_urn() -> None:
    source = GraphQLDataHubSource.__new__(GraphQLDataHubSource)
    hit = {
        "urn": "urn:li:glossaryNode:Finance",
        "properties": {"name": "Finance"},
    }
    canonical = source._search_hit_to_canonical(hit)
    assert canonical is not None
    assert canonical.entity_type == "glossary_node"
