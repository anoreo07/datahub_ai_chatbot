"""Tests for EntityItem metadata mapping.

Validates that the EntityItem Pydantic schema correctly serialises
metadata fields (entity_type, platform, domain, description, environment)
so the frontend EvidencePanel can display real data instead of
"Chưa có metadata".
"""

import pytest

from app.schemas.chat import ChatResponse, EntityItem, LineageNode


class TestEntityItemSchema:
    """EntityItem schema accepts and serialises all metadata fields."""

    def test_defaults(self) -> None:
        e = EntityItem(urn="urn:li:dataset:(abc,def)", name="my_table")
        assert e.urn == "urn:li:dataset:(abc,def)"
        assert e.name == "my_table"
        assert e.url is None
        assert e.entity_type is None
        assert e.platform is None
        assert e.domain is None
        assert e.description is None
        assert e.environment is None

    def test_full_metadata(self) -> None:
        e = EntityItem(
            urn="urn:li:dataset:(abc,def)",
            name="my_table",
            url="https://datahub.example.com/urn",
            entity_type="dataset",
            platform="bigquery",
            domain="SALES",
            description="Daily sales aggregation",
            environment="PROD",
        )
        d = e.model_dump()
        assert d["entity_type"] == "dataset"
        assert d["platform"] == "bigquery"
        assert d["domain"] == "SALES"
        assert d["description"] == "Daily sales aggregation"
        assert d["environment"] == "PROD"

    def test_partial_metadata(self) -> None:
        e = EntityItem(
            urn="urn:li:dataset:(abc,def)",
            name="my_table",
            entity_type="dataset",
            domain="FINANCE",
        )
        d = e.model_dump()
        assert d["entity_type"] == "dataset"
        assert d["domain"] == "FINANCE"
        assert d["platform"] is None
        assert d["description"] is None
        assert d["environment"] is None

    def test_json_serialisation_includes_new_fields(self) -> None:
        e = EntityItem(
            urn="urn:li:dataset:(abc,def)",
            name="my_table",
            entity_type="dashboard",
            platform="looker",
            domain="MARKETING",
        )
        json_str = e.model_dump_json()
        assert '"entity_type":"dashboard"' in json_str
        assert '"platform":"looker"' in json_str
        assert '"domain":"MARKETING"' in json_str

    def test_backward_compatible_old_clients(self) -> None:
        """Old clients that don't know about new fields still work."""
        e = EntityItem(urn="urn:li:dataset:(abc,def)", name="my_table")
        d = e.model_dump()
        # Old fields present
        assert "urn" in d
        assert "name" in d
        assert "url" in d
        # New fields are None, will be omitted or ignored by old clients
        assert d["entity_type"] is None
        assert d["platform"] is None


class TestEntityItemFromEntityORM:
    """Simulate EntityItem construction from Entity ORM objects."""

    def test_from_entity_with_all_fields(self) -> None:
        class FakeEntity:
            urn = "urn:li:dataset:(abc,def)"
            name = "raw_table"
            display_name = "Raw Table"
            entity_type = "dataset"
            platform = "snowflake"
            domain = "ANALYTICS"
            description = "Raw transaction data"
            environment = "PROD"
            datahub_url = "https://datahub.example.com/abc"

        e = FakeEntity()
        item = EntityItem(
            urn=e.urn, name=e.display_name or e.name, url=e.datahub_url,
            entity_type=e.entity_type, platform=e.platform,
            domain=e.domain, description=e.description, environment=e.environment,
        )
        assert item.entity_type == "dataset"
        assert item.platform == "snowflake"
        assert item.domain == "ANALYTICS"
        assert item.description == "Raw transaction data"
        assert item.environment == "PROD"

    def test_from_entity_without_optional_fields(self) -> None:
        class SparseEntity:
            urn = "urn:li:dataset:(abc,def)"
            name = "raw_table"
            display_name = None
            entity_type = "dataset"
            platform = None
            domain = None
            description = None
            environment = None
            datahub_url = None

        e = SparseEntity()
        item = EntityItem(
            urn=e.urn, name=e.display_name or e.name, url=e.datahub_url,
            entity_type=e.entity_type, platform=e.platform,
            domain=e.domain, description=e.description, environment=e.environment,
        )
        assert item.entity_type == "dataset"
        assert item.platform is None
        assert item.domain is None
        assert item.description is None
        assert item.environment is None


class TestEntityItemFromSearchResult:
    """Simulate EntityItem construction from SearchResult objects."""

    def test_from_search_result_with_payload(self) -> None:
        class FakeSearchResult:
            urn = "urn:li:dataset:(abc,def)"
            entity_type = "dataset"
            name = "my_table"
            score = 0.95
            snippet = "..."
            datahub_url = "https://datahub.example.com/abc"
            payload = {
                "platform": "bigquery",
                "domain": "SALES",
                "description": "Sales data",
                "environment": "PROD",
            }

        r = FakeSearchResult()
        item = EntityItem(
            urn=r.urn, name=r.name, url=r.datahub_url,
            entity_type=r.entity_type,
            platform=(r.payload or {}).get("platform"),
            domain=(r.payload or {}).get("domain"),
            description=(r.payload or {}).get("description"),
            environment=(r.payload or {}).get("environment"),
        )
        assert item.entity_type == "dataset"
        assert item.platform == "bigquery"
        assert item.domain == "SALES"
        assert item.description == "Sales data"
        assert item.environment == "PROD"

    def test_from_search_result_empty_payload(self) -> None:
        class FakeSearchResult:
            urn = "urn:li:dataset:(abc,def)"
            entity_type = "dataset"
            name = "my_table"
            datahub_url = None
            payload = {}

        r = FakeSearchResult()
        item = EntityItem(
            urn=r.urn, name=r.name, url=r.datahub_url,
            entity_type=r.entity_type,
            platform=(r.payload or {}).get("platform"),
            domain=(r.payload or {}).get("domain"),
            description=(r.payload or {}).get("description"),
            environment=(r.payload or {}).get("environment"),
        )
        assert item.entity_type == "dataset"
        assert item.platform is None
        assert item.domain is None
        assert item.description is None
        assert item.environment is None

    def test_from_search_result_none_payload(self) -> None:
        class FakeSearchResult:
            urn = "urn:li:dataset:(abc,def)"
            entity_type = "dashboard"
            name = "my_dashboard"
            datahub_url = None
            payload = None

        r = FakeSearchResult()
        item = EntityItem(
            urn=r.urn, name=r.name, url=r.datahub_url,
            entity_type=r.entity_type,
            platform=(r.payload or {}).get("platform"),
            domain=(r.payload or {}).get("domain"),
            description=(r.payload or {}).get("description"),
            environment=(r.payload or {}).get("environment"),
        )
        assert item.entity_type == "dashboard"
        assert item.platform is None


class TestEntityItemFromLineageNode:
    """Simulate EntityItem construction from LineageNode objects."""

    def test_from_lineage_node(self) -> None:
        node = LineageNode(
            name="upstream_table",
            urn="urn:li:dataset:(xyz,uvw)",
            url="https://datahub.example.com/xyz",
            entity_type="dataset",
        )
        item = EntityItem(
            urn=node.urn, name=node.name, url=node.url,
            entity_type=node.entity_type,
        )
        assert item.entity_type == "dataset"
        assert item.platform is None

    def test_from_lineage_node_default_type(self) -> None:
        node = LineageNode(name="upstream", urn="urn:li:dataset:(x,y)")
        item = EntityItem(urn=node.urn, name=node.name, url=node.url)
        assert item.entity_type is None


class TestEntityItemVariants:
    """Test different entity types through the schema."""

    @pytest.mark.parametrize("entity_type,expected", [
        ("dataset", "dataset"),
        ("dashboard", "dashboard"),
        ("glossary_term", "glossary_term"),
        ("chart", "chart"),
        ("dataFlow", "dataFlow"),
        ("dataJob", "dataJob"),
        ("container", "container"),
    ])
    def test_entity_type_preserved(self, entity_type: str, expected: str) -> None:
        e = EntityItem(urn=f"urn:li:{entity_type}:(a,b)", name="test", entity_type=entity_type)
        assert e.entity_type == expected


class TestChatResponseWithMetadata:
    """ChatResponse carries EntityItem with metadata through to API."""

    def test_chat_response_entities_have_metadata(self) -> None:
        resp = ChatResponse(
            answer="Here is info about the dataset",
            intent="DATASET_DETAILS",
            entities=[
                EntityItem(
                    urn="urn:li:dataset:(abc,def)",
                    name="sales_daily",
                    url="https://datahub.example.com/abc",
                    entity_type="dataset",
                    platform="bigquery",
                    domain="SALES",
                    description="Daily sales data",
                    environment="PROD",
                ),
            ],
        )
        e = resp.entities[0]
        d = e.model_dump()
        assert d["entity_type"] == "dataset"
        assert d["platform"] == "bigquery"
        assert d["domain"] == "SALES"
        assert d["description"] == "Daily sales data"
        assert d["environment"] == "PROD"

    def test_chat_response_empty_entities(self) -> None:
        resp = ChatResponse(answer="Hello", intent="GENERAL")
        assert resp.entities == []

    def test_chat_response_mixed_metadata(self) -> None:
        resp = ChatResponse(
            answer="Multiple datasets found",
            entities=[
                EntityItem(urn="urn:li:dataset:(a,b)", name="t1",
                           entity_type="dataset", platform="snowflake"),
                EntityItem(urn="urn:li:dataset:(c,d)", name="t2"),
                EntityItem(urn="urn:li:dashboard:(e,f)", name="d1",
                           entity_type="dashboard", domain="FINANCE"),
            ],
        )
        assert len(resp.entities) == 3
        assert resp.entities[0].platform == "snowflake"
        assert resp.entities[1].platform is None
        assert resp.entities[2].domain == "FINANCE"
