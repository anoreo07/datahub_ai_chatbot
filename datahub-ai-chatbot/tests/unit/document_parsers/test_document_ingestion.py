"""Tests for document ingestion service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingestion.document_ingestion import DocumentIngestionResult, DocumentIngestionService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = DocumentIngestionService(mock_session)
    svc._entity_repo = AsyncMock()
    svc._chunk_repo = AsyncMock()
    svc._vector_store = AsyncMock()
    svc._embedder = AsyncMock()
    svc._embedder.embed = AsyncMock(return_value=[[0.1] * 384])
    svc._embedder.model_name = "mock"
    svc._ssrf = MagicMock()
    svc._http_client = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_ingest_from_url_ssrf_rejected(service):
    service._ssrf.validate = MagicMock(return_value=False)
    result = await service.ingest_from_url("http://evil.com/malware.pdf")
    assert result.success is False
    assert "SSRF" in result.error


@pytest.mark.asyncio
async def test_ingest_from_url_rejected_no_parser(service):
    service._ssrf.validate = MagicMock(return_value=True)
    response = AsyncMock()
    response.content = b"test content"
    response.raise_for_status = MagicMock()
    service._http_client.get = AsyncMock(return_value=response)
    with patch("ingestion.document_ingestion.get_parser", return_value=None):
        result = await service.ingest_from_url("https://example.com/file.xyz")
        assert result.success is False
        assert "No parser" in result.error


@pytest.mark.asyncio
async def test_ingest_from_url_success(service):
    service._ssrf.validate = MagicMock(return_value=True)
    response = AsyncMock()
    response.content = b"Document content for testing."
    response.raise_for_status = MagicMock()
    service._http_client.get = AsyncMock(return_value=response)
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(return_value="Extracted text content")
    mock_parser.supports = MagicMock(return_value=True)
    with patch("ingestion.document_ingestion.get_parser", return_value=mock_parser):
        result = await service.ingest_from_url("https://example.com/doc.pdf")
        assert result.success is True
        assert result.entity_urn.startswith("urn:li:document:")
        assert result.chunks_count >= 1


@pytest.mark.asyncio
async def test_ingest_from_file_success(service):
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(return_value="File content for testing.")
    mock_parser.supports = MagicMock(return_value=True)
    with patch("ingestion.document_ingestion.get_parser", return_value=mock_parser):
        result = await service.ingest_from_file(b"file bytes", "test.txt", title="Test Doc")
        assert result.success is True
        assert result.title == "Test Doc"


@pytest.mark.asyncio
async def test_ingest_empty_content(service):
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(return_value="")
    mock_parser.supports = MagicMock(return_value=True)
    with patch("ingestion.document_ingestion.get_parser", return_value=mock_parser):
        result = await service.ingest_from_file(b"  ", "empty.txt")
        assert result.success is False
        assert "Empty content" in result.error


@pytest.mark.asyncio
async def test_result_defaults():
    r = DocumentIngestionResult()
    assert r.success is False
    assert r.chunks_count == 0
    assert r.error == ""


@pytest.mark.asyncio
async def test_ingest_from_url_download_failure(service):
    service._ssrf.validate = MagicMock(return_value=True)
    service._http_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    result = await service.ingest_from_url("https://example.com/doc.pdf")
    assert result.success is False
    assert "Download failed" in result.error


@pytest.mark.asyncio
async def test_close(service):
    service._http_client.aclose = AsyncMock()
    await service.close()
    service._http_client.aclose.assert_awaited_once()
