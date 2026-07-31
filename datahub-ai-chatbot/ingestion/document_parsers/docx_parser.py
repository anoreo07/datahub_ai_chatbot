"""DOCX document parser."""
import structlog

from ingestion.document_parsers.base import DocumentParser

log = structlog.get_logger()

try:
    from docx import Document as DocxDocument
    HAS_DOCX_SUPPORT = True
except ImportError:
    HAS_DOCX_SUPPORT = False


class DOCXParser(DocumentParser):
    async def parse(self, content: bytes, filename: str = "") -> str:
        if not HAS_DOCX_SUPPORT:
            log.warning("docx_parser_unavailable", filename=filename)
            return ""

        try:
            import io
            doc = DocxDocument(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            log.warning("docx_parser_failed", error=str(e))
            return ""

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".docx")
