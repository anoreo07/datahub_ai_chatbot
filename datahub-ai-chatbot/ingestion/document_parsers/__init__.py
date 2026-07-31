"""Document parser registry."""
from ingestion.document_parsers.base import DocumentParser
from ingestion.document_parsers.docx_parser import DOCXParser
from ingestion.document_parsers.html_parser import HTMLParser
from ingestion.document_parsers.mock_parser import MockDocumentParser
from ingestion.document_parsers.pdf_parser import PDFParser

_BUILTIN_PARSERS: list[DocumentParser] = [
    PDFParser(),
    DOCXParser(),
    HTMLParser(),
]


def get_parser(filename: str, *, use_mock: bool = False) -> DocumentParser | None:
    if use_mock:
        return MockDocumentParser()
    for parser in _BUILTIN_PARSERS:
        if parser.supports(filename):
            return parser
    return None


def list_supported_extensions() -> list[str]:
    return [".pdf", ".docx", ".html", ".htm"]
