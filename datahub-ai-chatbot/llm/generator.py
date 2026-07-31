from collections.abc import Sequence

import structlog

from config.prompts import NO_ANSWER_FALLBACKS, NO_ANSWER_RESPONSE
from llm.client import create_llm_client
from llm.fireworks import FireworksLLM
from retrieval.citation import Citation, build_citations, validate_citations
from retrieval.context_builder import ContextDocument, build_context, format_fallback_answer
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent

log = structlog.get_logger()


class AnswerGenerator:
    def __init__(self) -> None:
        self._llm = create_llm_client()

    async def generate(self, query: str, results: Sequence[SearchResult],
                       intent: QueryIntent,
                       history: list[tuple[str, str]] | None = None) -> tuple[str, list[Citation], list[ContextDocument], str, str]:
        docs, context_xml = build_context(results)

        if isinstance(self._llm, FireworksLLM) and not self._llm.available:
            answer = format_fallback_answer(docs, query) if docs else NO_ANSWER_RESPONSE
            citations = build_citations(docs, [d.cid for d in docs]) if docs else []
            return answer, citations, docs, context_xml, "medium" if docs else "low"

        if not docs:
            if intent == QueryIntent.TERM_DEFINITION or (history and len(history) > 0):
                answer, _ = await self._rag_answer(query, "", history=history)
                return answer, [], [], "", "medium"
            return NO_ANSWER_RESPONSE, [], [], context_xml, "low"

        answer, llm_citation_ids = await self._rag_answer(query, context_xml, history=history)

        if llm_citation_ids:
            citations = build_citations(docs, llm_citation_ids)
        else:
            citations = build_citations(docs, [d.cid for d in docs])
        citations = validate_citations(citations, docs)

        is_no_answer = any(p in answer.lower() for p in NO_ANSWER_FALLBACKS)
        confidence = "high"
        if is_no_answer:
            confidence = "low"

        return answer, citations, docs, context_xml, confidence

    async def _rag_answer(self, query: str, context_xml: str,
                          history: list[tuple[str, str]] | None = None) -> tuple[str, list[str]]:
        try:
            result = await self._llm.generate_structured(query, context_xml=context_xml, history=history)
            answer = result.get("answer", "Không thể tạo câu trả lời.")
            cids = result.get("citation_ids", [])
            return answer, cids
        except Exception:
            log.exception("llm_generation_failed")
            return "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.", []
