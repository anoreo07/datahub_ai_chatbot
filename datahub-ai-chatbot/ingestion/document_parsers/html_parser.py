"""HTML document parser."""
import re

import structlog

from ingestion.document_parsers.base import DocumentParser

log = structlog.get_logger()

try:
    from bs4 import BeautifulSoup
    HAS_HTML_SUPPORT = True
except ImportError:
    HAS_HTML_SUPPORT = False


class HTMLParser(DocumentParser):
    async def parse(self, content: bytes, filename: str = "") -> str:
        text = content.decode("utf-8", errors="replace")
        if HAS_HTML_SUPPORT:
            try:
                soup = BeautifulSoup(text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                return "\n\n".join(lines)
            except Exception as e:
                log.warning("html_parser_bs_failed", error=str(e))

        return self._fallback_extract(text)

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith((".html", ".htm"))

    def _fallback_extract(self, html_text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", html_text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
