"""Test DataHubSourceFactory selects correct source based on settings."""
from unittest.mock import patch

from ingestion.factory import DataHubSourceFactory
from ingestion.graphql_source import GraphQLDataHubSource
from ingestion.mock_source import MockDataHubSource


def test_factory_returns_mock_source():
    with patch("config.settings.settings.USE_MOCK_DATAHUB", True):
        source = DataHubSourceFactory.create()
        assert isinstance(source, MockDataHubSource)


def test_factory_returns_graphql_source():
    with patch("config.settings.settings.USE_MOCK_DATAHUB", False):
        source = DataHubSourceFactory.create()
        assert isinstance(source, GraphQLDataHubSource)


def test_mock_source_healthcheck():
    source = MockDataHubSource()
    import asyncio
    result = asyncio.run(source.healthcheck())
    assert result is True


def test_mock_source_list_entities():
    source = MockDataHubSource()
    import asyncio
    page = asyncio.run(source.list_entities("dataset"))
    assert page.total is not None
    assert len(page.items) > 0


def test_mock_source_get_entity():
    source = MockDataHubSource()
    import asyncio
    page = asyncio.run(source.list_entities("dataset"))
    if page.items:
        urn = page.items[0].get("urn", "")
        entity = asyncio.run(source.get_entity(urn))
        assert entity is not None
        assert entity.urn == urn


def test_mock_source_close():
    source = MockDataHubSource()
    import asyncio
    asyncio.run(source.close())
    assert True
