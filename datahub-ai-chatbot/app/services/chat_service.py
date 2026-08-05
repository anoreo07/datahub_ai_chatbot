import re
import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.chat import (
    ChatResponse,
    CitationItem,
    EntityItem,
    LineageData,
    LineageNode,
    Suggestion,
)
from app.services.conversation import get_conversation_memory
from config.settings import settings
from database.repositories.entity_repository import EntityRepository
from guardrails.sanitizer import mask_secrets
from guardrails.service import GuardrailService
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from llm.client import create_llm_client
from llm.generator import AnswerGenerator
from retrieval.datahub_intent import (
    DataHubRelevance,
    clarification_response,
    classify_datahub_relevance,
    refusal_response,
)
from retrieval.entity_resolver import EntityResolver, ResolutionResult
from retrieval.fuzzy import fuzzy_score
from retrieval.hybrid_search import HybridSearch, SearchResult
from retrieval.intent import QueryIntent, _norm_vn, classify_intent
from retrieval.reranker import Reranker

# Listing patterns - must NOT contain a specific entity name before the pattern
_LISTING_PATTERNS: list[re.Pattern] = [
    re.compile(r'^(?:có các|các)\s+(dataset|dashboard|glossary(?:\s+terms?)?)\s+(?:gì|nào)\??$', re.I),
    re.compile(r'^(?:có các|các)\s+(dataset|dashboard|glossary(?:\s+terms?)?)\s*$', re.I),
    re.compile(r'^liệt kê\s+(?:các\s+)?(dataset|dashboard|glossary(?:\s+terms?)?)\s*$', re.I),
    re.compile(r'^list\s+(?:all\s+)?(datasets|dashboards|glossary\s+terms)\s*$', re.I),
    re.compile(r'^danh sách\s+(?:các\s+)?(dataset|dashboard|glossary(?:\s+terms)?)\s*$', re.I),
    re.compile(r'^show\s+(?:all\s+)?(datasets|dashboards|glossary(?:\s+terms)?)\s*$', re.I),
    re.compile(r'^có những (dataset|dashboard|glossary(?:\s+terms?)?) nào\??$', re.I),
]

_LISTING_TYPE_MAP: dict[str, str] = {
    "dataset": "dataset",
    "dashboard": "dashboard",
    "glossary": "glossary_term",
    "glossary term": "glossary_term",
    "glossary_term": "glossary_term",
}

_FILTER_VALUE_PATTERNS: dict[QueryIntent, list[str]] = {
    QueryIntent.DOMAIN_QUERY: [
        r"(?:domain|mien|linh vuc)\s*[:=]?\s*([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
        r"(?:trong|thuoc|in|belonging to|belong to)\s+(?:the\s+)?(?:domain|mien|linh vuc)\s+([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
    ],
    QueryIntent.PLATFORM_QUERY: [
        r"(?:platform|nen tang)\s*[:=]?\s*([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
        r"(?:tren|trong|on|in)\s+(?:platform|nen tang)?\s*([a-z0-9\.\-]+)",
    ],
    QueryIntent.TAG_QUERY: [
        r"(?:tag|tagged|with tag|co tag|duoc gan tag|voi tag|gan tag)\s*[:=]?\s*([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
    ],
    QueryIntent.ENTITIES_BY_OWNER: [
        r"(?:owned by|do|boi|cua)\s+([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
        r"what does\s+([a-z0-9\.\- ]+?)\s+own",
    ],
}

_CONNECTOR_WORDS = {
    "bao", "gom", "co", "chua", "include", "includes", "has", "have",
    "contain", "what", "which", "are", "is", "the", "nao", "nhung",
    "cac", "gi", "asset", "assets", "entity", "entities", "dataset",
    "datasets", "dashboard", "dashboards",
}

# Intents answered deterministically from the DB (full, exact counts/lists)
# instead of top-K hybrid search, so counting/listing is complete & consistent.
_DETERMINISTIC_LISTING_INTENTS = {
    QueryIntent.COUNT_ENTITIES,
    QueryIntent.DOMAIN_QUERY,
    QueryIntent.PLATFORM_QUERY,
    QueryIntent.TAG_QUERY,
    QueryIntent.ENTITIES_BY_OWNER,
    QueryIntent.CERTIFIED_LIST,
}

_DIMENSION_MAP: dict[QueryIntent, str] = {
    QueryIntent.DOMAIN_QUERY: "domain",
    QueryIntent.PLATFORM_QUERY: "platform",
    QueryIntent.TAG_QUERY: "tag",
    QueryIntent.ENTITIES_BY_OWNER: "owner",
}

# Intents where the user asks about ONE entity. When retrieval returns several
# close-scored candidates for these, ask a clarification question instead of
# picking one randomly (guardrail #9). Listing-style intents legitimately return
# many entities and must NOT trigger clarification.
_AMBIGUOUS_CLARIFY_INTENTS = {
    QueryIntent.TERM_DEFINITION,
    QueryIntent.FIND_ENTITY,
    QueryIntent.OWNER_LOOKUP,
    QueryIntent.SCHEMA_LOOKUP,
    QueryIntent.ENTITY_DOMAIN,
    QueryIntent.DATAHUB_URL,
    QueryIntent.ENTITY_EXISTS,
    QueryIntent.GENERAL,
}

_ENTITY_TYPE_PATTERNS: list[tuple[re.Pattern[str], str | None]] = [
    (re.compile(r"glossary\s+terms?", re.I), "glossary_term"),
    (re.compile(r"\bglossary\b", re.I), "glossary_term"),
    (re.compile(r"\bdashboards?", re.I), "dashboard"),
    (re.compile(r"\bdatasets?", re.I), "dataset"),
    (re.compile(r"\bassets?", re.I), None),
    (re.compile(r"\bentities?", re.I), None),
]

_ENTITY_TYPE_LABELS: dict[str | None, str] = {
    "dataset": "datasets",
    "dashboard": "dashboards",
    "glossary_term": "glossary terms",
    None: "assets",
}

_ANAPHORA_WORDS = {"do", "no", "ay", "nay", "day", "kia", "o"}

# Listing all domains ("có các domain nào?", "liệt kê domain", "danh sách domain",
# "domain trong hệ thống", "có bao nhiêu domain") -> deterministic answer from DB.
_DOMAIN_LISTING_RE = re.compile(
    r"(có những domain nào|có các domain nào|co nhung domain nao|co cac domain nao|"
    r"liệt kê (các )?domain|liệt kê (các )?lĩnh vực|liệt kê (các )?miền|"
    r"liet ke domain|liet ke linh vuc|liet ke cac linh vuc|liet ke mien|"
    r"danh sách (các )?domain|danh sách (các )?lĩnh vực|danh sach domain|danh sach cac domain|danh sach linh vuc|"
    r"domain nào trong hệ thống|domain trong hệ thống|các domain trong hệ thống|"
    r"domain nao trong he thong|domain trong he thong|"
    r"có bao nhiêu domain|có bao nhiêu lĩnh vực|co bao nhieu domain|"
    r"how many domain)",
    re.I,
)

log = structlog.get_logger()

_GREETING_RESPONSES = [
    "Xin chào! Tôi là trợ lý DataHub. Tôi có thể giúp bạn tra cứu datasets, glossary terms, owners, lineage và các thông tin metadata khác.",
    "Chào bạn! Tôi có thể hỗ trợ bạn tra cứu thông tin dữ liệu trong hệ thống. Bạn muốn tìm hiểu về điều gì?",
    "Xin chào! Hãy hỏi tôi về bất kỳ thông tin metadata nào như datasets, dashboards, glossary terms, hoặc lineage.",
]

_TERM_REMOVE_WORDS = [
    "nghĩa là gì", "nghia la gi", "định nghĩa", "dinh nghia",
    "là gì", "la gi", "definition", "meaning", "define",
]

_CHITCHAT_RESPONSES: dict[str, str] = {
    "bạn khỏe không": "Tôi là một trợ lý AI, lúc nào cũng sẵn sàng giúp đỡ bạn!",
    "bạn khoẻ không": "Tôi là một trợ lý AI, lúc nào cũng sẵn sàng giúp đỡ bạn!",
    "how are you": "I'm an AI assistant, always ready to help!",
    "bạn tên gì": "Tôi là DataHub AI Chatbot, trợ lý tra cứu metadata cho hệ thống DataHub.",
    "bạn là ai": "Tôi là DataHub AI Chatbot, được xây dựng để giúp bạn tra cứu thông tin về dữ liệu doanh nghiệp.",
    "who are you": "I'm DataHub AI Chatbot, your metadata assistant.",
    "cảm ơn": "Không có gì! Nếu bạn cần thêm thông tin gì, cứ hỏi tôi nhé.",
    "cám ơn": "Không có gì! Nếu bạn cần thêm thông tin gì, cứ hỏi tôi nhé.",
    "thank": "You're welcome! Feel free to ask if you need anything else.",
}


class ChatService:
    def __init__(self, session: AsyncSession, auth_service: AuthorizationService | None = None) -> None:
        self._session = session
        self._auth_service = auth_service
        self._entity_resolver = EntityResolver(session)
        self._entity_repo = EntityRepository(session)
        self._hybrid_search = HybridSearch(session)
        self._reranker = Reranker()
        self._generator = AnswerGenerator()
        self._llm = create_llm_client()
        self._source: DataHubSource = create_datahub_source()
        self._memory = get_conversation_memory()
        self._last_denied_names: list[str] = []
        self._guardrails = GuardrailService()

    async def answer(self, question: str, user: UserContext | None = None,
                     conversation_id: str | None = None,
                     suggested_name: str | None = None,
                     model: str | None = None,
                     on_status: Callable[[str], Awaitable[None]] | None = None,
                     on_token: Callable[[str], Awaitable[None]] | None = None) -> ChatResponse:
        trace_id = uuid.uuid4().hex[:12]
        intent = classify_intent(question)
        cid = conversation_id or trace_id

        # Model selection: a per-request model id swaps in a dedicated generator
        # (e.g. NVIDIA NVCF) without disturbing the default Fireworks pipeline.
        generator = self._generator
        if model and model.strip():
            try:
                generator = AnswerGenerator(provider=model.strip())
            except Exception:  # noqa: BLE001
                log.warning(
                    "chat_model_override_failed",
                    trace_id=trace_id,
                    model=model[:80],
                )
                generator = self._generator

        async def _emit(step: str) -> None:
            if on_status:
                await on_status(step)

        await _emit("classify")

        log.info("chat_request", trace_id=trace_id, intent=intent.value,
                 question=question[:100], conversation_id=cid)

        user_ctx = user or UserContext(user_id="anonymous", is_admin=False)
        uid = user_ctx.user_id

        if intent == QueryIntent.GREETING:
            import random
            answer_text = random.choice(_GREETING_RESPONSES)
            await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
            return ChatResponse(answer=answer_text, intent=intent.value, confidence="high", trace_id=trace_id, conversation_id=cid)

        if intent == QueryIntent.CHITCHAT:
            cleaned = question.lower().strip().rstrip("?!.")
            answer_text = _CHITCHAT_RESPONSES.get(cleaned, "Tôi là trợ lý DataHub, sẵn sàng giúp bạn!")
            await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
            return ChatResponse(answer=answer_text, intent=intent.value, confidence="high", trace_id=trace_id, conversation_id=cid)

        # Guardrails: scope restriction (#5) and prompt injection in user input (#16).
        out_of_scope = self._guardrails.enforce_scope(question)
        if out_of_scope:
            log.info("chat_out_of_scope", trace_id=trace_id, question=question[:100])
            await self._memory.add_turn_db(self._session, uid, cid, question, out_of_scope)
            return ChatResponse(answer=out_of_scope, intent=intent.value, confidence="high",
                                insufficient_context=False, trace_id=trace_id, conversation_id=cid)

        injection_message = self._guardrails.check_prompt_injection(question)
        if injection_message:
            log.info("chat_injection_blocked", trace_id=trace_id, question=question[:100])
            await self._memory.add_turn_db(self._session, uid, cid, question, injection_message)
            return ChatResponse(answer=injection_message, intent=intent.value, confidence="high",
                                insufficient_context=False, trace_id=trace_id, conversation_id=cid)

        recommendation = self._guardrails.is_recommendation(question)
        if recommendation:
            log.info("chat_recommendation", trace_id=trace_id, question=question[:100])

        # AI intent gate: before ANY retrieval/search/GraphQL/RAG runs, ask the
        # LLM whether this question is about DataHub metadata. Non-DataHub
        # questions get a polite refusal; ambiguous ones ask for clarification.
        relevance = await classify_datahub_relevance(self._llm, question)
        if relevance == DataHubRelevance.NON_DATAHUB:
            log.info("route_ai_non_datahub", trace_id=trace_id, question=question[:100])
            await _emit("generate")
            answer_text = refusal_response(question)
            if on_token:
                await on_token(answer_text)
            await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )
        if relevance == DataHubRelevance.UNCERTAIN:
            # The LLM is a primary classifier but can be indecisive on clearly
            # in-scope questions. Fall back to the keyword relevance heuristic:
            # if it confirms DataHub vocabulary, proceed with the pipeline
            # instead of blocking a valid metadata question.
            if self._is_datahub_relevant(question):
                log.info("route_ai_uncertain_rescued",
                         trace_id=trace_id, question=question[:100])
                relevance = DataHubRelevance.DATAHUB
            else:
                log.info("route_ai_uncertain", trace_id=trace_id, question=question[:100])
                answer_text = clarification_response(question)
                await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
                return ChatResponse(
                    answer=answer_text, intent=intent.value, confidence="low",
                    ambiguous=True, insufficient_context=True,
                    trace_id=trace_id, conversation_id=cid,
                )

        # GENERAL intent with no DataHub relevance (trivia, non-business questions)
        # is answered conversationally without retrieval, so no spurious citations.
        if intent == QueryIntent.GENERAL and not self._is_datahub_relevant(question):
            log.info("route_general_conversational", trace_id=trace_id, question=question[:100])
            await _emit("generate")
            answer_text = await generator.generate_conversational(question, on_token=on_token)
            if not answer_text:
                answer_text = (
                    "Xin lỗi, tôi chưa hiểu câu hỏi này. Bạn có thể hỏi về dataset, "
                    "glossary term, owner, lineage hoặc SQL."
                )
            await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="medium",
                ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        listing_type = self._detect_listing(question)
        if listing_type:
            entity_type_label = "glossary terms" if listing_type == "glossary_term" else f"{listing_type}s"
            count = await self._entity_repo.count_by_type(listing_type)
            log.info("route_listing", trace_id=trace_id, question=question[:100],
                     listing_type=listing_type, db_count=count, source="deterministic_db")
            entities = await self._entity_repo.list_by_type(listing_type, limit=200)
            if self._auth_service:
                accessible = await self._auth_service.filter_accessible_urns(
                    user_ctx, [e.urn for e in entities]
                )
                entities = [e for e in entities if e.urn in accessible]
            platforms: dict[str, list[str]] = {}
            for e in entities:
                p = e.platform or "unknown"
                platforms.setdefault(p, []).append(e.display_name or e.name)
            lines = [f"Có tổng cộng {count} {entity_type_label} trong hệ thống."]
            for plat, names in sorted(platforms.items()):
                sample = sorted(names)
                lines.append(f"\n{plat}: {', '.join(sample[:15])}{', ...' if len(sample) > 15 else ''}")
            answer_text = mask_secrets("\n".join(lines))

            entity_list = []
            for e in entities:
                entity_list.append(EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url))
                if len(entity_list) >= 50:
                    break

            await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
            return ChatResponse(
                answer=answer_text, intent="LISTING", entities=entity_list,
                confidence="high", ambiguous=False,
                insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        if intent in _DETERMINISTIC_LISTING_INTENTS:
            response = await self._deterministic_listing(
                question, intent, user_ctx, trace_id, cid,
                suggested_name=suggested_name,
            )
            if response is not None:
                await self._memory.add_turn_db(self._session, uid, cid, question, response.answer)
                return response

        history = await self._memory.load_history_from_db(self._session, uid, cid)

        await _emit("retrieve")

        import unicodedata
        q_norm = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")

        _ANAPHORA = {"đó", "nó", "ấy", "này", "đây", "kia"}
        _ANAPHORA_ASCII = {"do", "no", "ay", "nay", "day", "kia"}
        has_anaphora = bool(
            re.search(r"\b(?:%s)\b" % "|".join(_ANAPHORA), question.lower())
            or re.search(r"\b(?:%s)\b" % "|".join(_ANAPHORA_ASCII), q_norm)
        )
        is_ellipsis = q_norm.startswith(("con ", "the ", "the con"))

        if (has_anaphora or is_ellipsis) and len(history) > 0:
            if is_ellipsis:
                m = re.search(r'^(?:the\s+con\s+|con\s+|the\s+)(.+?)\??\s*$', q_norm)
                entity_from_q = m.group(1).strip() if m else ""
                inferred_entity = entity_from_q if entity_from_q else None
            else:
                inferred_entity = self._infer_entity_from_history(history)
            log.info("route_anaphora", trace_id=trace_id, question=question[:100],
                     has_anaphora=has_anaphora, is_ellipsis=is_ellipsis,
                     inferred_entity=inferred_entity, history_len=len(history))
            if inferred_entity:
                if intent in (QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
                              QueryIntent.ENTITY_DOMAIN,
                              QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
                              QueryIntent.SCHEMA_LOOKUP, QueryIntent.DATAHUB_URL,
                              QueryIntent.ENTITY_EXISTS, QueryIntent.DOMAIN_QUERY,
                              QueryIntent.PLATFORM_QUERY, QueryIntent.TAG_QUERY,
                              QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST):
                    results = await self._structured_retrieval(intent, question, inferred_entity=inferred_entity, trace_id=trace_id)
                else:
                    results = []
                    for try_intent in [
                        QueryIntent.OWNER_LOOKUP, QueryIntent.ENTITY_DOMAIN,
                        QueryIntent.SCHEMA_LOOKUP,
                        QueryIntent.LINEAGE, QueryIntent.TERM_DEFINITION,
                        QueryIntent.TERM_TO_DATASETS, QueryIntent.DATAHUB_URL,
                        QueryIntent.ENTITY_EXISTS,
                    ]:
                        results = await self._structured_retrieval(try_intent, question, inferred_entity=inferred_entity, trace_id=trace_id)
                        if results:
                            intent = try_intent
                            break
            else:
                results = []
        elif intent in (QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
                        QueryIntent.ENTITY_DOMAIN,
                        QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
                        QueryIntent.SCHEMA_LOOKUP, QueryIntent.DATAHUB_URL,
                        QueryIntent.ENTITY_EXISTS, QueryIntent.DOMAIN_QUERY,
                        QueryIntent.PLATFORM_QUERY, QueryIntent.TAG_QUERY,
                        QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST):
            results = await self._structured_retrieval(
                intent, question, inferred_entity=suggested_name
            )
            log.info("route_structured", trace_id=trace_id, question=question[:100],
                     intent=intent.value, result_count=len(results))
        else:
            results = await self._hybrid_search.search(question, trace_id=trace_id)
            log.info("route_hybrid", trace_id=trace_id, question=question[:100],
                     intent=intent.value, result_count=len(results))

        suggestion: Suggestion | None = None
        if (not results) and suggested_name is None:
            if intent == QueryIntent.TERM_DEFINITION:
                extracted = self._extract_name(question, _TERM_REMOVE_WORDS)
                suggestion = await self._suggest_entity(
                    extracted, "glossary_term", question, trace_id
                )
            elif intent == QueryIntent.DOMAIN_QUERY:
                value = self._extract_filter_value(question, QueryIntent.DOMAIN_QUERY)
                if value and value not in _ANAPHORA_WORDS:
                    suggestion = await self._suggest_entity(value, None, question, trace_id)
            elif intent in (QueryIntent.LINEAGE, QueryIntent.OWNER_LOOKUP,
                            QueryIntent.ENTITY_DOMAIN, QueryIntent.SCHEMA_LOOKUP,
                            QueryIntent.TERM_TO_DATASETS, QueryIntent.ENTITY_EXISTS):
                # A picked function (Data Lineage, quality, …) with no matching
                # entity -> friendly, grounded "not found" answer instead of a
                # generic LLM guess.
                extracted = self._extract_name(question, _TERM_REMOVE_WORDS)
                if extracted and extracted not in _ANAPHORA_WORDS:
                    suggestion = await self._suggest_entity(
                        extracted,
                        "dataset" if intent != QueryIntent.TERM_TO_DATASETS else None,
                        question, trace_id,
                    )
                    not_found = (
                        f"Không tìm thấy dataset '{extracted}' trong hệ thống DataHub."
                    )
                    if suggestion is not None:
                        not_found += (
                            f" Ý bạn là '{suggestion.suggested}'?"
                        )
                    await self._memory.add_turn_db(self._session, uid, cid, question, not_found)
                    log.info("chat_not_found", trace_id=trace_id, intent=intent.value,
                             original=extracted, suggested=suggestion.suggested if suggestion else None,
                             conversation_id=cid)
                    return ChatResponse(
                        answer=not_found, intent=intent.value, confidence="high",
                        ambiguous=False, insufficient_context=False,
                        trace_id=trace_id, conversation_id=cid,
                    )
            if suggestion is not None:
                answer_text = (
                    f"'{suggestion.original}' không tồn tại trong hệ thống. "
                    f"Ý bạn là '{suggestion.suggested}'?"
                )
                await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)
                log.info("chat_suggestion", trace_id=trace_id, intent=intent.value,
                         original=suggestion.original, suggested=suggestion.suggested,
                         conversation_id=cid)
                return ChatResponse(
                    answer=answer_text, intent=intent.value, confidence="high",
                    ambiguous=False, insufficient_context=False,
                    trace_id=trace_id, conversation_id=cid,
                    suggestion=suggestion,
                )

        # When the user confirmed a suggestion, the question still contains the
        # misspelled name. Rewrite it with the confirmed entity so the generator
        # answers about the corrected term rather than reporting "no info" on the typo.
        question_for_gen = question
        if suggested_name and intent == QueryIntent.TERM_DEFINITION:
            extracted = self._extract_name(question, _TERM_REMOVE_WORDS)
            if extracted and extracted.lower() not in suggested_name.lower():
                question_for_gen = re.sub(
                    re.escape(extracted), suggested_name, question, flags=re.I
                )
                log.info("chat_rewrite_confirmed", trace_id=trace_id,
                         before=question[:100], after=question_for_gen[:100],
                         suggested=suggested_name)

        if self._auth_service:
            total_before = len(results)
            denied_names = [r.name for r in results]
            accessible = await self._auth_service.filter_accessible_urns(
                user_ctx, [r.urn for r in results]
            )
            if intent == QueryIntent.LINEAGE and results:
                # The main entity (score 1.0, first result) is the subject of the
                # question. If it is denied, never answer with a related entity's
                # lineage instead — treat the whole query as denied.
                main_urn = results[0].urn
                if main_urn not in accessible:
                    denied_count = len(results)
                    results = []
                else:
                    results = [r for r in results if r.urn in accessible]
                    denied_count = total_before - len(results)
            else:
                results = [r for r in results if r.urn in accessible]
                denied_count = total_before - len(results)
            if denied_count > 0:
                self._last_denied_names = denied_names
        else:
            denied_count = 0

        results = await self._reranker.rerank(question_for_gen, results)

        await _emit("rerank")

        # Guardrail #9: when a single-entity question matches multiple entities,
        # ask a clarification instead of randomly choosing one.
        ambiguous = (
            len(results) > 1
            and abs(results[0].score - results[1].score) < 0.15
            and results[1].score > 0.5
        )
        if ambiguous and intent in _AMBIGUOUS_CLARIFY_INTENTS:
            options = " hoặc ".join(f"'{r.name}'" for r in results[:3])
            clarification = (
                f"Có nhiều entity trùng khớp với yêu cầu của bạn: {options}. "
                "Bạn muốn hỏi về entity nào?"
            )
            entity_list = [
                EntityItem(urn=r.urn, name=r.name, url=r.datahub_url)
                for r in results if r.name
            ]
            await self._memory.add_turn_db(self._session, uid, cid, question_for_gen, clarification)
            log.info("chat_ambiguous_clarification", trace_id=trace_id, intent=intent.value,
                     top=results[0].name, runner_up=results[1].name, conversation_id=cid)
            return ChatResponse(
                answer=clarification, intent=intent.value, entities=entity_list,
                confidence="low", ambiguous=True, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        short_answer = self._short_negative_answer(intent, results)
        if short_answer is not None:
            entity_list = [
                EntityItem(urn=r.urn, name=r.name, url=r.datahub_url)
                for r in results if r.name
            ]
            await self._memory.add_turn_db(self._session, uid, cid, question_for_gen, short_answer)
            log.info("chat_response", trace_id=trace_id, intent=intent.value,
                     short_answer=True, entity_count=len(entity_list),
                     conversation_id=cid)
            return ChatResponse(
                answer=short_answer, intent=intent.value, entities=entity_list,
                confidence="high", ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        insufficient_context = len(results) == 0
        if insufficient_context and denied_count > 0:
            denied_text = self._build_access_denied_message(user_ctx, self._last_denied_names)
            await self._memory.add_turn_db(self._session, uid, cid, question_for_gen, denied_text)
            answer_text = denied_text
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid,
                insufficient_context=True,
            )

        await _emit("generate")
        if intent == QueryIntent.LINEAGE and results:
            # Deterministic answer from the SAME payload that drives the SVG.
            answer_text, citations, lineage_main = await self._build_lineage_answer(results[0])
            docs = []
            context_xml = ""
            confidence = "high"
            if on_token:
                await on_token(answer_text)
        elif on_token:
            answer_text, citations, docs, context_xml, confidence = await generator.generate_stream(
                question_for_gen, results, intent, history=history, on_token=on_token,
                recommendation=recommendation,
            )
        else:
            answer_text, citations, docs, context_xml, confidence = await generator.generate(
                question_for_gen, results, intent, history=history,
                recommendation=recommendation,
            )

        if intent == QueryIntent.DATAHUB_URL:
            urls = [d.url for d in docs if d.url]
            if urls:
                url_block = "\n".join(f"- {u}" for u in dict.fromkeys(urls))
                answer_text = f"{answer_text.rstrip()}\n\nLink DataHub:\n{url_block}"

        entity_list = [
            EntityItem(urn=d.entity_urn, name=d.entity_name, url=d.url)
            for d in docs if d.entity_name
        ]
        if intent == QueryIntent.LINEAGE and results and not entity_list:
            lineage_data = await self._build_lineage_data(results[0])
            if lineage_data:
                entity_list = [
                    EntityItem(urn=n.urn, name=n.name, url=n.url)
                    for n in (lineage_data.upstreams + lineage_data.downstreams)
                ] + [
                    EntityItem(urn=lineage_data.entity_urn,
                               name=lineage_data.entity_name,
                               url=lineage_data.entity_url)
                ]

        ambiguous = (
            len(results) > 1
            and abs(results[0].score - results[1].score) < 0.15
            and results[1].score > 0.5
        )
        insufficient_context = (len(docs) == 0 or confidence == "low") and not (
            intent == QueryIntent.LINEAGE and results
        )

        await self._memory.add_turn_db(self._session, uid, cid, question_for_gen, answer_text)

        log.info("chat_response", trace_id=trace_id, intent=intent.value,
                 entity_count=len(entity_list), citation_count=len(citations),
                 confidence=confidence, ambiguous=ambiguous,
                 insufficient_context=insufficient_context, conversation_id=cid)

        lineage: LineageData | None = None
        if intent == QueryIntent.LINEAGE and results:
            lineage = await self._build_lineage_data(results[0])

        await _emit("done")

        return ChatResponse(
            answer=answer_text,
            intent=intent.value,
            entities=entity_list,
            citations=[CitationItem(**c.to_dict()) for c in citations],
            confidence=confidence,
            ambiguous=ambiguous,
            insufficient_context=insufficient_context,
            trace_id=trace_id,
            conversation_id=cid,
            lineage=lineage,
        )

    @staticmethod
    def _infer_entity_from_history(history: list[tuple[str, str]]) -> str | None:
        import re
        for question, answer in reversed(history):
            question_lower = question.lower()
            for prefix in ["schema", "định nghĩa", "dinh nghia", "là gì", "la gi",
                           "dataset", "field", "owner", "upstream", "nguồn"]:
                question_lower = question_lower.replace(prefix, " ")
            tokens = re.sub(r"[^a-z0-9_\s]", " ", question_lower).split()
            for t in tokens:
                if len(t) > 3 and t not in {"cho", "có", "của", "và", "là", "nào",
                                             "gì", "các", "được", "bạn", "không",
                                             "những", "này", "đó", "nó", "ấy",
                                             "thông", "tin", "về", "với", "từ",
                                             "còn", "the", "một", "hoặc", "hay",
                                             "lại", "lên", "xuống", "vào", "ra",
                                             "cho", "tôi", "này", "nào", "gì",
                                             "field", "link", "url", "datahub",
                                             "schema", "table", "report", "list"}:
                    return t
        return None

    @staticmethod
    def _extract_name(question: str, remove_words: list[str]) -> str:
        import re
        import unicodedata

        def _norm(s: str) -> str:
            s = s.lower()
            s = s.replace("_", " ").replace("-", " ").replace(".", " ")
            s = s.replace("?", " ").replace("!", " ").replace(",", " ")
            s = s.replace(";", " ").replace(":", " ")
            s = unicodedata.normalize("NFKD", s)
            s = s.encode("ascii", "ignore").decode("ascii")
            return re.sub(r"\s+", " ", s).strip()

        name = _norm(question)
        for word in remove_words:
            name = name.replace(_norm(word), " ")
        for prefix in ["dataset", "dashboard", "report", "term ", "entity"]:
            name = name.replace(prefix, " ")
        name = re.sub(r"\s+", " ", name).strip()
        tokens = name.split()
        stop_words = {
            "cho", "toi", "cua", "va", "co", "nhung", "nao", "gi",
            "la", "the", "a", "an", "of", "in", "to", "for", "with",
            "khong", "cac", "duoc", "ban", "hay", "business", "ai",
            "thong", "tin", "ve", "lineage", "linage", "field", "schema",
        }
        clean_tokens = [t for t in tokens if t not in stop_words]
        # Drop leading noise tokens (verbs/prepositions) that often precede the
        # entity name but are not reduced by the global stop-word set above,
        # e.g. "trinh bay ve" / "mo ta ve" / "hay cho biet ve".
        _leading_noise = {
            "trinh", "bay", "mo", "ta", "neu", "cho", "giup", "hay", "ban",
            "tim", "hieu", "noi", "giui", "the", "nay", "do", "biet", "xin",
            "describe", "about", "explain", "what", "tell", "me", "please",
            "information", "info", "show", "display", "detail",
        }
        while clean_tokens and clean_tokens[0] in _leading_noise:
            clean_tokens.pop(0)
        result = " ".join(clean_tokens) if clean_tokens else name
        result = result.strip().strip(" ?.!,:;-'\"").strip()
        return result

    @staticmethod
    def _is_datahub_relevant(question: str) -> bool:
        """Heuristic filter: is this question about DataHub concepts/metadata?

        Non-relevant (general chit-chat / trivia) questions should be answered
        conversationally without retrieval, so we do not attach spurious
        citations to irrelevant retrieved documents.
        """
        import unicodedata

        q = question.lower()
        n = unicodedata.normalize("NFKD", q).encode("ascii", "ignore").decode("ascii")
        keywords = {
            # explicit DataHub / data-governance vocabulary
            "dataset", "dashboard", "glossary term", "glossary_term", "glossary",
            "domain", "mien", "linh vuc", "platform", "owner", "hieu tai lieu",
            "metadata", "schema", "field", "column", "cot ", "column",
            "table", "bang", "sql", "query", "lineage", "linage", "nguon",
            "upstream", "downstream", "dataflow", "data flow", "etl", "el",
            "report", "bao cao", "tag", "milestone", "certified", "den uy quyen",
            "document", "tai lieu", "ingestion", "ingest", "pipeline",
            # Vietnamese terms often used for metadata questions
            "datasets", "dashboards", "co bao nhieu", "bao nhieu", "nào",
            "lien ke", "liệt kê", "danh sach", "list", "thuoc ve", "chu so huu",
            "la gi", "la gì", "dinh nghia", "định nghĩa", "meaning", "definition",
            "source", "du lieu", "data", "business", "metric", "kpi",
        }
        return any(k in q or k in n for k in keywords)

    async def _structured_retrieval(self, intent: QueryIntent, question: str,
                                    inferred_entity: str | None = None,
                                    trace_id: str | None = None) -> list[SearchResult]:
        from retrieval.hybrid_search import SearchResult

        if intent == QueryIntent.TERM_DEFINITION:
            term_name = inferred_entity or self._extract_name(question, _TERM_REMOVE_WORDS)
            if not term_name:
                log.info("structured_no_name", trace_id=trace_id, intent=intent.value,
                         question=question[:100])
                return []
            # "dataset/dashboard X là gì ?" must resolve the requested type, not a
            # glossary term. Fall back to glossary_term only when no type is named.
            q = question.lower()
            preferred_types: list[str] = []
            if "dataset" in q or "data set" in q or "bảng" in q or "bảng số" in q:
                preferred_types = ["dataset", "dashboard", "glossary_term"]
            elif "dashboard" in q or "report" in q:
                preferred_types = ["dashboard", "dataset", "glossary_term"]
            else:
                preferred_types = ["glossary_term", "dataset", "dashboard"]
            last_error = None
            for etype in preferred_types:
                resolution = await self._entity_resolver.resolve(
                    term_name, entity_type=etype, trace_id=trace_id)
                if self._trusted_resolution(resolution):
                    return await self._resolve_to_results(resolution, trace_id=trace_id)
                last_error = resolution
            # No trusted glossary/dataset match. The name may be a FIELD (column)
            # inside a dataset (e.g. "uom_name" in dataset "dim_uom"). Use the LLM
            # to decide what the user is actually asking about before giving up.
            field_results = await self._resolve_field_lookup(term_name, trace_id=trace_id)
            kind = await self._classify_term_kind(
                question, term_name, has_field_hit=bool(field_results), trace_id=trace_id)
            log.info("structured_low_trust", trace_id=trace_id, term=term_name,
                     top=last_error.resolved.name if last_error and last_error.resolved else None,
                     top_score=last_error.resolved.score if last_error and last_error.resolved else None,
                     llm_kind=kind, field_hits=len(field_results))
            if kind == "field" and field_results:
                return field_results
            if kind == "glossary":
                resolution = await self._entity_resolver.resolve(
                    term_name, entity_type="glossary_term", trace_id=trace_id)
                if resolution.resolved and self._trusted_resolution(resolution):
                    return await self._resolve_to_results(resolution, trace_id=trace_id)
            if kind == "dataset":
                resolution = await self._entity_resolver.resolve(
                    term_name, entity_type="dataset", trace_id=trace_id)
                if resolution.resolved and self._trusted_resolution(resolution):
                    return await self._resolve_to_results(resolution, trace_id=trace_id)
            if field_results:
                return field_results
            return []

        if intent == QueryIntent.OWNER_LOOKUP:
            entity_name = inferred_entity or self._extract_name(question, [
                "ai sở hữu", "ai là", "ai la", "ai là chủ", "business owner",
                "owner", "của ai", "cua ai", "who owns", "who is the owner of",
                "thuộc về ai", "thuộc ai", "thuộc sở hữu", "sở hữu của ai",
                "thuộc về", "thuộc", "người sở hữu", "chủ sở hữu",
                "belongs to whom", "owned by whom", "whose",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.ENTITY_DOMAIN:
            entity_name = inferred_entity or self._extract_name(question, [
                "thuộc về domain", "thuộc domain", "thuộc lĩnh vực", "thuộc miền",
                "thuộc về", "thuộc", "domain nào", "lĩnh vực nào", "miền nào",
                "domain của", "lĩnh vực của", "nằm trong",
                "belongs to which domain", "which domain", "what domain",
                "belongs to", "belong to", "does it belong", "belongs",
                "belong", "does", "thuộc của",
                "là gì", "la gi", "nào", "nao",
            ])
            if not entity_name:
                entity_name = inferred_entity or ""
            resolution = await self._entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.TERM_TO_DATASETS:
            term_name = inferred_entity or self._extract_name(question, [
                "dataset nào gắn term", "dataset nào có term",
                "find dataset", "entity nào gắn", "gắn term",
            ])
            if not term_name:
                log.info("structured_no_term", trace_id=trace_id, intent=intent.value,
                         question=question[:100])
                return []
            resolution = await self._entity_resolver.resolve(term_name, entity_type="glossary_term",
                                                             trace_id=trace_id)
            if resolution.resolved:
                all_entities = await self._entity_repo.list_by_type("dataset")
                term_urn = resolution.resolved.urn
                matching = [e for e in all_entities if e.payload and term_urn in (e.payload.get("glossary_terms") or [])]
                results: list[SearchResult] = []
                for e in matching:
                    payload = e.payload or {}
                    content = self._entity_payload_to_text(e.entity_type, payload)
                    results.append(SearchResult(
                        urn=e.urn, entity_type=e.entity_type, name=e.display_name or e.name,
                        score=0.9, datahub_url=e.datahub_url,
                        payload={**payload, "content": content},
                    ))
                log.info("structure_term_to_datasets", trace_id=trace_id, term=term_name,
                         matching=len(matching))
                return results
            return []

        if intent == QueryIntent.LINEAGE:
            entity_name = inferred_entity or self._extract_name(question, [
                "lấy dữ liệu từ đâu", "upstream", "downstream",
                "nguồn", "phụ thuộc", "source of data",
                "thông tin về lineage", "thông tin về linage",
                "lineage", "linage", "thông tin", "thong tin",
                "luồng dữ liệu", "dòng dữ liệu", "luong du lieu", "dong du lieu",
                "data flow", "flow of data", "như nào", "nhu nao", "như thế nào",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, entity_type="dataset",
                                                             trace_id=trace_id)
            if resolution.resolved:
                entity_db = await self._entity_repo.get_by_urn(resolution.resolved.urn)
                if entity_db and entity_db.payload:
                    main_content = self._entity_payload_to_text(entity_db.entity_type, entity_db.payload)

                    upstreams: list[str] = []
                    downstreams: list[str] = []
                    try:
                        up = await self._source.get_lineage(entity_db.urn, direction="upstream")
                        down = await self._source.get_lineage(entity_db.urn, direction="downstream")
                        upstreams = [r["entity"]["urn"] for r in up.get("relationships", [])
                                     if (r.get("entity") or {}).get("urn")]
                        downstreams = [r["entity"]["urn"] for r in down.get("relationships", [])
                                       if (r.get("entity") or {}).get("urn")]
                    except Exception:
                        log.exception("lineage_live_failed", trace_id=trace_id, urn=entity_db.urn)

                    log.info("structure_lineage", trace_id=trace_id,
                             entity=entity_db.display_name or entity_db.name,
                             upstream_count=len(upstreams), downstream_count=len(downstreams),
                             source="live")

                    payload = {
                        **entity_db.payload,
                        "upstreams": upstreams,
                        "downstreams": downstreams,
                        "content": f"Entity: {main_content}\nUpstream: {', '.join(upstreams) if upstreams else 'None'}\nDownstream: {', '.join(downstreams) if downstreams else 'None'}",
                    }
                    results: list[SearchResult] = []
                    results.append(SearchResult(
                        urn=entity_db.urn, entity_type=entity_db.entity_type,
                        name=entity_db.display_name or entity_db.name,
                        score=1.0, datahub_url=entity_db.datahub_url,
                        payload=payload,
                    ))

                    async def _related(urn: str, score: float) -> SearchResult:
                        rel_entity = await self._entity_repo.get_by_urn(urn)
                        name = (rel_entity.display_name or rel_entity.name) if rel_entity else urn
                        content = self._entity_payload_to_text(
                            rel_entity.entity_type if rel_entity else "dataset",
                            rel_entity.payload if rel_entity else {},
                        ) if rel_entity else urn
                        return SearchResult(
                            urn=urn,
                            entity_type=rel_entity.entity_type if rel_entity else "dataset",
                            name=name, score=score,
                            datahub_url=rel_entity.datahub_url if rel_entity else None,
                            payload={"content": f"Related entity: {content}"},
                        )

                    for u in upstreams:
                        results.append(await _related(u, 0.8))
                    for d in downstreams:
                        results.append(await _related(d, 0.75))
                    return results
            return []

        if intent == QueryIntent.SCHEMA_LOOKUP:
            entity_name = inferred_entity or self._extract_name(question, [
                "field", "schema", "cột", "trường", "có những",
                "columns", "fields", "thuộc tính",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, entity_type="dataset",
                                                             trace_id=trace_id)
            if resolution.resolved and self._trusted_resolution(resolution):
                return await self._resolve_to_results(resolution, trace_id=trace_id)
            # The asked name may be a FIELD (column) inside one or more datasets,
            # e.g. "trường uom_name là gì?" -> uom_name belongs to dataset dim_uom.
            field_results = await self._resolve_field_lookup(entity_name, trace_id=trace_id)
            if field_results:
                log.info("structured_field_lookup", trace_id=trace_id,
                         field=entity_name, datasets=len(field_results))
                return field_results
            return await self._resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.DATAHUB_URL:
            entity_name = inferred_entity or self._extract_name(question, [
                "link", "url", "datahub", "đường dẫn",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.ENTITY_EXISTS:
            entity_name = inferred_entity or self._extract_name(question, [
                "có tồn tại", "tồn tại không", "exist",
                "có không", "does.*exist",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, trace_id=trace_id)
            return await self._resolve_to_results(resolution, trace_id=trace_id)

        if intent == QueryIntent.CERTIFIED_LIST:
            entities = await self._entity_repo.list_certified()
            return self._entities_to_results(entities)

        if intent in (QueryIntent.DOMAIN_QUERY, QueryIntent.PLATFORM_QUERY,
                      QueryIntent.TAG_QUERY, QueryIntent.ENTITIES_BY_OWNER):
            value = inferred_entity or self._extract_filter_value(question, intent)
            if not value:
                return []
            log.info("structured_filter", trace_id=trace_id, intent=intent.value,
                     value=value, question=question[:100])
            if intent == QueryIntent.DOMAIN_QUERY:
                entities = await self._entity_repo.list_by_domain(value)
            elif intent == QueryIntent.PLATFORM_QUERY:
                entities = await self._entity_repo.list_by_platform(value)
            elif intent == QueryIntent.TAG_QUERY:
                entities = await self._entity_repo.list_by_tag(value)
            else:
                entities = await self._entity_repo.list_by_owner(value)
            log.info("structured_filter_result", trace_id=trace_id, intent=intent.value,
                     value=value, count=len(entities))
            return self._entities_to_results(entities)

        return []

    @staticmethod
    def _extract_filter_value(question: str, intent: QueryIntent) -> str:
        q = _norm_vn(question)
        for pattern in _FILTER_VALUE_PATTERNS.get(intent, []):
            m = re.search(pattern, q, re.I)
            if m:
                tokens = [
                    t for t in m.group(1).split()
                    if t not in _CONNECTOR_WORDS
                ]
                return " ".join(tokens).strip("?!.,:")
        return ""

    def _entities_to_results(self, entities: Sequence) -> list[SearchResult]:
        results: list[SearchResult] = []
        for e in entities:
            payload = e.payload or {}
            content = self._entity_payload_to_text(e.entity_type, payload)
            results.append(SearchResult(
                urn=e.urn, entity_type=e.entity_type,
                name=e.display_name or e.name,
                score=0.9, datahub_url=e.datahub_url,
                payload={**payload, "content": content},
            ))
        return results

    @staticmethod
    def _detect_listing(question: str) -> str | None:
        cleaned = question.lower().strip().rstrip("?!.")
        for pattern in _LISTING_PATTERNS:
            m = pattern.match(cleaned)
            if m:
                type_word = m.group(1).lower().strip()
                for key, entity_type in _LISTING_TYPE_MAP.items():
                    if type_word.startswith(key) or key.startswith(type_word):
                        return entity_type
        return None

    @staticmethod
    def _detect_entity_type(question: str) -> str | None:
        for pattern, entity_type in _ENTITY_TYPE_PATTERNS:
            if pattern.search(question):
                return entity_type
        return None

    async def _build_lineage_data(self, result: SearchResult) -> LineageData | None:
        payload = result.payload or {}
        main_urn = result.urn

        def _dedupe(urns: Sequence[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for u in urns:
                if not u or u == main_urn or u in seen:
                    continue
                seen.add(u)
                out.append(u)
            return out

        upstreams = _dedupe(payload.get("upstreams", []) or [])
        downstreams = _dedupe(payload.get("downstreams", []) or [])
        # A dataset appearing on BOTH sides would render twice; keep it upstream only.
        upstream_set = set(upstreams)
        downstreams = [d for d in downstreams if d not in upstream_set]
        if not upstreams and not downstreams:
            return None

        async def _node(urn: str) -> LineageNode:
            e = await self._entity_repo.get_by_urn(urn)
            if e:
                return LineageNode(
                    name=e.display_name or e.name, urn=e.urn,
                    url=e.datahub_url, entity_type=e.entity_type,
                )
            return LineageNode(name=urn, urn=urn)

        up_nodes = [await _node(u) for u in upstreams]
        down_nodes = [await _node(d) for d in downstreams]
        return LineageData(
            entity_name=result.name,
            entity_urn=result.urn,
            entity_url=result.datahub_url,
            upstreams=up_nodes,
            downstreams=down_nodes,
        )

    async def _build_lineage_answer(self, result: SearchResult,
                                    history: list[tuple[str, str]] | None = None) -> tuple[str, list, str]:
        """Deterministic lineage answer, built from the SAME payload that drives the SVG."""
        from retrieval.citation import Citation

        payload = result.payload or {}
        main_urn = result.urn

        def _dedupe(urns):
            seen, out = set(), []
            for u in urns:
                if not u or u == main_urn or u in seen:
                    continue
                seen.add(u)
                out.append(u)
            return out

        upstreams = _dedupe(payload.get("upstreams", []) or [])
        downstreams = _dedupe(payload.get("downstreams", []) or [])
        up_set = set(upstreams)
        downstreams = [d for d in downstreams if d not in up_set]

        async def _name(urn: str) -> str:
            e = await self._entity_repo.get_by_urn(urn)
            return (e.display_name or e.name) if e else urn

        async def _url(urn: str) -> str | None:
            e = await self._entity_repo.get_by_urn(urn)
            return e.datahub_url if e else None

        parts: list[str] = []
        citations: list = []
        idx = 1

        async def _fmt(urn: str) -> str:
            nonlocal idx
            cid = f"E{idx}"
            idx += 1
            citations.append(Citation(cid=cid, source_type="datahub_entity",
                                      entity_urn=urn, entity_name=await _name(urn),
                                      url=await _url(urn)))
            return f"{await _name(urn)} [{cid}]"

        if upstreams:
            names = ", ".join([await _fmt(u) for u in upstreams])
            parts.append(f"{len(upstreams)} upstream: {names}")
        if downstreams:
            names = ", ".join([await _fmt(d) for d in downstreams])
            parts.append(f"{len(downstreams)} downstream: {names}")

        answer = mask_secrets(
            f"Dataset {result.name} có lineage theo DataHub: " + "; ".join(parts) + "."
        )
        return answer, citations, result.name

    @staticmethod
    @staticmethod
    def _build_access_denied_message(
        user: UserContext | None, entity_names: Sequence[str] | None
    ) -> str:
        names = [n for n in (entity_names or []) if n]
        entity_part = (
            f" về {', '.join(names[:2])}" if names else ""
        )
        group_part = ""
        if user and user.display_name:
            group_part = f", {user.display_name}"
        elif user and user.user_id:
            group_part = f", {user.user_id}"
        return (
            f"Xin lỗi{group_part}, tài khoản của bạn hiện không có quyền truy cập"
            f" vào dữ liệu{entity_part} này (bị giới hạn theo phòng ban)."
            " Vui lòng đăng nhập bằng tài khoản có quyền phù hợp hoặc liên hệ quản trị viên."
        )

    @staticmethod
    def _short_negative_answer(intent: QueryIntent, results: Sequence[SearchResult]) -> str | None:
        if intent == QueryIntent.OWNER_LOOKUP and len(results) == 1:
            payload = results[0].payload or {}
            owners = payload.get("owners")
            if not owners:
                return f"Dataset {results[0].name} hiện không có người sở hữu (owner)."
        if intent == QueryIntent.LINEAGE and len(results) == 1:
            payload = results[0].payload or {}
            if not payload.get("upstreams") and not payload.get("downstreams"):
                return f"Dataset {results[0].name} hiện không có lineage (upstream/downstream) được ghi nhận."
        # Guardrail #1/#2: an absence query with no metadata match is a grounded
        # negative answer ("does not exist in the catalog") rather than a guess.
        if intent == QueryIntent.ENTITY_EXISTS and len(results) == 0:
            return "Entity này không tồn tại trong metadata DataHub hiện có."
        return None

    async def _collect_domain_names(self) -> list[str]:
        """Distinct domain names present in entity payloads."""
        import unicodedata

        entities = await self._entity_repo.list_all(limit=2000)
        seen: dict[str, str] = {}
        for e in entities:
            domain = (e.domain or (e.payload or {}).get("domain") or "").strip()
            if not domain:
                continue
            key = unicodedata.normalize("NFKD", domain.lower()).encode("ascii", "ignore").decode("ascii")
            seen.setdefault(key, domain)
        return list(seen.values())

    async def _suggest_entity(self, original: str, entity_type: str | None,
                              question: str, trace_id: str) -> Suggestion | None:
        """Find a likely intended entity name for a misspelled one, using the LLM."""
        if not original:
            return None
        if entity_type == "glossary_term":
            entities = await self._entity_repo.list_all(entity_type="glossary_term", limit=2000)
            candidates = sorted({(e.display_name or e.name) for e in entities})
        elif entity_type == "dataset":
            entities = await self._entity_repo.list_all(entity_type="dataset", limit=2000)
            candidates = sorted({(e.display_name or e.name) for e in entities})
        else:
            candidates = sorted(await self._collect_domain_names())

        if not candidates:
            return None

        scored: list[tuple[float, str]] = []
        for c in candidates:
            sc = fuzzy_score(original, c)
            if sc >= 0.45:
                scored.append((sc, c))
        scored.sort(key=lambda t: -t[0])
        shortlist = [c for _, c in scored[:10]]
        if not shortlist:
            return None
        log.info("suggestion_shortlist", trace_id=trace_id, original=original,
                 entity_type=entity_type, shortlist=shortlist)

        if len(shortlist) == 1 and scored[0][0] >= 0.65:
            chosen: str | None = scored[0][1]
        # Top candidate clearly dominates the runner-up -> pick it without the LLM.
        elif (len(scored) >= 2
              and scored[0][0] >= 0.65
              and (scored[0][0] - scored[1][0]) >= 0.15):
            chosen = scored[0][1]
        else:
            chosen = await self._llm_pick_suggestion(original, shortlist, question)
        if not chosen:
            return None
        return Suggestion(original=original, suggested=chosen)

    async def _llm_pick_suggestion(self, original: str, shortlist: list[str],
                                   question: str) -> str | None:
        """Ask the LLM which candidate is the intended (corrected) name."""
        prompt = (
            "Người dùng đang hỏi về một glossary term hoặc domain trong hệ thống data catalog "
            "nhưng có thể đã gõ sai. Dựa vào ngữ cảnh câu hỏi, hãy chọn tên ĐÚNG NHẤT mà "
            "người dùng muốn hỏi.\n\n"
            f"Câu hỏi: {question}\n"
            f"Tên người dùng đã gõ: '{original}'\n\n"
            "Danh sách ứng viên có sẵn trong hệ thống:\n"
            + "\n".join(f"- {c}" for c in shortlist)
            + "\n\nChỉ trả về đúng một tên ứng viên được chọn. "
              "Nếu không có ứng viên nào khớp ý người dùng, trả về: NONE. "
              "Không thêm giải thích hay dấu câu."
        )
        try:
            raw = (await self._llm.generate(prompt) or "").strip()
        except Exception:
            log.exception("llm_suggestion_failed")
            return None
        if not raw or raw.upper() == "NONE":
            return None
        best = max(shortlist, key=lambda c: fuzzy_score(raw, c))
        if fuzzy_score(raw, best) >= 0.55:
            return best
        return None

    async def _deterministic_listing(self, question: str, intent: QueryIntent,
                                     user_ctx: UserContext, trace_id: str,
                                     conversation_id: str,
                                     suggested_name: str | None = None) -> ChatResponse | None:
        entity_type = self._detect_entity_type(question)
        label = _ENTITY_TYPE_LABELS.get(entity_type, "assets")

        if intent == QueryIntent.DOMAIN_QUERY and _DOMAIN_LISTING_RE.search(question):
            all_entities = await self._entity_repo.list_all(limit=2000)
            if self._auth_service:
                accessible = await self._auth_service.filter_accessible_urns(
                    user_ctx, [e.urn for e in all_entities]
                )
                all_entities = [e for e in all_entities if e.urn in accessible]
            counts: dict[str, int] = {}
            for e in all_entities:
                domain = (e.domain or (e.payload or {}).get("domain") or "").strip()
                if domain:
                    counts[domain] = counts.get(domain, 0) + 1
            is_count = bool(re.search(
                r"(có bao nhiêu|co bao nhieu|bao nhiêu|how many|số lượng|so luong)",
                question, re.I))
            if is_count:
                answer_text = f"Có tổng cộng {len(counts)} domain trong hệ thống."
            else:
                lines = [f"Có tổng cộng {len(counts)} domain trong hệ thống:"]
                for d, c in sorted(counts.items(), key=lambda kv: (-kv[1], _norm_vn(kv[0]))):
                    lines.append(f"- {d} ({c} assets)")
                answer_text = mask_secrets("\n".join(lines))
            log.info("route_domain_listing", trace_id=trace_id, question=question[:100],
                     domain_count=len(counts), source="deterministic_db")
            return ChatResponse(
                answer=answer_text, intent="DOMAIN_QUERY", entities=[],
                confidence="high", ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=conversation_id,
            )

        if intent == QueryIntent.CERTIFIED_LIST:
            entities = await self._entity_repo.list_certified(entity_type)
            dimension, value = "certified", ""
        else:
            dimension, value = "", ""
            for try_intent in (QueryIntent.DOMAIN_QUERY, QueryIntent.TAG_QUERY,
                               QueryIntent.ENTITIES_BY_OWNER, QueryIntent.PLATFORM_QUERY):
                v = self._extract_filter_value(question, try_intent)
                if v:
                    if v in _ANAPHORA_WORDS:
                        return None
                    dimension = _DIMENSION_MAP[try_intent]
                    value = v
                    break
            if suggested_name and dimension == "domain":
                value = suggested_name
            if dimension == "domain":
                entities = await self._entity_repo.list_by_domain(value, entity_type)
            elif dimension == "platform":
                entities = await self._entity_repo.list_by_platform(value, entity_type)
            elif dimension == "tag":
                entities = await self._entity_repo.list_by_tag(value, entity_type)
            elif dimension == "owner":
                entities = await self._entity_repo.list_by_owner(value, entity_type)
            elif entity_type:
                entities = await self._entity_repo.list_by_type(entity_type, limit=500)
            else:
                entities = await self._entity_repo.list_all(limit=500)

            if (dimension == "domain" and not entities and not suggested_name
                    and intent != QueryIntent.CERTIFIED_LIST):
                suggestion = await self._suggest_entity(value, None, question, trace_id)
                if suggestion is not None:
                    answer_text = (
                        f"'{suggestion.original}' không tồn tại trong hệ thống. "
                        f"Ý bạn là '{suggestion.suggested}'?"
                    )
                    log.info("chat_suggestion", trace_id=trace_id, intent=intent.value,
                             original=suggestion.original, suggested=suggestion.suggested,
                             conversation_id=conversation_id)
                    return ChatResponse(
                        answer=answer_text, intent=intent.value, confidence="high",
                        ambiguous=False, insufficient_context=False,
                        trace_id=trace_id, conversation_id=conversation_id,
                        suggestion=suggestion,
                    )

        if self._auth_service:
            accessible = await self._auth_service.filter_accessible_urns(
                user_ctx, [e.urn for e in entities]
            )
            entities = [e for e in entities if e.urn in accessible]

        count = len(entities)
        scope = self._scope_text(dimension, value, entities)
        lines = [f"Có tổng cộng {count} {label}{scope}."]

        platforms: dict[str, list[str]] = {}
        for e in entities:
            p = e.platform or "unknown"
            platforms.setdefault(p, []).append(e.display_name or e.name)
        for plat, names in sorted(platforms.items()):
            sample = sorted(names)
            shown = ", ".join(sample[:50])
            lines.append(f"\n{plat}: {shown}{', ...' if len(sample) > 50 else ''}")
        answer_text = mask_secrets("\n".join(lines))

        entity_list = [
            EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url)
            for e in entities[:200]
        ]

        return ChatResponse(
            answer=answer_text, intent=intent.value, entities=entity_list,
            confidence="high", ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=conversation_id,
        )

    @staticmethod
    def _scope_text(dimension: str, value: str, entities: Sequence[Any]) -> str:
        if not dimension:
            return ""
        if dimension == "domain":
            display = ""
            if value:
                display = f"'{value}'"
                for e in entities:
                    if e.domain:
                        display = f"'{e.domain}'"
                        break
            return f" trong lĩnh vực {display}" if display else ""
        if dimension == "platform":
            return f" trên platform '{value}'" if value else ""
        if dimension == "tag":
            return f" có tag '{value}'" if value else ""
        if dimension == "owner":
            return f" thuộc sở hữu '{value}'" if value else ""
        if dimension == "certified":
            return " đã được certified"
        return ""

    async def _listing_retrieval(self, entity_type: str) -> list[SearchResult]:
        count = await self._entity_repo.count_by_type(entity_type)
        entities = await self._entity_repo.list_by_type(entity_type, limit=200)
        platforms: dict[str, list[str]] = {}
        domains: dict[str, list[str]] = {}
        for e in entities:
            p = e.platform or "unknown"
            platforms.setdefault(p, []).append(e.display_name or e.name)
        summary_parts = [f"Có tổng cộng {count} {entity_type} trong hệ thống."]
        if platforms:
            summary_parts.append(f"Platforms: {', '.join(sorted(platforms.keys()))}.")
            for plat, names in sorted(platforms.items()):
                summary_parts.append(f"- {plat}: {', '.join(sorted(names)[:30])}{'...' if len(names) > 30 else ''}")
        summary_text = "\n".join(summary_parts)
        results: list[SearchResult] = []
        for e in entities[:20]:
            payload = e.payload or {}
            content = self._entity_payload_to_text(e.entity_type, payload)
            results.append(SearchResult(
                urn=e.urn, entity_type=e.entity_type,
                name=e.display_name or e.name,
                score=1.0, datahub_url=e.datahub_url,
                payload={**payload, "content": content},
            ))
        if results:
            results[0].payload["content"] = summary_text + "\n\n" + results[0].payload.get("content", "")
        return results

    @staticmethod
    def _trusted_resolution(resolution: ResolutionResult) -> bool:
        """True when a resolution is confident enough to answer without asking.

        Exact name/URN matches (1.0) and high-confidence prefix matches (0.9)
        pass. Low-trust fuzzy/substring resolutions (e.g. typo'd "ABV Matching"
        -> "3-Way Matching" at 0.77) fail so the caller can offer a suggestion.
        """
        return bool(
            resolution.resolved
            and resolution.resolved.score >= settings.ENTITY_RESOLVER_TRUST_THRESHOLD
        )

    async def _resolve_to_results(self, resolution: ResolutionResult,
                                  trace_id: str | None = None) -> list[SearchResult]:
        from retrieval.hybrid_search import SearchResult
        if resolution.resolved:
            entity_db = await self._entity_repo.get_by_urn(resolution.resolved.urn)
            if entity_db:
                payload = entity_db.payload or {}
                content = self._entity_payload_to_text(entity_db.entity_type, payload)
                log.info("resolve_to_results", trace_id=trace_id,
                         resolved=entity_db.display_name or entity_db.name,
                         urn=entity_db.urn, candidates=len(resolution.candidates))
                return [SearchResult(
                    urn=entity_db.urn, entity_type=entity_db.entity_type,
                    name=entity_db.display_name or entity_db.name,
                    score=1.0, datahub_url=entity_db.datahub_url,
                    payload={**payload, "content": content},
                )]
        log.info("resolve_to_results", trace_id=trace_id,
                 resolved=None, candidates=len(resolution.candidates))
        return []

    async def _resolve_field_lookup(self, field_name: str,
                                    trace_id: str | None = None) -> list[SearchResult]:
        """Find the dataset(s) that contain a schema field named ``field_name``.

        Returns a SearchResult per matching dataset whose content highlights the
        field, so the generator can explain what the column means.
        """
        from retrieval.hybrid_search import SearchResult
        if not field_name:
            return []
        target = _norm_vn(field_name).replace(" ", "_")
        datasets = await self._entity_repo.list_by_type("dataset", limit=2000)
        results: list[SearchResult] = []
        seen_urns: set[str] = set()
        for ds in datasets:
            if ds.urn in seen_urns:
                continue
            fields = (ds.payload or {}).get("schema_fields") or []
            match = None
            for f in fields:
                fname = (f or {}).get("name") or ""
                if _norm_vn(fname).replace(" ", "_") == target:
                    match = f
                    break
            if match is None:
                continue
            seen_urns.add(ds.urn)
            payload = {**(ds.payload or {})}
            fdesc = (match.get("description") or "").strip()
            ftype = (match.get("type") or "").strip()
            field_line = f"- {match.get('name', field_name)} ({ftype})"
            if fdesc:
                field_line += f": {fdesc}"
            content = self._entity_payload_to_text(ds.entity_type, payload)
            content = f"Trường '{match.get('name', field_name)}' thuộc dataset {ds.display_name or ds.name}:\n{field_line}\n\n{content}"
            results.append(SearchResult(
                urn=ds.urn, entity_type=ds.entity_type,
                name=ds.display_name or ds.name,
                score=0.95, datahub_url=ds.datahub_url,
                payload={**payload, "content": content},
            ))
        log.info("field_lookup", trace_id=trace_id, field=field_name, hits=len(results))
        return results

    async def _classify_term_kind(self, question: str, term: str,
                                  has_field_hit: bool,
                                  trace_id: str | None = None) -> str:
        """Use the LLM to decide what kind of entity the user is asking about.

        Returns one of: ``glossary``, ``dataset``, ``field``, or ``unknown``.
        This disambiguates cases like "uom_name là gì?" where the name is a
        column of a dataset (dim_uom) rather than a glossary term.
        """
        if not term:
            return "unknown"
        q_norm = _norm_vn(question)
        mentions_field = bool(
            re.search(r"(trường|truong|field|fields|cột|cot|column|columns|schema|thuộc tính|thuoc tinh)", q_norm, re.I)
        )
        mentions_dataset = bool(
            re.search(r"(dataset|data set|bảng|bang|table|dim_|fact_)", q_norm, re.I)
        )
        # Strong local signals override the LLM call.
        if mentions_field and has_field_hit and not mentions_dataset:
            return "field"
        if mentions_dataset and not mentions_field:
            return "dataset"
        if mentions_field and not has_field_hit:
            return "glossary"

        glossary_hint = await self._fuzzy_name_match(term, "glossary_term")
        dataset_hint = await self._fuzzy_name_match(term, "dataset")
        prompt = (
            "Bạn là trợ lý metadata DataHub. Người dùng đang hỏi về một thuật ngữ dữ liệu.\n"
            f"Câu hỏi: {question}\n"
            f"Tên cần phân loại: '{term}'\n"
            f"Glossary term khớp nhất trong hệ thống: {glossary_hint or 'không có'}\n"
            f"Dataset khớp nhất trong hệ thống: {dataset_hint or 'không có'}\n"
            f"Tên này có xuất hiện như một field (cột) trong dataset không: {'CÓ' if has_field_hit else 'KHÔNG'}\n\n"
            "Hãy xác định người dùng đang hỏi về loại thực thể nào:\n"
            "- 'glossary': một glossary term (khái niệm/định nghĩa nghiệp vụ)\n"
            "- 'dataset': một dataset/bảng dữ liệu\n"
            "- 'field': một cột/trường bên trong dataset\n\n"
            "Chỉ trả về ĐÚNG MỘT từ trong ba từ: glossary, dataset, hoặc field. "
            "Không thêm giải thích hay dấu câu."
        )
        try:
            raw = (await self._llm.generate(prompt) or "").strip().lower()
        except Exception:
            log.exception("llm_term_kind_failed", trace_id=trace_id, term=term)
            return "unknown"
        for kind in ("glossary", "dataset", "field"):
            if kind in raw:
                return kind
        log.warning("llm_term_kind_unparsed", trace_id=trace_id, term=term, raw=raw[:80])
        return "unknown"

    async def _fuzzy_name_match(self, term: str, entity_type: str) -> str | None:
        """Best fuzzy match for ``term`` among entities of ``entity_type``."""
        entities = await self._entity_repo.list_all(entity_type=entity_type, limit=2000)
        best, best_score = None, 0.0
        for e in entities:
            sc = fuzzy_score(term, e.display_name or e.name)
            if sc > best_score:
                best, best_score = (e.display_name or e.name), sc
        return best if best_score >= 0.3 else None

    @staticmethod
    def _entity_payload_to_text(entity_type: str, payload: dict) -> str:
        parts = []
        name = payload.get("display_name") or payload.get("name", "")
        if name:
            parts.append(f"Name: {name}")
        desc = payload.get("description", "")
        if desc:
            parts.append(f"Description: {desc}")
        domain = payload.get("domain", "")
        if domain:
            parts.append(f"Domain: {domain}")
        platform = payload.get("platform", "")
        if platform:
            parts.append(f"Platform: {platform}")
        owners = payload.get("owners", [])
        if owners:
            owner_names = [o.get("name", "") for o in owners]
            parts.append(f"Owners: {', '.join(owner_names)}")
        fields = payload.get("schema_fields", [])
        if fields:
            field_lines = []
            for f in fields:
                desc = f.get("description", "")
                field_lines.append(f"  - {f.get('name', '')} ({f.get('type', '')}): {desc}" if desc else f"  - {f.get('name', '')} ({f.get('type', '')})")
            parts.append("Schema fields:\n" + "\n".join(field_lines))
        terms = payload.get("glossary_terms", [])
        if terms:
            parts.append(f"Glossary terms: {', '.join(terms)}")
        upstreams = payload.get("upstreams", [])
        if upstreams:
            parts.append(f"Upstream: {', '.join(upstreams)}")
        downstreams = payload.get("downstreams", [])
        if downstreams:
            parts.append(f"Downstream: {', '.join(downstreams)}")
        return " | ".join(parts)

    async def _entity_to_result(self, urn: str) -> SearchResult | None:
        entity = await self._entity_repo.get_by_urn(urn)
        if entity:
            return SearchResult(
                urn=entity.urn, entity_type=entity.entity_type,
                name=entity.display_name or entity.name,
                score=0.9, datahub_url=entity.datahub_url,
                payload=entity.payload,
            )
        return None
