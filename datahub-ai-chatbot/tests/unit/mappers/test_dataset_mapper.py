"""Test DatasetMapper maps raw GraphQL response to CanonicalEntity."""
from ingestion.mappers.dataset import DatasetMapper
from ingestion.models import CanonicalEntity
from ingestion.url_builder import DataHubUrlBuilder

RAW_DATASET = {
    "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)",
    "name": "sales.orders",
    "description": "Bảng lưu thông tin đơn hàng đã xác nhận.",
    "properties": {
        "description": "Bảng lưu thông tin đơn hàng đã xác nhận.",
        "customProperties": {"key1": "value1"},
        "environment": "PROD",
    },
    "platform": {"name": "snowflake", "urn": "urn:li:dataPlatform:snowflake"},
    "schemaMetadata": {
        "fields": [
            {
                "fieldPath": "order_id",
                "description": "Mã đơn hàng",
                "nativeDataType": "string",
                "type": "String",
                "nullable": False,
                "isPartOfKey": True,
            },
            {
                "fieldPath": "amount",
                "description": "Số tiền",
                "nativeDataType": "decimal",
                "type": "Decimal",
                "nullable": True,
                "isPartOfKey": False,
            },
        ]
    },
    "ownership": {
        "owners": [
            {
                "type": "DATA_OWNER",
                "owner": {
                    "username": "sale_analytics",
                    "urn": "urn:li:corpuser:sale_analytics",
                    "info": {"displayName": "Sales Analytics", "email": "sale@company.com"},
                },
            }
        ]
    },
    "lineage": {
        "upstream": {
            "total": 1,
            "relationships": [
                {
                    "entity": {
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,customer_events,PROD)",
                        "type": "dataset",
                        "name": "customer_events",
                    }
                }
            ],
        },
        "downstream": {
            "total": 1,
            "relationships": [
                {
                    "entity": {
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.monthly_revenue,PROD)",
                        "type": "dataset",
                        "name": "finance.monthly_revenue",
                    }
                }
            ],
        },
    },
    "domain": {
        "domains": [
            {
                "domain": {
                    "urn": "urn:li:domain:Sales",
                    "name": "Sales",
                    "properties": {"name": "Sales", "description": "Sales domain"},
                }
            }
        ]
    },
    "glossaryTerms": {
        "terms": [
            {"term": {"urn": "urn:li:glossaryTerm:Revenue", "name": "Revenue"}},
        ]
    },
    "tags": {
        "tags": [
            {"tag": {"name": "PII", "urn": "urn:li:tag:PII"}},
        ]
    },
    "lastModified": {"time": 1700000000000},
}


def test_dataset_mapper_returns_canonical_entity():
    mapper = DatasetMapper()
    url_builder = DataHubUrlBuilder(base_url="http://localhost:9002")

    result = mapper.to_canonical(RAW_DATASET, url_builder)

    assert isinstance(result, CanonicalEntity)
    assert result.urn == RAW_DATASET["urn"]
    assert result.entity_type == "dataset"
    assert result.name == "sales.orders"
    assert result.display_name == "sales.orders"
    assert result.description == RAW_DATASET["description"]
    assert result.platform == "snowflake"
    assert result.environment == "PROD"
    assert result.domain == "Sales"
    assert not result.deleted


def test_dataset_mapper_owners():
    mapper = DatasetMapper()
    result = mapper.to_canonical(RAW_DATASET)
    assert len(result.owners) == 1
    assert result.owners[0].name == "sale_analytics"
    assert result.owners[0].type == "DATA_OWNER"


def test_dataset_mapper_schema_fields():
    mapper = DatasetMapper()
    result = mapper.to_canonical(RAW_DATASET)
    assert len(result.schema_fields) == 2
    order_id = result.schema_fields[0]
    assert order_id.name == "order_id"
    assert order_id.type == "string"
    assert order_id.nullable is False
    assert order_id.is_primary_key is True
    amount = result.schema_fields[1]
    assert amount.name == "amount"
    assert amount.type == "decimal"
    assert amount.nullable is True
    assert amount.is_primary_key is False


def test_dataset_mapper_lineage():
    mapper = DatasetMapper()
    result = mapper.to_canonical(RAW_DATASET)
    assert len(result.upstreams) == 1
    assert "customer_events" in result.upstreams[0]
    assert len(result.downstreams) == 1
    assert "monthly_revenue" in result.downstreams[0]


def test_dataset_mapper_glossary_terms():
    mapper = DatasetMapper()
    result = mapper.to_canonical(RAW_DATASET)
    assert len(result.glossary_terms) == 1
    assert "urn:li:glossaryTerm:Revenue" in result.glossary_terms


def test_dataset_mapper_tags():
    mapper = DatasetMapper()
    result = mapper.to_canonical(RAW_DATASET)
    assert len(result.tags) == 1
    assert "PII" in result.tags


def test_dataset_mapper_url():
    mapper = DatasetMapper()
    url_builder = DataHubUrlBuilder(base_url="http://datahub.company.com")
    result = mapper.to_canonical(RAW_DATASET, url_builder)
    assert result.source_url is not None
    assert "datahub.company.com" in result.source_url
    assert result.source_url.endswith(RAW_DATASET["urn"])


def test_dataset_mapper_raw_properties():
    mapper = DatasetMapper()
    result = mapper.to_canonical(RAW_DATASET)
    assert result.raw_properties == {"key1": "value1"}


def test_normalize_field_path():
    from ingestion.mappers.dataset import _normalize_field_path
    # V2 schema format
    assert _normalize_field_path("[version=2.0].[type=string].bf_ext_order_id") == "bf_ext_order_id"
    # Nested struct format
    assert _normalize_field_path("[version=2.0].[type=struct].outer.[type=string].inner") == "inner"
    # Normal field
    assert _normalize_field_path("amount") == "amount"
    # Empty
    assert _normalize_field_path("") == ""
    # Nested without bracket
    assert _normalize_field_path("a.b.c") == "a.b.c"

