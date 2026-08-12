import re
import uuid
from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.chat import (
    ChatResponse,
    CitationItem,
    EntityItem,
    LineageData,
    Suggestion,
)
from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import (
    _AMBIGUOUS_CLARIFY_INTENTS,
    _ANAPHORA_WORDS,
    _CHITCHAT_RESPONSES,
    _CONCEPT_PHRASE_RE,
    _CONCEPT_TO_DATASETS_RE,
    _DETERMINISTIC_LISTING_INTENTS,
    _GREETING_RESPONSES,
    _IMAGE_REF_RE,
    _QUALITY_FAVORED_INTENTS,
    _SYNC_RE,
    _TERM_REMOVE_WORDS,
    _build_access_denied_message,
    _detect_entity_type,
    _detect_listing,
    _extract_field_identifier,
    _extract_filter_value,
    _extract_name,
    _has_own_identifier,
    _is_contextual_followup,
    _is_datahub_relevant,
    _is_glossary_followup,
    _short_negative_answer,
    _trusted_resolution,
)
from app.services.image_context import ImageContext
from config.settings import settings
from guardrails.sanitizer import mask_secrets
from llm.generator import AnswerGenerator
from retrieval import classifier as intent_classifier
from retrieval.context_builder import build_context
from retrieval.context_resolver import resolve_context
from retrieval.datahub_intent import (
    DataHubRelevance,
    clarification_response,
    classify_datahub_relevance,
    refusal_response,
)
from retrieval.evidence import (
    FieldOp,
    extract_field_entity,
    parse_field_operation,
)
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent

log = structlog.get_logger()


class ChatService:
    """Chat orchestration service."""

    def __init__(
        self, session: AsyncSession,
        auth_service: AuthorizationService | None = None,
    ) -> None:
        from app.services.chat.access import DomainAccessService
        from app.services.chat.entity_resolution import EntityResolutionService
        from app.services.chat.evidence import EvidenceService
        from app.services.chat.flows import ChatFlowsService
        from app.services.chat.lineage import LineageService
        from app.services.chat.listing import ListingService
        from app.services.chat.structured_retrieval import StructuredRetrievalService
        from app.services.chat.vision import VisionContextService

        ctx = ChatContext(session, auth_service=auth_service)
        self._ctx = ctx
        ctx.entities = EntityResolutionService(ctx)
        ctx.retrieval = StructuredRetrievalService(ctx)
        ctx.evidence = EvidenceService(ctx)
        ctx.listing = ListingService(ctx)
        ctx.lineage = LineageService(ctx)
        ctx.flows = ChatFlowsService(ctx)
        ctx.access = DomainAccessService(ctx)
        ctx.vision = VisionContextService(ctx)
        self._entities = ctx.entities
        self._retrieval = ctx.retrieval
        self._evidence = ctx.evidence
        self._listing = ctx.listing
        self._lineage = ctx.lineage
        self._flows = ctx.flows
        self._access = ctx.access
        self._vision_svc = ctx.vision
        self._source = ctx.source
        self._vision = ctx.vision_skill
        self._conv_context = ctx.conv_context
        self._last_denied_names: list[str] = []


    def _upload_service(self):
        from app.services.image_upload import ImageUploadService

        return ImageUploadService(
            self._ctx.session, vision_service=self._ctx.conversation_vision,
        )


    async def answer(self, question: str, user: UserContext | None = None,
                     conversation_id: str | None = None,
                     suggested_name: str | None = None,
                     model: str | None = None,
                     selected_action: str | None = None,
                     images: list[str] | None = None,
                     on_status: Callable[[str], Awaitable[None]] | None = None,
                     on_token: Callable[[str], Awaitable[None]] | None = None) -> ChatResponse:
        trace_id = uuid.uuid4().hex[:12]
        cid = conversation_id or trace_id

        # Model selection: a per-request model id swaps in a dedicated generator
        # (e.g. NVIDIA NVCF) without disturbing the default Fireworks pipeline.
        generator = self._ctx.generator
        if model and model.strip():
            try:
                generator = AnswerGenerator(provider=model.strip())
            except Exception:  # noqa: BLE001
                log.warning(
                    "chat_model_override_failed",
                    trace_id=trace_id,
                    model=model[:80],
                )
                generator = self._ctx.generator

        async def _emit(step: str) -> None:
            if on_status:
                await on_status(step)

        await _emit("classify")

        user_ctx = user or UserContext(user_id="anonymous", is_admin=False)
        uid = user_ctx.user_id

        # Conversation context for intent resolution (anaphora, follow-up turns).
        history = await self._ctx.memory.load_history_from_db(self._ctx.session, uid, cid)
        # Canonical entities this conversation last talked about (for coreference).
        active_entities = self._ctx.memory.get_active_entities(uid, cid)

        # Semantic intent resolution: merge the raw user message with the selected
        # "+" menu action (a hint, never an order) and the conversation context to
        # decide the ACTUAL task. The action only wins when it agrees with the
        # message; explicit user wording overrides a conflicting action; ambiguous
        # combinations ask for clarification instead of blindly executing the action.
        resolution = await self._ctx.intent_resolver.resolve(
            question, selected_action=selected_action, history=history, trace_id=trace_id,
        )
        intent = resolution.intent
        plan = resolution.plan

        # Concept-to-dataset questions ("Có tồn tại dataset nào liên quan đến khái
        # niệm doanh thu?") semantically ask which datasets carry a business concept.
        # Reroute away from generic FIND_ENTITY / ENTITY_EXISTS / GENERAL - and AWAY
        # from the resolver's ambiguous-entity clarification - so the term->datasets
        # flow answers deterministically. This must run BEFORE the clarify early
        # return below.
        concept_phrase: str | None = None
        if (intent in (QueryIntent.FIND_ENTITY, QueryIntent.ENTITY_EXISTS,
                       QueryIntent.GENERAL, QueryIntent.SCHEMA_LOOKUP)
                and _CONCEPT_TO_DATASETS_RE.search(question)):
            _cm = _CONCEPT_PHRASE_RE.search(question)
            if _cm:
                concept_phrase = next(
                    (g for g in (_cm.group(1), _cm.group(2), _cm.group(3)) if g), None
                )
                concept_phrase = concept_phrase.strip() if concept_phrase else None
            if plan:
                plan.intent = QueryIntent.TERM_TO_DATASETS
            intent = QueryIntent.TERM_TO_DATASETS
            decision = "proceed"
            log.info("route_concept_to_datasets", trace_id=trace_id,
                     question=question[:100], concept=concept_phrase)
        else:
            decision = resolution.decision

        log.info(
            "intent_resolution",
            trace_id=trace_id,
            selected_action=resolution.selected_action,
            message_intent=resolution.message_intent.value,
            detected_intent=intent.value,
            routing_decision=resolution.decision,
            confidence=resolution.confidence,
            chosen_tool=resolution.chosen_tool,
            override_reason=resolution.override_reason,
            entity_hint=resolution.entity_hint,
            plan_source=(plan.source if plan else None),
            conversation_id=cid,
            question=question[:120],
        )

        if decision == "clarify":
            answer_text = resolution.clarification or (
                "Xin lỗi, tôi chưa rõ bạn muốn làm gì. Bạn có thể làm rõ thêm yêu cầu được không?"
            )
            log.info("route_clarify", trace_id=trace_id, intent=intent.value,
                     selected_action=selected_action, answer=answer_text[:120])
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="low",
                ambiguous=True, insufficient_context=True,
                trace_id=trace_id, conversation_id=cid,
            )

        # Retrieval / generation runs on the effective question: the raw message,
        # or the action-framed question when the action supplies the missing context.
        query = resolution.effective_question or question
        entity_hint = suggested_name or resolution.entity_hint
        if concept_phrase:
            entity_hint = concept_phrase

        log.info("chat_request", trace_id=trace_id, intent=intent.value,
                 question=question[:100], conversation_id=cid)

        if intent == QueryIntent.GREETING:
            import random
            answer_text = random.choice(_GREETING_RESPONSES)
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid,
            )

        if intent == QueryIntent.CHITCHAT:
            cleaned = question.lower().strip().rstrip("?!.")
            answer_text = _CHITCHAT_RESPONSES.get(
                cleaned, "Tôi là trợ lý DataHub, sẵn sàng giúp bạn!",
            )
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid,
            )

        # Guardrails: scope restriction (#5) and prompt injection in user input (#16).
        out_of_scope = self._ctx.guardrails.enforce_scope(question)
        if out_of_scope:
            log.info("chat_out_of_scope", trace_id=trace_id, question=question[:100])
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, out_of_scope)
            return ChatResponse(answer=out_of_scope, intent=intent.value, confidence="high",
                                insufficient_context=False, trace_id=trace_id, conversation_id=cid)

        injection_message = self._ctx.guardrails.check_prompt_injection(question)
        if injection_message:
            log.info("chat_injection_blocked", trace_id=trace_id, question=question[:100])
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question, injection_message,
            )
            return ChatResponse(answer=injection_message, intent=intent.value, confidence="high",
                                insufficient_context=False, trace_id=trace_id, conversation_id=cid)

        recommendation = self._ctx.guardrails.is_recommendation(question)
        if recommendation:
            log.info("chat_recommendation", trace_id=trace_id, question=question[:100])

        # Domain RBAC gate: before ANY listing / count / GraphQL / metadata /
        # vector / RAG / semantic / aggregation / LLM call, deny access when the
        # question explicitly targets a domain the user's roles cannot see.
        if self._ctx.auth_service:
            denied = await self._access.gate_domain_access(
                query, user_ctx, entity_hint=entity_hint, history=history,
            )
            if denied:
                log.info("chat_domain_blocked", trace_id=trace_id, question=question[:100])
                await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, denied)
                return ChatResponse(
                    answer=denied, intent=intent.value, confidence="high",
                    ambiguous=False, insufficient_context=False,
                    trace_id=trace_id, conversation_id=cid,
                )

        # AI intent gate: before ANY retrieval/search/GraphQL/RAG runs, ask the
        # LLM whether this question is about DataHub metadata. Non-DataHub
        # questions get a polite refusal; ambiguous ones ask for clarification.
        # The gate evaluates the *effective* question (the selected action frames
        # a bare entity into a full DataHub request), so action-driven flows are
        # not misclassified as non-DataHub just because the message is short.
        relevance = await classify_datahub_relevance(self._ctx.llm, query)
        # Deterministic rescue: even when the LLM gate hesitates or refuses, a
        # question that clearly uses DataHub vocabulary (or names a catalog
        # entity) is in scope. The keyword heuristic is trusted for UNCERTAIN
        # below anyway; hoisting it here prevents flaky NON_DATAHUB refusals of
        # glossary / schema questions like "Term 3-Way Matching là gì?".
        if relevance != DataHubRelevance.DATAHUB and _is_datahub_relevant(query):
            log.info("route_ai_keyword_rescued", trace_id=trace_id, question=query[:100])
            relevance = DataHubRelevance.DATAHUB
        if relevance == DataHubRelevance.NON_DATAHUB:
            log.info("route_ai_non_datahub", trace_id=trace_id, question=query[:100])
            await _emit("generate")
            answer_text = refusal_response(query)
            if on_token:
                await on_token(answer_text)
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, query, answer_text)
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
            if _is_datahub_relevant(query):
                log.info("route_ai_uncertain_rescued",
                         trace_id=trace_id, question=query[:100])
                relevance = DataHubRelevance.DATAHUB
            else:
                log.info("route_ai_uncertain", trace_id=trace_id, question=query[:100])
                answer_text = clarification_response(query)
                await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, query, answer_text)
                return ChatResponse(
                    answer=answer_text, intent=intent.value, confidence="low",
                    ambiguous=True, insufficient_context=True,
                    trace_id=trace_id, conversation_id=cid,
                )

        # Visual Understanding + Image Context gate: image attachments are
        # persisted (Image Storage), analysed (Vision Service, cache-aware) and
        # the extracted Image Context is bound to the conversation so follow-up
        # turns never need a re-upload.
        #
        # IMAGE IS CONTEXT, NOT INTENT. The image-derived dataset is bound as the
        # conversation's active entity (and entity hint) so the REAL function
        # flows — SQL, quality, impact, lineage, schema, owner, domain,
        # glossary… — execute against it, at their normal priority
        # (selected action > natural-language intent > conversation context >
        # image-derived context > generic metadata). The image answers directly
        # ONLY for questions that are purely about the image's own contents
        # ("ảnh này là gì", "dataset trong ảnh tên gì?"); anything that maps to
        # a DataHub function falls through and the normal routing runs it.
        if settings.VISION_ENABLED and (images or self._conv_context):
            await _emit("retrieve")
            contexts: list[ImageContext] = []
            if images:
                # Persist + analyze new uploads and bind them to the conversation.
                contexts = await self._conv_context.ingest(
                    uid, cid, list(images), image_text_hint=query,
                    vision_skill=self._vision,
                )
            if not contexts:
                # Restore previously-stored Image Contexts for this conversation.
                contexts = await self._conv_context.load(uid, cid)

            if contexts:
                active, needs_more = self._conv_context.resolve_active(
                    query, uid, cid, contexts,
                )
                if images and active is None and len(contexts) >= 2 and not needs_more:
                    active = contexts[0]
                vision_payload = active.to_dict() if active else None
                if active is not None:
                    image_ref = _IMAGE_REF_RE.search(query) is not None
                    # A listing request ("có những document nào trong hệ thống?",
                    # "có những datasets nào?") is an INDEPENDENT new intent: it
                    # must never be answered from or bound to the image-derived
                    # entity. The image stays only as the anaphora subject for
                    # future direct follow-ups ("lineage của nó?").
                    listing_type = _detect_listing(query)
                    if not active.irrelevant:
                        # Bind the image-derived dataset as the entity for this
                        # turn: the real function flows resolve it from here. The
                        # image entity becomes the hint when the question explicitly
                        # refers back to the image ("nó", "ảnh này") OR when it
                        # carries no catalog entity of its own (capability-ellipsis
                        # like "có những trường nào?"). A self-contained question
                        # naming a catalog entity of its own ("dim_warehouse có
                        # lineage gì?") keeps that entity — the image-derived
                        # context stays BELOW explicit natural-language intent.
                        image_entity, image_urn = await self._vision_svc.image_entity_identity(
                            active,
                        )
                        if image_entity:
                            self._ctx.memory.set_image_focus(uid, cid, image_entity, image_urn)
                        names_own_entity = _has_own_identifier(query)
                        if (image_entity and not listing_type and
                                (image_ref or (not names_own_entity and not entity_hint))):
                            entity_hint = image_entity
                        if image_entity and not listing_type:
                            await self._evidence.record_active_entities(uid, cid, [], extra=[{
                                "name": image_entity,
                                "entity_type": "dataset",
                                "urn": image_urn,
                            }])
                            await self._evidence.record_image_evidence(
                                uid, cid, query, image_entity, image_urn,
                            )
                            if not any(
                                a.get("name") == image_entity for a in active_entities
                            ):
                                active_entities.append({
                                    "name": image_entity,
                                    "entity_type": "dataset",
                                    "urn": image_urn,
                                })
                    # Answer directly only when the question is about the image's
                    # own contents (and the user is not listing a different type);
                    # otherwise fall through to the normal pipeline so the
                    # matching DataHub function runs against the image entity
                    # (which is now bound above as entity_hint / active).
                    if image_ref and not listing_type:
                        answer_text, vision_conf, vision_handled = \
                            await self._vision_svc.answer_from_image_context(
                                active, query, history,
                            )
                    else:
                        answer_text, vision_conf, vision_handled = None, "low", False
                    if vision_handled:
                        intent_label = "VISION_REFUSED" if active.irrelevant else "VISION_ANALYSIS"
                        log.info("route_vision_context", trace_id=trace_id,
                                 image_id=active.image_id, question=query[:100])
                        await self._ctx.memory.add_turn_db(
                            self._ctx.session, uid, cid, query, answer_text,
                        )
                        await _emit("generate")
                        if on_token:
                            await on_token(answer_text)
                        await _emit("done")
                        return ChatResponse(
                            answer=answer_text, intent=intent_label,
                            confidence=vision_conf, ambiguous=False,
                            insufficient_context=False,
                            trace_id=trace_id, conversation_id=cid,
                            vision=vision_payload,
                        )
                elif needs_more:
                    answer_text = (
                        "Tôi thấy bạn đã gửi nhiều ảnh. Bạn muốn hỏi về ảnh nào: "
                        + ", ".join(f"“{c.file_name}”" for c in contexts[:3])
                        + "?"
                    )
                    await self._ctx.memory.add_turn_db(
                        self._ctx.session, uid, cid, query, answer_text,
                    )
                    await _emit("generate")
                    if on_token:
                        await on_token(answer_text)
                    await _emit("done")
                    return ChatResponse(
                        answer=answer_text, intent="VISION_CLARIFY",
                        confidence="low", ambiguous=False,
                        insufficient_context=False,
                        trace_id=trace_id, conversation_id=cid,
                    )

        # Evidence-context gate: follow-up questions that reference metadata the
        # conversation already collected ("schema vừa lấy", "field đó", "kết quả
        # vừa rồi", "toàn bộ kết quả vừa rồi", "chỉ dựa trên metadata vừa lấy",
        # image-derived datasets...) are answered STRICTLY from the conversation's
        # evidence store (E1, E2, ...) — grounded in exactly what was fetched,
        # never a fresh silent cross-catalog semantic re-search. This runs AFTER
        # the vision gate (which may inject image-derived evidence) and BEFORE the
        # Thinking layer, so context-referencing follow-ups are never swallowed by
        # an independent re-search plan. Questions that carry their own entity and
        # no evidence reference (Test F style) fall through untouched.
        _evidence_resolution = resolve_context(
            query,
            self._ctx.memory.get_evidence(uid, cid),
            active_entities,
        )
        if _evidence_resolution.is_followup:
            _evidence_response = await self._evidence.answer_from_evidence(
                uid, cid, query, _evidence_resolution, trace_id,
            )
            if _evidence_response is not None:
                log.info("route_evidence_context", trace_id=trace_id,
                         question=query[:100],
                         evidence=_evidence_resolution.referenced_evidence_ids,
                         intent=_evidence_response.intent)
                await _emit("generate")
                if on_token:
                    await on_token(_evidence_response.answer)
                await _emit("done")
                return _evidence_response

        # Field-property gate: a self-contained field question that names its own
        # entity and field ("warehouse_id của fact_inventory_movement có kiểu dữ
        # liệu gì?") answers directly from the resolved dataset's schema metadata.
        # Runs after the evidence gate (evidence takes precedence for follow-ups)
        # and before the Thinking layer so it never falls into a re-search plan.
        _field_property_response = await self._answer_direct_field_op(
            query, uid, cid, trace_id,
        )
        if _field_property_response is not None:
            log.info("route_field_property", trace_id=trace_id,
                     question=query[:100],
                     intent=_field_property_response.intent)
            await _emit("generate")
            if on_token:
                await on_token(_field_property_response.answer)
            await _emit("done")
            return _field_property_response

        # Thinking Mode gate: for complex / system-level / multi-hop questions that
        # fall through to the generic (GENERAL) intent, run the independent
        # planning + multi-source reasoning layer and return its structured,
        # evidence-tracked answer. Questions with a dedicated existing handler
        # (IMPACT, TERM_TO_DATASETS, SQL, QUALITY, lineage, listing...) keep
        # their specialised flow untouched. Simple GENERAL questions score below
        # the complexity threshold and also fall through unchanged.
        # Anaphoric / ellipsis follow-ups ("nó", "đó", "bảng này", "cái trên",
        # "con ...") must NOT be swallowed by the thinking layer: their entity
        # lives in the conversation context, so they need the coreference-aware
        # routing below, never an independent plan that re-searches from scratch.
        _ctx_followup = bool(
            _is_contextual_followup(query) and (history or active_entities)
        )
        if settings.THINKING_MODE_ENABLED and intent == QueryIntent.GENERAL \
                and not _ctx_followup:
            _complex = False
            try:
                _complex = await self._ctx.thinking.is_complex(
                    query, entity_mentions=(
                        [entity_hint] if entity_hint else None
                    ), history=history,
                )
            except Exception:  # noqa: BLE001
                log.exception("thinking_complexity_failed", trace_id=trace_id,
                              question=query[:100])
            if _complex:
                await _emit("thinking")
            try:
                thinking_answer = await self._ctx.thinking.maybe_answer(
                    query, entity_mentions=(
                        [entity_hint] if entity_hint else None
                    ), history=history,
                )
            except Exception:  # noqa: BLE001
                log.exception("thinking_mode_failed", trace_id=trace_id,
                              question=query[:100])
                thinking_answer = None
            if thinking_answer:
                log.info("route_thinking_mode", trace_id=trace_id,
                         question=query[:100], intent=intent.value)
                answer_text = mask_secrets(thinking_answer)
                await self._evidence.record_overview_evidence(
                    uid, cid, query, answer_text,
                    entity_hint=entity_hint,
                )
                await self._ctx.memory.add_turn_db(
                    self._ctx.session, uid, cid, query, answer_text,
                )
                if _complex:
                    await _emit("thinking_done")
                await _emit("generate")
                if on_token:
                    await on_token(answer_text)
                await _emit("done")
                return ChatResponse(
                    answer=answer_text, intent="THINKING_OVERVIEW",
                    confidence="high", ambiguous=False,
                    insufficient_context=False,
                    trace_id=trace_id, conversation_id=cid,
                )

        # SQL Generation: when the intent resolver picked the sql_generator tool
        # (explicit "Generate SQL" action, or a field/query request like
        # "truy vấn ... warehouse_id"), run the field-aware SQL pipeline instead
        # of generic entity search. An explicitly selected action always wins.
        if resolution.chosen_tool == "sql_generator" or intent == QueryIntent.SQL_GENERATION:
            sql_response = await self._flows.sql_generation_flow(
                query, user_ctx, trace_id, cid, entity_hint,
            )
            if sql_response is not None:
                await _emit("done")
                return sql_response

        # Field synchronisation / data-mapping: "warehouse_id được sync với gì?"
        # asks WHERE a column is shared across tables (the join keys). Answer
        # deterministically from the schema instead of running a free-form topic
        # overview or a conversational reply.
        if _SYNC_RE.search(query) and intent in (
            QueryIntent.GENERAL, QueryIntent.TERM_DEFINITION,
            QueryIntent.SCHEMA_LOOKUP, QueryIntent.LINEAGE,
        ):
            sync_response = await self._flows.sync_relation_flow(
                query, user_ctx, trace_id, cid,
            )
            if sync_response is not None:
                await _emit("done")
                return sync_response

        # Data Quality Check: an explicit "quality" action, or a framed dataset
        # quality request, runs the deterministic quality report against DataHub
        # metadata and returns it as a rendered markdown answer plus the structured
        # report (carried on ChatResponse.quality_report) for the chat export UI.
        if resolution.chosen_tool == "quality_check" or (
            selected_action == "quality" and intent in _QUALITY_FAVORED_INTENTS
        ):
            quality_response = await self._flows.quality_check_flow(
                query, user_ctx, trace_id, cid, entity_hint,
            )
            if quality_response is not None:
                await _emit("done")
                return quality_response

        # GENERAL intent with no DataHub relevance (trivia, non-business questions)
        # is answered conversationally without retrieval, so no spurious citations.
        # Action-framed GENERAL intents (quality / report) keep the retrieval path.
        if (intent == QueryIntent.GENERAL and not resolution.framed
                and not _is_datahub_relevant(query)):
            log.info("route_general_conversational", trace_id=trace_id, question=query[:100])
            await _emit("generate")
            answer_text = await generator.generate_conversational(query, on_token=on_token)
            if not answer_text:
                answer_text = (
                    "Xin lỗi, tôi chưa hiểu câu hỏi này. Bạn có thể hỏi về dataset, "
                    "glossary term, owner, lineage hoặc SQL."
                )
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="medium",
                ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        listing_type = _detect_listing(query)
        if listing_type:
            entity_type_label = (
                "glossary terms" if listing_type == "glossary_term"
                else f"{listing_type}s"
            )
            count = await self._ctx.entity_repo.count_by_type(listing_type)
            log.info("route_listing", trace_id=trace_id, question=question[:100],
                     listing_type=listing_type, db_count=count, source="deterministic_db")
            entities = await self._ctx.entity_repo.list_by_type(listing_type, limit=200)
            if self._ctx.auth_service:
                entities = await self._ctx.auth_service.filter_entities_by_domain(
                    user_ctx, entities
                )
                accessible = await self._ctx.auth_service.filter_accessible_urns(
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
                lines.append(
                f"\n{plat}: {', '.join(sample[:15])}"
                f"{', ...' if len(sample) > 15 else ''}"
            )
            answer_text = mask_secrets("\n".join(lines))

            entity_list = []
            for e in entities:
                entity_list.append(
                EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url)
            )
                if len(entity_list) >= 50:
                    break

            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, query, answer_text)
            return ChatResponse(
                answer=answer_text, intent="LISTING", entities=entity_list,
                confidence="high", ambiguous=False,
                insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        if intent in _DETERMINISTIC_LISTING_INTENTS:
            response = await self._listing.deterministic_listing(
                query, intent, user_ctx, trace_id, cid,
                suggested_name=entity_hint,
            )
            if response is not None:
                await self._ctx.memory.add_turn_db(
                    self._ctx.session, uid, cid, query, response.answer,
                )
                return response

        # Semantic plan: used to detect recursive-impact / composite questions
        # that the keyword router would otherwise miscast as LINEAGE/GENERAL.
        # The intent resolver already produced a plan (locked when it was rebuilt
        # from a selected action). Cheap regex plan by default; the LLM upgrades
        # only ambiguous cases.
        if plan is None:
            plan = intent_classifier.regex_plan(query)
        if (not resolution.framed
                and intent_classifier.needs_semantic(query, intent.value)
                and settings.INTENT_CLASSIFIER_ENABLED
                and not settings.USE_MOCK_LLM):
            plan = await intent_classifier.classify(query, self._ctx.llm)
        impact_mode = plan.intent == "IMPACT"

        # Query-planner path: plans with explicit executable steps (composite /
        # LLM-planned multi-step questions) go through the DAG tool orchestrator
        # (parallel branches + retries). Single-intent plans keep the direct
        # structured path below for lower latency.
        import time
        _t0 = time.perf_counter()
        planner_results: list[SearchResult] = []
        if (settings.QUERY_PLANNER_ENABLED
                and (plan.steps or plan.intent in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY"))):
            planner_results = await self._ctx.planner.execute(plan)
            log.info("route_planner_dag", trace_id=trace_id, question=query[:100],
                     intent=plan.intent, steps=len(plan.steps),
                     result_count=len(planner_results))

        if planner_results:
            results = planner_results
            impact_mode = False
            await _emit("retrieve")
        else:
            await _emit("retrieve")

            _t0 = time.perf_counter()
            import unicodedata
            q_norm = (
                unicodedata.normalize("NFKD", query.lower())
                .encode("ascii", "ignore").decode("ascii")
            )

            anaphora = {"đó", "nó", "ấy", "này", "đây", "kia"}
            anaphora_ascii = {"do", "no", "ay", "nay", "day", "kia"}
            has_anaphora = bool(
                re.search(r"\b(?:{})\b".format("|".join(anaphora)), query.lower())
                or re.search(
                    r"\b(?:{})\b".format("|".join(anaphora_ascii)), q_norm,
                )
            ) and not _has_own_identifier(query)
            is_ellipsis = q_norm.startswith(("con ", "the ", "the con"))
            # Broad contextual detection: catches anaphora, demonstratives and
            # capability-ellipsis ("có các trường nào?", "bảng này thuộc về ai?")
            # that rely on the conversation's active entity, while leaving
            # self-contained questions ("dim_warehouse có những trường nào?") out.
            is_ctx_followup = _is_contextual_followup(query)
            has_ctx = has_anaphora or is_ellipsis or is_ctx_followup

            if impact_mode and not has_ctx:
                results = await self._retrieval.recursive_impact_retrieval(
                    plan, query, entity_hint, trace_id
                )
                log.info("route_impact", trace_id=trace_id, question=query[:100],
                         result_count=len(results), entity=plan.primary_entity)
            elif has_ctx and len(history) > 0:
                if is_ellipsis:
                    m = re.search(r'^(?:the\s+con\s+|con\s+|the\s+)(.+?)\??\s*$', q_norm)
                    entity_from_q = m.group(1).strip() if m else ""
                    # Strip ellipsis/interrogative noise ("thi sao", "thì sao",
                    # "thế nào", "vậy") so "Còn fact_goods_receipt thì sao?" keeps
                    # a clean entity name for exact resolution.
                    entity_from_q = re.sub(
                        r"\s+(?:thi|thì)?\s*(?:sao|thế\s+nào|the\s+nao|"
                        r"là\s+gì|la\s+gi|vậy|vay)\s*$",
                        "", entity_from_q,
                    ).strip()
                    inferred_entity = entity_from_q if entity_from_q else None
                    inferred_type: str | None = None
                else:
                    inferred_entity, inferred_type = await self._entities.resolve_followup_entity(
                        uid, cid, query, history, active_entities,
                    )
                log.info("route_anaphora", trace_id=trace_id, question=query[:100],
                         has_anaphora=has_anaphora, is_ellipsis=is_ellipsis,
                         inferred_entity=inferred_entity, inferred_type=inferred_type,
                         history_len=len(history))
                if inferred_entity:
                    # Follow-up "có dataset nào liên quan đến nó?" when "nó" is a
                    # glossary term -> the user wants term->datasets, not an owner.
                    if (inferred_type == "glossary_term"
                            and re.search(
                                r"(dataset|bảng|bang|table)[^?]{0,30}?"
                                r"(liên quan|lien quan|chứa|chua|gắn|gan|mapping)",
                                query, re.I,
                            )):
                        intent = QueryIntent.TERM_TO_DATASETS
                        term_datasets_response = await self._flows.term_datasets_flow(
                            uid, cid, inferred_entity, trace_id, question=query,
                        )
                        if term_datasets_response is not None:
                            await self._ctx.memory.add_turn_db(
                                self._ctx.session, uid, cid, query,
                                term_datasets_response.answer,
                            )
                            await _emit("generate")
                            if on_token:
                                await on_token(term_datasets_response.answer)
                            await _emit("done")
                            return term_datasets_response
                    # Glossary-term follow-up about the conversation's active
                    # (dataset) entity -> answer from the dataset's bound terms
                    # rather than letting the keyword router guess an intent.
                    if _is_glossary_followup(query):
                        glossary_response = await self._flows.dataset_terms_flow(
                            uid, cid, inferred_entity, inferred_type, trace_id,
                            question=query,
                        )
                        if glossary_response is not None:
                            await self._ctx.memory.add_turn_db(
                                self._ctx.session, uid, cid, query, glossary_response.answer,
                            )
                            await _emit("generate")
                            if on_token:
                                await on_token(glossary_response.answer)
                            await _emit("done")
                            return glossary_response
                    if intent in (QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
                                  QueryIntent.ENTITY_DOMAIN,
                                  QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
                                  QueryIntent.SCHEMA_LOOKUP, QueryIntent.DATAHUB_URL,
                                  QueryIntent.ENTITY_EXISTS, QueryIntent.DOMAIN_QUERY,
                                  QueryIntent.PLATFORM_QUERY, QueryIntent.TAG_QUERY,
                                  QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST):
                        results = await self._retrieval.structured_retrieval(
                            intent, query, inferred_entity=inferred_entity,
                            inferred_type=inferred_type, trace_id=trace_id,
                        )
                    elif impact_mode:
                        # Anaphoric implicit impact: "xóa nó thì sao?" — the entity
                        # comes from the conversation context, and the impact tool
                        # must run against it (not the raw question, which carries
                        # no entity of its own).
                        from retrieval.query_models import QueryPlan
                        impact_plan = QueryPlan(
                            intent="IMPACT", entity_refs=[inferred_entity],
                            entity_type="dataset", direction="downstream",
                            confidence="high", source="coreference",
                        )
                        results = await self._retrieval.recursive_impact_retrieval(
                            impact_plan, query, inferred_entity, trace_id
                        )
                        intent = QueryIntent.IMPACT
                        log.info("route_impact_anaphora", trace_id=trace_id,
                                 question=query[:100], entity=inferred_entity,
                                 result_count=len(results))
                    else:
                        # "Còn X thì sao?" / bare-entity ellipsis: inherit the
                        # previous turn's tool so the new entity is re-retrieved
                        # the same way ("thì sao" after a schema fetch -> schema).
                        _tool_to_intent = {
                            "schema_lookup": QueryIntent.SCHEMA_LOOKUP,
                            "owner_lookup": QueryIntent.OWNER_LOOKUP,
                            "lineage": QueryIntent.LINEAGE,
                            "impact": QueryIntent.IMPACT,
                            "domain_lookup": QueryIntent.ENTITY_DOMAIN,
                            "term_definition": QueryIntent.TERM_DEFINITION,
                            "sql_generator": QueryIntent.SQL_GENERATION,
                        }
                        _last_ev = (
                            self._ctx.memory.get_evidence(uid, cid) or [{}]
                        )[-1]
                        preferred = _tool_to_intent.get(
                            _last_ev.get("tool_name") or ""
                        )
                        results = []
                        try_intents = [
                            preferred,
                            QueryIntent.OWNER_LOOKUP, QueryIntent.ENTITY_DOMAIN,
                            QueryIntent.SCHEMA_LOOKUP,
                            QueryIntent.LINEAGE, QueryIntent.TERM_DEFINITION,
                            QueryIntent.TERM_TO_DATASETS, QueryIntent.DATAHUB_URL,
                            QueryIntent.ENTITY_EXISTS,
                        ]
                        for try_intent in try_intents:
                            if try_intent is None:
                                continue
                            results = await self._retrieval.structured_retrieval(
                                try_intent, query, inferred_entity=inferred_entity,
                                inferred_type=inferred_type, trace_id=trace_id,
                            )
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
                results = await self._retrieval.structured_retrieval(
                    intent, query, inferred_entity=entity_hint
                )
                log.info("route_structured", trace_id=trace_id, question=query[:100],
                         intent=intent.value, result_count=len(results))
            else:
                # Exact-name fast path: when the question names a catalog
                # entity itself ("Dataset dim_warehouse lưu trữ thông tin gì?",
                # "Lấy thông tin fact_inventory_movement",
                # "Có mấy dataset tên fact_inventory_movement?") resolve it
                # deterministically instead of letting fuzzy hybrid search rank
                # unrelated candidates above the very entity the user typed
                # (which then triggers a wrong clarification). This lookup is a
                # pure entity resolution that runs INDEPENDENTLY of the intent
                # the keyword router assigned — any question that names an exact
                # catalog entity is grounded on that entity before any re-search.
                results = await self._entities.try_explicit_entity_lookup(
                    query, user_ctx, trace_id)
                if results:
                    log.info("route_explicit_entity", trace_id=trace_id,
                             question=query[:100],
                             hit=results[0].name)
                    # Deterministic count answer: "Có mấy dataset tên X?" asks
                    # for the number of catalog entries matching that exact
                    # name. The explicit lookup IS the exact-name count — if it
                    # resolved exactly one entity, that is the answer.
                    if intent == QueryIntent.COUNT_ENTITIES:
                        await self._ctx.memory.add_turn_db(
                            self._ctx.session, uid, cid, query,
                            f"Có {len(results)} dataset tên chính xác "
                            f"'{results[0].name}' trong hệ thống.",
                        )
                        log.info("route_explicit_count", trace_id=trace_id,
                                 question=query[:100],
                                 hit=results[0].name, count=len(results))
                        await self._evidence.record_active_entities(
                            uid, cid, results, question=query)
                        await _emit("generate")
                        await _emit("done")
                        return ChatResponse(
                            answer=f"Có {len(results)} dataset tên chính xác "
                                   f"'{results[0].name}' trong hệ thống.",
                            intent="COUNT_ENTITIES", confidence="high",
                            ambiguous=False, insufficient_context=False,
                            trace_id=trace_id, conversation_id=cid,
                        )
                else:
                    results = await self._ctx.hybrid_search.search(query, trace_id=trace_id)
                log.info("route_hybrid", trace_id=trace_id, question=query[:100],
                         intent=intent.value, result_count=len(results))

        # Remember the entities this turn resolved so follow-ups ("nó", "đó")
        # can be answered from canonical names instead of raw text tokens.
        await self._evidence.record_active_entities(uid, cid, results, question=query)
        # Record the structured metadata this turn produced (schema fields,
        # owners, lineage, glossary, domain...) as evidence (E1, E2, ...) so
        # evidence-referencing follow-ups are answered from it without re-search.
        await self._evidence.record_evidence_from_results(uid, cid, query, intent, results)


        suggestion: Suggestion | None = None
        if (not results) and suggested_name is None:
            if intent == QueryIntent.TERM_DEFINITION:
                extracted = _extract_name(query, _TERM_REMOVE_WORDS)
                if not extracted:
                    _am = re.search(r"\b[A-Z]{2,8}(?:-[A-Z]+)*\b", question)
                    if _am:
                        extracted = _am.group(0)
                suggestion = await self._entities.suggest_entity(
                    extracted, "glossary_term", query, trace_id
                )
                if extracted:
                    # Deterministic term-not-found: name the term so follow-up
                    # troubleshooting is possible instead of an LLM "no info".
                    term_not_found = (
                        f"Term '{extracted}' hiện chưa có trong danh mục glossary "
                        f"của DataHub."
                    )
                    if suggestion is not None:
                        term_not_found += f" Ý bạn là '{suggestion.suggested}'?"
                    await self._ctx.memory.add_turn_db(
                        self._ctx.session, uid, cid, query, term_not_found)
                    log.info("chat_term_not_found", trace_id=trace_id,
                             intent=intent.value, original=extracted,
                             suggested=suggestion.suggested if suggestion else None,
                             conversation_id=cid)
                    return ChatResponse(
                        answer=term_not_found, intent=intent.value, confidence="high",
                        ambiguous=False, insufficient_context=False,
                        trace_id=trace_id, conversation_id=cid,
                    )
            elif intent == QueryIntent.DOMAIN_QUERY:
                value = _extract_filter_value(query, QueryIntent.DOMAIN_QUERY)
                if value and value not in _ANAPHORA_WORDS:
                    suggestion = await self._entities.suggest_entity(value, None, query, trace_id)
            elif intent in (QueryIntent.LINEAGE, QueryIntent.OWNER_LOOKUP,
                            QueryIntent.ENTITY_DOMAIN, QueryIntent.SCHEMA_LOOKUP,
                            QueryIntent.TERM_TO_DATASETS, QueryIntent.ENTITY_EXISTS):
                # A picked function (Data Lineage, quality, …) with no matching
                # entity -> friendly, grounded "not found" answer instead of a
                # generic LLM guess.
                extracted = _extract_name(query, _TERM_REMOVE_WORDS)
                if extracted and extracted not in _ANAPHORA_WORDS:
                    suggestion = await self._entities.suggest_entity(
                        extracted,
                        "dataset" if intent != QueryIntent.TERM_TO_DATASETS else None,
                        query, trace_id,
                    )
                    not_found = (
                        f"Không tìm thấy dataset '{extracted}' trong hệ thống DataHub."
                    )
                    if suggestion is not None:
                        not_found += (
                            f" Ý bạn là '{suggestion.suggested}'?"
                        )
                    await self._ctx.memory.add_turn_db(
                        self._ctx.session, uid, cid, query, not_found,
                    )
                    log.info("chat_not_found", trace_id=trace_id, intent=intent.value,
                             original=extracted,
                             suggested=suggestion.suggested if suggestion else None,
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
                await self._ctx.memory.add_turn_db(
                    self._ctx.session, uid, cid, question, answer_text,
                )
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
        question_for_gen = query
        if suggested_name and intent == QueryIntent.TERM_DEFINITION:
            extracted = _extract_name(query, _TERM_REMOVE_WORDS)
            if extracted and extracted.lower() not in suggested_name.lower():
                question_for_gen = re.sub(
                    re.escape(extracted), suggested_name, query, flags=re.I
                )
                log.info("chat_rewrite_confirmed", trace_id=trace_id,
                         before=query[:100], after=question_for_gen[:100],
                         suggested=suggested_name)

        if self._ctx.auth_service:
            total_before = len(results)
            denied_names = [r.name for r in results]

            def _result_domain(r: SearchResult) -> str | None:
                p = r.payload or {}
                return (p.get("domain") or "").strip() or None

            results = await self._ctx.auth_service.filter_results_by_domain(
                user_ctx, results, _result_domain
            )
            accessible = await self._ctx.auth_service.filter_accessible_urns(
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

        results = await self._ctx.reranker.rerank(question_for_gen, results)

        await _emit("rerank")

        # Observability: retrieval latency + rerank signal breakdown.
        log.info("chat_observability", trace_id=trace_id, intent=intent.value,
                 retrieval_ms=round((time.perf_counter() - _t0) * 1000, 1),
                 result_count=len(results),
                 top_score=results[0].score if results else None,
                 rerank_scores=(results[0].payload or {}).get("rerank_scores")
                 if results else None,
                 impact_mode=impact_mode,
                 conversation_id=cid)

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
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question_for_gen, clarification,
            )
            log.info("chat_ambiguous_clarification", trace_id=trace_id, intent=intent.value,
                     top=results[0].name, runner_up=results[1].name, conversation_id=cid)
            return ChatResponse(
                answer=clarification, intent=intent.value, entities=entity_list,
                confidence="low", ambiguous=True, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        short_answer = None if impact_mode else _short_negative_answer(intent, results)
        if short_answer is not None:
            entity_list = [
                EntityItem(urn=r.urn, name=r.name, url=r.datahub_url)
                for r in results if r.name
            ]
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question_for_gen, short_answer,
            )
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
            denied_text = _build_access_denied_message(user_ctx, self._last_denied_names)
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question_for_gen, denied_text,
            )
            answer_text = denied_text
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid,
                insufficient_context=True,
            )

        await _emit("generate")
        if intent == QueryIntent.LINEAGE and results and not impact_mode:
            # Deterministic answer from the SAME payload that drives the SVG.
            answer_text, citations, lineage_main = await self._lineage.build_lineage_answer(
                results[0],
            )
            docs = []
            context_xml = ""
            confidence = "high"
            if on_token:
                await on_token(answer_text)
        elif intent == QueryIntent.SCHEMA_LOOKUP and results and not impact_mode:
            # Deterministic schema listing from the resolved metadata: always
            # names the actual fields instead of asking the LLM to paraphrase
            # (or a mock to drop them). Matches the evidence-layer wording.
            _payload = (results[0].payload or {}) if results[0].payload else {}
            _schema_fields = [
                f.get("name") or "" for f in (_payload.get("schema_fields") or [])
                if (f.get("name") or "").strip()
            ]
            if _schema_fields:
                answer_text = (
                    f"Dataset **{results[0].name}** có các trường: "
                    f"{', '.join(_schema_fields)}."
                )
                citations = []
                docs, context_xml = build_context(results)
                confidence = "high"
                if on_token:
                    await on_token(answer_text)
            else:
                if on_token:
                    answer_text, citations, docs, context_xml, confidence = (
                        await generator.generate_stream(
                            question_for_gen, results, intent, history=history,
                            on_token=on_token, recommendation=recommendation,
                        )
                    )
                else:
                    answer_text, citations, docs, context_xml, confidence = (
                        await generator.generate(
                            question_for_gen, results, intent, history=history,
                            recommendation=recommendation,
                        )
                    )
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
            lineage_data = await self._lineage.build_lineage_data(results[0])
            if lineage_data:
                entity_list = [
                    EntityItem(urn=n.urn, name=n.name, url=n.url)
                    for n in (lineage_data.upstreams + lineage_data.downstreams)
                ] + [
                    EntityItem(urn=lineage_data.entity_urn,
                               name=lineage_data.entity_name,
                               url=lineage_data.entity_url)
                ]

        # Guardrail #9b: ambiguity only applies to single-entity intents. Listing
        # / cross-match intents (TERM_TO_DATASETS, LISTING, DOMAIN_QUERY, ...)
        # legitimately return multiple entities - that is not ambiguity.
        ambiguous = (
            intent in _AMBIGUOUS_CLARIFY_INTENTS
            and len(results) > 1
            and abs(results[0].score - results[1].score) < 0.15
            and results[1].score > 0.5
        )
        insufficient_context = (len(docs) == 0 or confidence == "low") and not (
            (intent == QueryIntent.LINEAGE and results and not impact_mode)
            or (impact_mode and results)
        )

        await self._ctx.memory.add_turn_db(
            self._ctx.session, uid, cid, question_for_gen, answer_text,
        )

        log.info("chat_response", trace_id=trace_id, intent=intent.value,
                 entity_count=len(entity_list), citation_count=len(citations),
                 confidence=confidence, ambiguous=ambiguous,
                 insufficient_context=insufficient_context, conversation_id=cid)

        lineage: LineageData | None = None
        if intent == QueryIntent.LINEAGE and results and not impact_mode:
            lineage = await self._lineage.build_lineage_data(results[0])

        await _emit("done")

        return ChatResponse(
            answer=answer_text,
            intent=plan.intent if impact_mode else intent.value,
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
    def _detect_listing(question: str) -> str | None:
        return _detect_listing(question)

    @staticmethod
    def _detect_entity_type(question: str) -> str | None:
        return _detect_entity_type(question)

    @staticmethod
    def _extract_field_identifier(question: str) -> str | None:
        return _extract_field_identifier(question)

    @staticmethod
    def _extract_name(question: str, remove_words: list[str]) -> str:
        return _extract_name(question, remove_words)

    async def _answer_direct_field_op(
        self, query: str, uid: str, cid: str, trace_id: str | None = None,
    ) -> "ChatResponse | None":
        """Answer a self-contained field question that names its own entity and
        field ("warehouse_id của fact_inventory_movement có kiểu dữ liệu gì?")
        directly from the resolved dataset's schema metadata.

        Returns ``None`` (falls through to the search pipeline) when no explicit
        ``entity.field`` pair can be extracted, the entity can't be trusted, or
        the dataset has no usable ``schema_fields``.
        """
        from app.services.chat.field_ops import answer_field_op

        op = parse_field_operation(query)
        if op is None or op.op == "find_field":
            return None
        entity_name, field = extract_field_entity(query)
        if not entity_name or not field:
            return None
        resolution = await self._ctx.entity_resolver.resolve(
            entity_name, entity_type="dataset", trace_id=trace_id,
        )
        if resolution is None or not _trusted_resolution(resolution):
            return None
        entity_db = await self._ctx.entity_repo.get_by_urn(resolution.resolved.urn)
        if entity_db is None:
            return None
        schema_fields = (entity_db.payload or {}).get("schema_fields") or []
        display = entity_db.display_name or entity_db.name
        text = answer_field_op(
            schema_fields, display,
            FieldOp(op="get_property", property=op.property, field=field),
            citation=entity_db.urn,
        )
        if text is None:
            return None
        self._evidence.record_evidence(
            uid, cid, kind="schema", entity_name=display,
            entity_urn=entity_db.urn, entity_type="dataset",
            structured={
                "schema_fields": schema_fields,
                "fields": [
                    (f.get("name") or "").strip()
                    for f in schema_fields if (f.get("name") or "").strip()
                ],
                "focus_field": field,
            },
            tool_name="field_property", question=query,
            source="schema-metadata",
        )
        await self._ctx.memory.add_turn_db(
            self._ctx.session, uid, cid, query, text,
        )
        intent_label = {
            "data_type": "CONTEXT_FIELD_TYPE",
            "native_data_type": "CONTEXT_FIELD_TYPE",
            "description": "CONTEXT_FIELD_DESCRIPTION",
        }.get(op.property or "", "CONTEXT_FIELD_PROPERTY")
        return ChatResponse(
            answer=text,
            intent=intent_label,
            confidence="high",
            ambiguous=False,
            insufficient_context=False,
            trace_id=trace_id,
            conversation_id=cid,
        )

