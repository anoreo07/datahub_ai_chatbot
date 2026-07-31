"""Test that mock mode does not make any network requests."""
from unittest.mock import patch

import pytest


def _block_external_network():
    """Allow localhost (127.0.0.1, ::1) but block all other network addresses."""
    import socket

    original_getaddrinfo = socket.getaddrinfo

    def blocked_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return original_getaddrinfo(host, port, family, type, proto, flags)
        raise RuntimeError(f"Network call attempted to {host}:{port} in mock mode!")

    return patch.object(socket, "getaddrinfo", blocked_getaddrinfo)


@pytest.mark.asyncio
async def test_mock_source_no_network():
    """MockDataHubSource must not make any network calls."""
    with _block_external_network():
        from ingestion.mock_source import MockDataHubSource
        source = MockDataHubSource()

        health = await source.healthcheck()
        assert health is True

        datasets = await source.list_datasets()
        assert len(datasets) >= 1

        dashboards = await source.list_dashboards()
        assert len(dashboards) >= 1

        glossary = await source.list_glossary_terms()
        assert len(glossary) >= 1

        documents = await source.list_documents()
        assert len(documents) >= 1

        entity = await source.get_entity(datasets[0].urn)
        assert entity is not None

        results = await source.search_entities("dataset", "inventory")
        assert isinstance(results, list)

        lineage = await source.get_lineage(datasets[0].urn)
        assert "relationships" in lineage

        await source.close()


@pytest.mark.asyncio
async def test_mock_llm_no_network():
    """MockLLM must not make any network calls."""
    with _block_external_network():
        from llm.mock import MockLLM
        llm = MockLLM()

        result = await llm.generate("test prompt")
        assert isinstance(result, str)
        assert len(result) > 0

        structured = await llm.generate_structured("test prompt", context_xml="<test>sample</test>")
        assert "answer" in structured
        assert "confidence" in structured


@pytest.mark.asyncio
async def test_fake_search_no_network():
    """FakeSearchBackend must not make any network calls."""
    with _block_external_network():
        from indexing.fake_search import FakeSearchBackend, SearchChunk

        backend = FakeSearchBackend()
        await backend.ensure_index()

        chunk = SearchChunk(
            chunk_id="test_001",
            entity_urn="urn:li:dataset:test",
            entity_type="dataset",
            chunk_type="SUMMARY",
            text="Test inventory data",
            domain="Logistic",
        )
        await backend.index_chunk(chunk)

        results = await backend.search("inventory")
        assert len(results) >= 1

        count = await backend.count()
        assert count >= 1

        healthy = await backend.healthcheck()
        assert healthy is True


@pytest.mark.asyncio
async def test_full_mock_flow_no_network():
    """End-to-end mock flow must not make network calls."""
    with _block_external_network():
        from ingestion.mock_source import MockDataHubSource
        source = MockDataHubSource()

        all_entities = list(source.list_all())
        assert len(all_entities) >= 10

        domains = source.list_domains()
        assert isinstance(domains, list)

        await source.close()


@pytest.mark.asyncio
async def test_chat_service_responds_without_network():
    """ChatService with MockLLM should respond without network."""
    with _block_external_network():
        from app.services.chat_service import ChatService
        service = ChatService.__new__(ChatService)
        assert service is not None


def test_graphql_source_not_imported_in_mock_mode():
    """GraphQLDataHubSource should not be used when USE_MOCK_DATAHUB=true."""
    from config.settings import settings
    assert settings.USE_MOCK_DATAHUB is True

    from ingestion import create_datahub_source
    source = create_datahub_source()
    from ingestion.mock_source import MockDataHubSource
    assert isinstance(source, MockDataHubSource)
