"""PDF document parser."""
import re

import structlog

from ingestion.document_parsers.base import DocumentParser

log = structlog.get_logger()

try:
    import fitz
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False


class PDFParser(DocumentParser):
    async def parse(self, content: bytes, filename: str = "") -> str:
        if HAS_PDF_SUPPORT:
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
                text = "\n\n".join(text_parts)
                if text.strip():
                    return text
            except Exception as e:
                log.warning("pdf_parser_fitz_failed", error=str(e))

        return self._fallback_extract(content)

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def _fallback_extract(self, content: bytes) -> str:
        text = content.decode("latin-1")
        text = re.sub(r"[^\x20-\x7E\n]", "", text)
        if len(text) > 100:
            return text
        return ""
