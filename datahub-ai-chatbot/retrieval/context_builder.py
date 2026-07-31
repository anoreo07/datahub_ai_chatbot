from collections.abc import Sequence

from config.settings import settings
from retrieval.hybrid_search import SearchResult

MAX_CHUNKS = settings.MAX_CONTEXT_CHUNKS
MAX_CHARS = settings.MAX_CONTEXT_CHARACTERS


class ContextDocument:
    def __init__(self, cid: str, source_type: str, entity_urn: str, entity_name: str,
                 content: str, url: str | None = None,
                 page: int | None = None, section: str | None = None) -> None:
        self.cid = cid
        self.source_type = source_type
        self.entity_urn = entity_urn
        self.entity_name = entity_name
        self.content = content
        self.url = url
        self.page = page
        self.section = section

    def to_xml(self) -> str:
        parts = [f'<entity id="{self.cid}">']
        if self.entity_urn:
            parts.append(f"  <urn>{self._esc(self.entity_urn)}</urn>")
        if self.entity_name:
            parts.append(f"  <name>{self._esc(self.entity_name)}</name>")
        if self.url:
            parts.append(f"  <url>{self._esc(self.url)}</url>")
        if self.page is not None:
            parts.append(f"  <page>{self.page}</page>")
        if self.section:
            parts.append(f"  <section>{self._esc(self.section)}</section>")
        parts.append(f"  <content>{self._esc(self.content)}</content>")
        parts.append("</entity>")
        return "\n".join(parts)

    @staticmethod
    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_context(results: Sequence[SearchResult], max_chunks: int = MAX_CHUNKS) -> tuple[list[ContextDocument], str]:
    docs: list[ContextDocument] = []
    total_chars = 0
    cid_counter = 0

    for result in results:
        if len(docs) >= max_chunks:
            break
        payload = result.payload or {}
        chunk_type = payload.get("chunk_type", "")
        content = payload.get("content", "") or result.snippet or result.name
        if total_chars + len(content) > MAX_CHARS:
            content = content[:MAX_CHARS - total_chars]
        cid_counter += 1
        cid = f"E{cid_counter}"
        doc = ContextDocument(
            cid=cid,
            source_type="datahub_entity" if chunk_type != "document_chunk" else "document_chunk",
            entity_urn=result.urn,
            entity_name=result.name,
            content=content,
            url=result.datahub_url,
            page=payload.get("page"),
            section=payload.get("section"),
        )
        docs.append(doc)
        total_chars += len(content)

    context_xml = "<context>\n" + "\n".join(d.to_xml() for d in docs) + "\n</context>"
    return docs, context_xml


def format_fallback_answer(docs: list[ContextDocument], query: str) -> str:
    if not docs:
        return "Không tìm thấy dữ liệu phù hợp."

    answers: list[str] = []
    for doc in docs:
        answers.append(f"- {doc.entity_name}: {doc.content[:200]}")
    return "Dựa trên dữ liệu có sẵn:\n" + "\n".join(answers)
