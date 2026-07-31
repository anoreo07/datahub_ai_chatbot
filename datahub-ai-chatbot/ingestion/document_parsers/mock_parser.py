"""Mock document parser for testing."""
from ingestion.document_parsers.base import DocumentParser


class MockDocumentParser(DocumentParser):
    async def parse(self, content: bytes, filename: str = "") -> str:
        return content.decode("utf-8", errors="replace")

    def supports(self, filename: str) -> bool:
        return True
