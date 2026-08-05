from collections.abc import Awaitable, Callable, Sequence

import structlog

from config.prompts import NO_ANSWER_FALLBACKS
from guardrails.sanitizer import mask_secrets
from guardrails.validation import NO_EVIDENCE_RESPONSE, validate_generation
from llm.client import create_llm_client, resolve_provider
from llm.fireworks import FireworksLLM
from retrieval.citation import Citation, build_citations, validate_citations
from retrieval.context_builder import ContextDocument, build_context, format_fallback_answer
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent

log = structlog.get_logger()


def _sanitize_context(docs: list[ContextDocument]) -> tuple[list[ContextDocument], str]:
    """Mask secrets in document content and rebuild the context XML."""
    for doc in docs:
        doc.content = mask_secrets(doc.content)
    context_xml = "<context>\n" + "\n".join(d.to_xml() for d in docs) + "\n</context>"
    return docs, context_xml


def _enforce_recommendation_format(answer: str) -> str:
    """Ensure a recommendation answer is labelled with a Facts section."""
    lowered = answer.lower()
    if "facts:" in lowered or "recommendation:" in lowered or "khuyến nghị" in lowered:
        return answer
    return f"Facts:\n{answer}"


class AnswerGenerator:
    def __init__(self, provider: str | None = None) -> None:
        self._llm = create_llm_client(provider)
        self._provider_key = resolve_provider(provider or "")

    async def generate(self, query: str, results: Sequence[SearchResult],
                       intent: QueryIntent,
                       history: list[tuple[str, str]] | None = None,
                       recommendation: bool = False
                       ) -> tuple[str, list[Citation], list[ContextDocument], str, str]:
        docs, context_xml = build_context(results)

        if isinstance(self._llm, FireworksLLM) and not self._llm.available:
            answer = format_fallback_answer(docs, query) if docs else NO_EVIDENCE_RESPONSE
            citations = build_citations(docs, [d.cid for d in docs]) if docs else []
            return answer, citations, docs, context_xml, "medium" if docs else "low"

        if not docs:
            if intent == QueryIntent.TERM_DEFINITION or (history and len(history) > 0):
                answer, _ = await self._rag_answer(query, "", history=history)
                return answer, [], [], "", "medium"
            return NO_EVIDENCE_RESPONSE, [], [], context_xml, "low"

        docs, context_xml = _sanitize_context(docs)

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

        if recommendation:
            answer = _enforce_recommendation_format(answer)

        validated = validate_generation(answer, docs, confidence)
        return validated.answer, citations, docs, context_xml, validated.confidence

    async def generate_stream(
        self, query: str, results: Sequence[SearchResult],
        intent: QueryIntent,
        history: list[tuple[str, str]] | None = None,
        on_token: Callable[[str], Awaitable[None]] | None = None,
        recommendation: bool = False,
    ) -> tuple[str, list[Citation], list[ContextDocument], str, str]:
        """Like ``generate`` but streams the answer text via ``on_token``."""
        docs, context_xml = build_context(results)

        if isinstance(self._llm, FireworksLLM) and not self._llm.available:
            answer = format_fallback_answer(docs, query) if docs else NO_EVIDENCE_RESPONSE
            if on_token:
                await on_token(answer)
            citations = build_citations(docs, [d.cid for d in docs]) if docs else []
            return answer, citations, docs, context_xml, "medium" if docs else "low"

        if not docs:
            if intent == QueryIntent.TERM_DEFINITION or (history and len(history) > 0):
                answer, _ = await self._rag_answer(query, "", history=history)
            else:
                answer = NO_EVIDENCE_RESPONSE
            if on_token:
                await on_token(answer)
            return answer, [], [], "", "low"

        docs, context_xml = _sanitize_context(docs)

        raw_answer = await self._llm.stream(
            query, context=[context_xml], history=history, on_token=on_token
        )
        answer = raw_answer.strip()

        citations = build_citations(docs, [d.cid for d in docs])
        citations = validate_citations(citations, docs)

        is_no_answer = any(p in answer.lower() for p in NO_ANSWER_FALLBACKS)
        confidence = "low" if is_no_answer else "high"

        if recommendation:
            answer = _enforce_recommendation_format(answer)

        validated = validate_generation(answer, docs, confidence)
        return validated.answer, citations, docs, context_xml, validated.confidence

    async def _rag_answer(self, query: str, context_xml: str,
                          history: list[tuple[str, str]] | None = None) -> tuple[str, list[str]]:
        try:
            result = await self._llm.generate_structured(
                query, context_xml=context_xml, history=history
            )
            answer = result.get("answer", "Không thể tạo câu trả lời.")
            cids = result.get("citation_ids", [])
            return answer, cids
        except Exception:
            log.exception("llm_generation_failed")
            return "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.", []

    async def generate_conversational(
        self, query: str,
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Answer a non-DataHub (general) question without retrieval context.

        Streams the reply via ``on_token`` when provided, and never returns
        citations — general questions have no evidence to cite.
        """
        from llm.fireworks import GENERAL_SYSTEM_PROMPT, FireworksLLM

        # Apply the strict refusal prompt where the provider supports a custom
        # system prompt; MockLLM and other stubs ignore the kwarg.
        system_prompt = (
            GENERAL_SYSTEM_PROMPT
            if isinstance(self._llm, (FireworksLLM,))
            or self._provider_key == "nvidia"
            else None
        )
        try:
            if on_token is not None:
                if system_prompt is not None:
                    answer = await self._llm.stream(
                        query, context=None, history=None, on_token=on_token,
                        system_prompt=system_prompt,
                    )
                else:
                    answer = await self._llm.stream(
                        query, context=None, history=None, on_token=on_token
                    )
            else:
                if system_prompt is not None:
                    answer = await self._llm.generate(
                        query, context=None, history=None, system_prompt=system_prompt
                    )
                else:
                    answer = await self._llm.generate(query, context=None, history=None)
            return (answer or "").strip()
        except Exception:
            log.exception("conversational_generation_failed")
            fallback = (
                "Xin lỗi, tôi chưa hiểu câu hỏi này. Bạn có thể hỏi về dataset, "
                "glossary term, owner, lineage hoặc SQL."
            )
            if on_token is not None:
                await on_token(fallback)
            return fallback
