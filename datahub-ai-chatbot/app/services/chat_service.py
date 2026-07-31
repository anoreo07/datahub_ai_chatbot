import re
import uuid
from collections.abc import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.chat import ChatResponse, CitationItem, EntityItem
from app.services.conversation import get_conversation_memory
from config.prompts import ACCESS_DENIED_RESPONSE, NO_ANSWER_RESPONSE
from database.repositories.entity_repository import EntityRepository
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from llm.generator import AnswerGenerator
from retrieval.entity_resolver import EntityResolver, ResolutionResult
from retrieval.hybrid_search import HybridSearch, SearchResult
from retrieval.intent import QueryIntent, _norm_vn, classify_intent
from retrieval.reranker import Reranker

# Listing patterns - must NOT contain a specific entity name before the pattern
_LISTING_PATTERNS: list[re.Pattern] = [
    re.compile(r'^(?:có các|các)\s+(dataset|dashboard|glossary)\s+(?:gì|nào)\??$', re.I),
    re.compile(r'^liệt kê\s+(?:các\s+)?(dataset|dashboard|glossary(?:\s+term)?)\s*$', re.I),
    re.compile(r'^list\s+(?:all\s+)?(datasets|dashboards|glossary\s+terms)\s*$', re.I),
    re.compile(r'^danh sách\s+(?:các\s+)?(dataset|dashboard|glossary)\s*$', re.I),
    re.compile(r'^show\s+(?:all\s+)?(datasets|dashboards|glossary)\s*$', re.I),
    re.compile(r'^có những (dataset|dashboard|glossary) nào\??$', re.I),
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
        r"(?:domain|mien)\s*[:=]?\s*([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
        r"(?:trong|thuoc|in|belonging to|belong to)\s+(?:the\s+)?(?:domain|mien)\s+([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
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

log = structlog.get_logger()

_GREETING_RESPONSES = [
    "Xin chào! Tôi là trợ lý DataHub. Tôi có thể giúp bạn tra cứu datasets, glossary terms, owners, lineage và các thông tin metadata khác.",
    "Chào bạn! Tôi có thể hỗ trợ bạn tra cứu thông tin dữ liệu trong hệ thống. Bạn muốn tìm hiểu về điều gì?",
    "Xin chào! Hãy hỏi tôi về bất kỳ thông tin metadata nào như datasets, dashboards, glossary terms, hoặc lineage.",
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
        self._source: DataHubSource = create_datahub_source()
        self._memory = get_conversation_memory()

    async def answer(self, question: str, user: UserContext | None = None,
                     conversation_id: str | None = None) -> ChatResponse:
        trace_id = uuid.uuid4().hex[:12]
        intent = classify_intent(question)
        cid = conversation_id or trace_id

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

        listing_type = self._detect_listing(question)
        if listing_type:
            entity_type_label = "glossary terms" if listing_type == "glossary_term" else f"{listing_type}s"
            count = await self._entity_repo.count_by_type(listing_type)
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
            answer_text = "\n".join(lines)
            
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

        history = await self._memory.load_history_from_db(self._session, uid, cid)

        import unicodedata
        q_norm = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")

        _ANAPHORA = {"đó", "do", "nó", "no", "ấy", "ay", "này", "nay", "đây", "day", "kia"}
        has_anaphora = any(a in question.lower() for a in _ANAPHORA) or any(a in q_norm for a in ["do", "no", "ay", "nay", "day", "kia"])
        is_ellipsis = q_norm.startswith(("con ", "the ", "the con"))

        if (has_anaphora or is_ellipsis) and len(history) > 0:
            if is_ellipsis:
                m = re.search(r'^(?:the\s+con\s+|con\s+|the\s+)(.+?)\??\s*$', q_norm)
                entity_from_q = m.group(1).strip() if m else ""
                inferred_entity = entity_from_q if entity_from_q else None
            else:
                inferred_entity = self._infer_entity_from_history(history)
            if inferred_entity:
                if intent in (QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
                              QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
                              QueryIntent.SCHEMA_LOOKUP, QueryIntent.DATAHUB_URL,
                              QueryIntent.ENTITY_EXISTS, QueryIntent.DOMAIN_QUERY,
                              QueryIntent.PLATFORM_QUERY, QueryIntent.TAG_QUERY,
                              QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST):
                    results = await self._structured_retrieval(intent, question, inferred_entity=inferred_entity)
                else:
                    results = []
                    for try_intent in [
                        QueryIntent.OWNER_LOOKUP, QueryIntent.SCHEMA_LOOKUP,
                        QueryIntent.LINEAGE, QueryIntent.TERM_DEFINITION,
                        QueryIntent.TERM_TO_DATASETS, QueryIntent.DATAHUB_URL,
                        QueryIntent.ENTITY_EXISTS,
                    ]:
                        results = await self._structured_retrieval(try_intent, question, inferred_entity=inferred_entity)
                        if results:
                            intent = try_intent
                            break
            else:
                results = []
        elif intent in (QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
                        QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
                        QueryIntent.SCHEMA_LOOKUP, QueryIntent.DATAHUB_URL,
                        QueryIntent.ENTITY_EXISTS, QueryIntent.DOMAIN_QUERY,
                        QueryIntent.PLATFORM_QUERY, QueryIntent.TAG_QUERY,
                        QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST):
            results = await self._structured_retrieval(intent, question)
        else:
            results = await self._hybrid_search.search(question)

        if self._auth_service:
            total_before = len(results)
            accessible = await self._auth_service.filter_accessible_urns(
                user_ctx, [r.urn for r in results]
            )
            results = [r for r in results if r.urn in accessible]
            denied_count = total_before - len(results)
        else:
            denied_count = 0

        results = await self._reranker.rerank(question, results)

        insufficient_context = len(results) == 0
        if insufficient_context and denied_count > 0:
            await self._memory.add_turn_db(self._session, uid, cid, question, ACCESS_DENIED_RESPONSE)
            answer_text = ACCESS_DENIED_RESPONSE
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid,
                insufficient_context=True,
            )

        answer_text, citations, docs, context_xml, confidence = await self._generator.generate(
            question, results, intent, history=history
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

        ambiguous = (
            len(results) > 1
            and abs(results[0].score - results[1].score) < 0.15
            and results[1].score > 0.5
        )
        insufficient_context = len(docs) == 0 or confidence == "low"

        await self._memory.add_turn_db(self._session, uid, cid, question, answer_text)

        log.info("chat_response", trace_id=trace_id, intent=intent.value,
                 entity_count=len(entity_list), citation_count=len(citations),
                 confidence=confidence, ambiguous=ambiguous,
                 insufficient_context=insufficient_context, conversation_id=cid)

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
        }
        clean_tokens = [t for t in tokens if t not in stop_words]
        result = " ".join(clean_tokens) if clean_tokens else name
        result = result.strip().strip(" ?.!,:;-'\"").strip()
        return result

    async def _structured_retrieval(self, intent: QueryIntent, question: str,
                                    inferred_entity: str | None = None) -> list[SearchResult]:
        from retrieval.hybrid_search import SearchResult

        if intent == QueryIntent.TERM_DEFINITION:
            term_name = inferred_entity or self._extract_name(question, [
                "nghĩa là gì", "nghia la gi", "định nghĩa", "dinh nghia",
                "là gì", "la gi", "definition",
                "meaning", "define", "term",
            ])
            if not term_name:
                return []
            resolution = await self._entity_resolver.resolve(term_name, entity_type="glossary_term")
            return await self._resolve_to_results(resolution)

        if intent == QueryIntent.OWNER_LOOKUP:
            entity_name = inferred_entity or self._extract_name(question, [
                "ai sở hữu", "ai là", "ai la", "business owner",
                "owner", "của ai", "who owns", "who is the owner of",
            ])
            resolution = await self._entity_resolver.resolve(entity_name)
            return await self._resolve_to_results(resolution)

        if intent == QueryIntent.TERM_TO_DATASETS:
            term_name = inferred_entity or self._extract_name(question, [
                "dataset nào gắn term", "dataset nào có term",
                "find dataset", "entity nào gắn", "gắn term",
            ])
            if not term_name:
                return []
            resolution = await self._entity_resolver.resolve(term_name, entity_type="glossary_term")
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
                return results
            return []

        if intent == QueryIntent.LINEAGE:
            entity_name = inferred_entity or self._extract_name(question, [
                "lấy dữ liệu từ đâu", "upstream", "downstream",
                "nguồn", "phụ thuộc", "source of data",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, entity_type="dataset")
            if resolution.resolved:
                entity_db = await self._entity_repo.get_by_urn(resolution.resolved.urn)
                if entity_db and entity_db.payload:
                    upstreams = entity_db.payload.get("upstreams", [])
                    main_content = self._entity_payload_to_text(entity_db.entity_type, entity_db.payload)
                    results: list[SearchResult] = []

                    results.append(SearchResult(
                        urn=entity_db.urn, entity_type=entity_db.entity_type,
                        name=entity_db.display_name or entity_db.name,
                        score=1.0, datahub_url=entity_db.datahub_url,
                        payload={**entity_db.payload, "content": f"Entity: {main_content}\nUpstreams: {', '.join(upstreams) if upstreams else 'None'}"},
                    ))

                    for u in upstreams:
                        upstream_entity = await self._entity_repo.get_by_urn(u)
                        upstream_name = (upstream_entity.display_name or upstream_entity.name) if upstream_entity else u
                        upstream_content = self._entity_payload_to_text(
                            upstream_entity.entity_type if upstream_entity else "dataset",
                            upstream_entity.payload if upstream_entity else {},
                        ) if upstream_entity else u
                        results.append(SearchResult(
                            urn=u, entity_type=upstream_entity.entity_type if upstream_entity else "dataset",
                            name=upstream_name, score=0.8, datahub_url=upstream_entity.datahub_url if upstream_entity else None,
                            payload={"content": f"Upstream entity: {upstream_content}"},
                        ))
                    return results
            return []

        if intent == QueryIntent.SCHEMA_LOOKUP:
            entity_name = inferred_entity or self._extract_name(question, [
                "field", "schema", "cột", "trường", "có những",
                "columns", "fields",
            ])
            resolution = await self._entity_resolver.resolve(entity_name, entity_type="dataset")
            return await self._resolve_to_results(resolution)

        if intent == QueryIntent.DATAHUB_URL:
            entity_name = inferred_entity or self._extract_name(question, [
                "link", "url", "datahub", "đường dẫn",
            ])
            resolution = await self._entity_resolver.resolve(entity_name)
            return await self._resolve_to_results(resolution)

        if intent == QueryIntent.ENTITY_EXISTS:
            entity_name = inferred_entity or self._extract_name(question, [
                "có tồn tại", "tồn tại không", "exist",
                "có không", "does.*exist",
            ])
            resolution = await self._entity_resolver.resolve(entity_name)
            return await self._resolve_to_results(resolution)

        if intent == QueryIntent.CERTIFIED_LIST:
            entities = await self._entity_repo.list_certified()
            return self._entities_to_results(entities)

        if intent in (QueryIntent.DOMAIN_QUERY, QueryIntent.PLATFORM_QUERY,
                      QueryIntent.TAG_QUERY, QueryIntent.ENTITIES_BY_OWNER):
            value = inferred_entity or self._extract_filter_value(question, intent)
            if not value:
                return []
            if intent == QueryIntent.DOMAIN_QUERY:
                entities = await self._entity_repo.list_by_domain(value)
            elif intent == QueryIntent.PLATFORM_QUERY:
                entities = await self._entity_repo.list_by_platform(value)
            elif intent == QueryIntent.TAG_QUERY:
                entities = await self._entity_repo.list_by_tag(value)
            else:
                entities = await self._entity_repo.list_by_owner(value)
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

    async def _resolve_to_results(self, resolution: ResolutionResult) -> list[SearchResult]:
        from retrieval.hybrid_search import SearchResult
        if resolution.resolved:
            entity_db = await self._entity_repo.get_by_urn(resolution.resolved.urn)
            if entity_db:
                payload = entity_db.payload or {}
                content = self._entity_payload_to_text(entity_db.entity_type, payload)
                return [SearchResult(
                    urn=entity_db.urn, entity_type=entity_db.entity_type,
                    name=entity_db.display_name or entity_db.name,
                    score=1.0, datahub_url=entity_db.datahub_url,
                    payload={**payload, "content": content},
                )]
        return []

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
