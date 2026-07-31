"""Test DataHubUrlBuilder generates correct URLs."""
from ingestion.url_builder import DataHubUrlBuilder


def test_dataset_url():
    builder = DataHubUrlBuilder(base_url="http://localhost:9002")
    url = builder.dataset_url("urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)")
    assert url.startswith("http://localhost:9002/dataset/")
    assert "urn:li:dataset:" in url


def test_dashboard_url():
    builder = DataHubUrlBuilder(base_url="http://datahub.company.com")
    url = builder.dashboard_url("urn:li:dashboard:MonthlyRevenue")
    assert url.startswith("http://datahub.company.com/dashboard/")


def test_glossary_url():
    builder = DataHubUrlBuilder(base_url="http://localhost:9002")
    url = builder.glossary_url("urn:li:glossaryTerm:Revenue")
    assert url.startswith("http://localhost:9002/glossary/")


def test_document_url():
    builder = DataHubUrlBuilder(base_url="http://localhost:9002")
    url = builder.document_url("urn:li:document:Doc1")
    assert url.startswith("http://localhost:9002/document/")


def test_search_url():
    builder = DataHubUrlBuilder(base_url="http://localhost:9002")
    url = builder.search_url("sales.orders")
    assert "search?q=sales.orders" in url


def test_entity_url_custom_route():
    builder = DataHubUrlBuilder(base_url="http://localhost:9002")
    url = builder.entity_url("chart", "urn:li:chart:Chart1")
    assert url.startswith("http://localhost:9002/chart/")


def test_entity_url_fallback():
    builder = DataHubUrlBuilder(base_url="http://localhost:9002")
    url = builder.entity_url("unknown_type", "urn:li:unknown:Test")
    assert url.startswith("http://localhost:9002/entity/")
