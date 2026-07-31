"""Tests for document parsers."""
import pytest

from ingestion.document_parsers import get_parser, list_supported_extensions
from ingestion.document_parsers.docx_parser import DOCXParser
from ingestion.document_parsers.html_parser import HTMLParser
from ingestion.document_parsers.mock_parser import MockDocumentParser
from ingestion.document_parsers.pdf_parser import PDFParser


def test_get_pdf_parser():
    parser = get_parser("document.pdf")
    assert parser is not None
    assert isinstance(parser, PDFParser)


def test_get_docx_parser():
    parser = get_parser("document.docx")
    assert parser is not None
    assert isinstance(parser, DOCXParser)


def test_get_html_parser():
    parser = get_parser("page.html")
    assert parser is not None
    assert isinstance(parser, HTMLParser)


def test_get_parser_without_extension():
    parser = get_parser("noextension")
    assert parser is None


def test_get_mock_parser():
    parser = get_parser("anything.xyz", use_mock=True)
    assert isinstance(parser, MockDocumentParser)


def test_list_supported_extensions():
    exts = list_supported_extensions()
    assert ".pdf" in exts
    assert ".docx" in exts
    assert ".html" in exts


@pytest.mark.asyncio
async def test_pdf_parser_empty():
    parser = PDFParser()
    text = await parser.parse(b"", "test.pdf")
    assert text == ""


@pytest.mark.asyncio
async def test_pdf_parser_plain_text():
    parser = PDFParser()
    text = await parser.parse(b"Hello PDF World", "test.pdf")
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_pdf_supports():
    parser = PDFParser()
    assert parser.supports("file.pdf")
    assert parser.supports("FILE.PDF")
    assert not parser.supports("file.txt")


@pytest.mark.asyncio
async def test_html_parser_basic():
    parser = HTMLParser()
    html = b"<html><body><p>Hello World</p></body></html>"
    text = await parser.parse(html, "test.html")
    assert "Hello World" in text


@pytest.mark.asyncio
async def test_html_parser_strips_tags():
    parser = HTMLParser()
    html = b"<html><body><script>alert('xss')</script><p>Content</p></body></html>"
    text = await parser.parse(html, "test.html")
    assert "Content" in text
    assert "<script>" not in text


@pytest.mark.asyncio
async def test_html_supports():
    parser = HTMLParser()
    assert parser.supports("page.html")
    assert parser.supports("page.htm")
    assert not parser.supports("page.xml")


@pytest.mark.asyncio
async def test_html_fallback():
    parser = HTMLParser()
    html = b"<p>Simple text</p>"
    text = await parser.parse(html, "test.html")
    assert "Simple text" in text


@pytest.mark.asyncio
async def test_docx_parser_empty():
    parser = DOCXParser()
    text = await parser.parse(b"", "test.docx")
    assert text == ""


@pytest.mark.asyncio
async def test_docx_supports():
    parser = DOCXParser()
    assert parser.supports("file.docx")
    assert not parser.supports("file.doc")


@pytest.mark.asyncio
async def test_mock_parser():
    parser = MockDocumentParser()
    text = await parser.parse(b"mock content", "test.xyz")
    assert text == "mock content"
