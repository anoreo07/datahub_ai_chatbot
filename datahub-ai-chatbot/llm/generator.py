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


def _multisignal_confidence(results: Sequence[SearchResult], llm_conf: str | None,
                            citation_count: int) -> str:
    """Combine retrieval evidence and LLM-reported confidence into one value.

    Signals:
    - retrieval strength (top score, result count)
    - citation coverage (how many claims are attributed)
    - the model's own reported confidence (when available)

    The result is conservative: low retrieval support or zero citations always
    cap the confidence, regardless of what the model claims.
    """
    if not results:
        return "low"

    top_score = max((r.score for r in results), default=0.0)
    has_citations = citation_count > 0

    evidence = "high" if top_score >= 0.8 else ("medium" if top_score >= 0.5 else "low")

    if llm_conf == "low":
        return "low"
    if llm_conf == "medium":
        evidence = "medium" if evidence == "high" else evidence
    if not has_citations and evidence == "high":
        evidence = "medium"
    if len(results) == 0:
        return "low"
    return evidence


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
                answer, _, _ = await self._rag_answer(query, "", history=history)
                return answer, [], [], "", "medium"
            return NO_EVIDENCE_RESPONSE, [], [], context_xml, "low"

        docs, context_xml = _sanitize_context(docs)

        answer, llm_citation_ids, llm_confidence = await self._rag_answer(
            query, context_xml, history=history
        )

        if llm_citation_ids:
            citations = build_citations(docs, llm_citation_ids)
        else:
            citations = build_citations(docs, [d.cid for d in docs])
        citations = validate_citations(citations, docs)

        is_no_answer = any(p in answer.lower() for p in NO_ANSWER_FALLBACKS)
        confidence = "high"
        if is_no_answer:
            confidence = "low"

        confidence = _multisignal_confidence(results, llm_confidence, len(citations))

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
                answer, _, _ = await self._rag_answer(query, "", history=history)
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
                          history: list[tuple[str, str]] | None = None
                          ) -> tuple[str, list[str], str | None]:
        try:
            result = await self._llm.generate_structured(
                query, context_xml=context_xml, history=history
            )
            answer = result.get("answer", "Không thể tạo câu trả lời.")
            cids = result.get("citation_ids", []) or []
            conf = result.get("confidence")
            if conf not in ("high", "medium", "low"):
                conf = None
            return answer, cids, conf
        except Exception:
            log.exception("llm_generation_failed")
            return "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.", [], None

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
            # Always collect through the streaming path: Fireworks `generate()`
            # forces response_format json_object, which coerces free-form
            # conversational replies into a JSON placeholder (e.g. {"type":
            # "object"}). `stream()` never sets response_format, so the answer
            # stays plain text whether or not a live on_token is supplied.
            if system_prompt is not None:
                answer = await self._llm.stream(
                    query, context=None, history=None, on_token=on_token,
                    system_prompt=system_prompt,
                )
            else:
                answer = await self._llm.stream(
                    query, context=None, history=None, on_token=on_token
                )
            # Fragile fallback: some providers still wrap free-form text in a
            # JSON object ({...}) or a blank schema placeholder despite the
            # plain-stream path. Never surface that as the answer.
            text = (answer or "").strip()
            if text and (
                (text.startswith("{") and text.endswith("}"))
                or (text.startswith("[") and text.endswith("]"))
            ):
                import json as _json

                try:
                    parsed = _json.loads(text)
                    if isinstance(parsed, dict) and "answer" in parsed:
                        inner = parsed["answer"]
                        text = inner if isinstance(inner, str) else text
                except _json.JSONDecodeError:
                    pass
            return text
        except Exception:
            log.exception("conversational_generation_failed")
            fallback = (
                "Xin lỗi, tôi chưa hiểu câu hỏi này. Bạn có thể hỏi về dataset, "
                "glossary term, owner, lineage hoặc SQL."
            )
            if on_token is not None:
                await on_token(fallback)
            return fallback
