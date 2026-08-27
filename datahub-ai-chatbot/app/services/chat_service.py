import asyncio
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import structlog
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ConversationHistory

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
    _MULTI_HOP_CHAIN_RE,
    _METADATA_REPORT_RE,
    _QUALITY_FAVORED_INTENTS,
    _SYNC_RE,
    _TERM_REMOVE_WORDS,
    _TERM_TO_DATASETS_ASK_RE,
    _build_access_denied_message,
    _detect_entity_type,
    _detect_listing,
    _extract_field_identifier,
    _extract_filter_value,
    _extract_name,
    _has_own_identifier,
    _is_column_meaning_question,
    _is_contextual_followup,
    _is_datahub_relevant,
    _is_field_location_question,
    _is_glossary_followup,
    _is_noisy_entity,
    _is_term_in_dataset_question,
    _looks_like_join,
    _short_negative_answer,
    _trusted_resolution,
)
from app.services.image_context import ImageContext
from config.settings import settings
from database.repositories.job_repository import JobRepository
from database.repositories.notification_repository import NotificationRepository
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
from retrieval.intent import QueryIntent, _norm_vn
from retrieval.metadata_filter_engine import MetadataFilterEngine
from retrieval.metadata_query_parser import parse_metadata_query
from retrieval.query_parser import classify_followup_type, merge_query_specs, parse_query
from retrieval.query_understanding import understand_query

log = structlog.get_logger()

# Standard intent taxonomy the QU layer emits (see QUERY_UNDERSTANDING_PROMPT).
STANDARD_TAXONOMY = {
    "FIELD_PROPERTY", "SCHEMA_LOOKUP", "FIND_FIELD", "LINEAGE", "OWNER",
    "GLOSSARY", "JOIN", "ENTITY_EXISTS", "TERM_TO_DATASETS", "GENERAL",
    "COUNT",
}

# Deterministic mapping from the legacy evidence / field-property path labels
# to the standard taxonomy. Used when the QU layer produced no usable intent:
# the label a path stamps on the answer ("where the answer came from") is
# separate from what the question really ASKS. Unlisted labels are kept as-is
# (OWNER_LOOKUP, ENTITY_DOMAIN, QUALITY_REPORT, SCHEMA_LOOKUP, LINEAGE, ...).
FALLBACK_INTENT_MAP = {
    "CONTEXT_FIELD_FIND": "FIELD_PROPERTY",
    "CONTEXT_FIELD_DESCRIPTION": "FIELD_PROPERTY",
    "CONTEXT_FIELD_TYPE": "FIELD_PROPERTY",
    "CONTEXT_FIELD_PROPERTY": "FIELD_PROPERTY",
    "CONTEXT_FIELD_LOCATION": "SCHEMA_LOOKUP",
    "CONTEXT_FIELD_GLOSSARY": "GLOSSARY",
    "CONTEXT_JOIN": "JOIN",
    "CONTEXT_LINEAGE": "LINEAGE",
    "CONTEXT_EVIDENCE": "GENERAL",
}


def _qu_primary_intent(understanding) -> str | None:
    """The question's standard-taxonomy intent as read by the QU layer.

    Prefers the first structured sub-question's intent, then derives a
    deterministic label from the top-level contract. ``None`` when the QU
    layer produced nothing usable — the caller falls back to
    :data:`FALLBACK_INTENT_MAP`.
    """
    if understanding is None:
        return None
    for sq in understanding.sub_question_details:
        intent = (sq.intent or "").strip().upper()
        if intent in STANDARD_TAXONOMY:
            return intent
    if understanding.is_field_property_question:
        return "FIELD_PROPERTY"
    return None


def _unify_intent_label(raw: str, understanding) -> str:
    """Resolve the final response ``intent`` to the standard taxonomy.

    ``raw`` is the path-stamped label (e.g. ``CONTEXT_FIELD_FIND``); the QU
    layer's read of the question wins when available, otherwise the
    deterministic legacy→standard map applies.
    """
    qu_intent = _qu_primary_intent(understanding)
    if qu_intent:
        return qu_intent
    return FALLBACK_INTENT_MAP.get(raw, raw)


# Concept families whose glossary terms must be disambiguated by domain.
# "Demand là gì?" maps to several catalog terms (Nhu cầu linh kiện, Demand of
# all build phases per variant, Required Demand); only a domain (or listing
# every member) answers it. Keywords are normalized (lowercase, diacritics
# stripped) and matched against normalized term names.
_GLOSSARY_CONCEPT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "demand": ("demand", "nhu cau linh kien"),
}

_TERM_DOMAIN_CACHE: dict[str, Any] = {
    "term_domains": None,
    "built_at": 0.0,
}


# Vietnamese name-derived meaning for the most common catalog columns. Field
# descriptions are frequently empty in DataHub; "trường X nghĩa là gì?" is
# answered deterministically from the field name ("bu_short_name" -> "tên viết
# tắt của đơn vị kinh doanh") rather than by an LLM.
_FIELD_MEANING_MAP: dict[str, str] = {
    "bu_short_name": "tên viết tắt của đơn vị kinh doanh (Business Unit short name)",
    "sod_total_amount": "tổng giá trị đơn bán (Sales Order Detail total amount)",
    "is_manufacturing": "đánh dấu nhà máy sản xuất (Manufacturing plant flag)",
    "plant_id": "mã định danh của nhà máy (Plant identifier)",
    "plant_name": "tên của nhà máy (Plant name)",
    "material_code": "mã định danh của nguyên vật liệu/linh kiện (Material code)",
    "material_name": "tên của nguyên vật liệu/linh kiện (Material name)",
    "vendor_code": "mã định danh của nhà cung cấp (Vendor code)",
    "vendor_name": "tên của nhà cung cấp (Vendor name)",
    "order_date": "ngày đặt hàng (Order date)",
    "sales_order_number": "số đơn hàng bán (Sales order number)",
    "unit_price": "đơn giá (Unit price)",
    "quantity": "số lượng (Quantity)",
    "status": "trạng thái (Status)",
}

_FIELD_FRAGMENT_VN: tuple[tuple[str, str], ...] = (
    ("short", "viết tắt"),
    ("name", "tên"),
    ("id", "mã định danh"),
    ("code", "mã"),
    ("description", "mô tả"),
    ("amount", "giá trị"),
    ("total", "tổng"),
    ("qty", "số lượng"),
    ("quantity", "số lượng"),
    ("date", "ngày"),
    ("status", "trạng thái"),
    ("type", "loại"),
    ("flag", "cờ đánh dấu"),
    ("is_", "cờ đánh dấu"),
    ("plant", "nhà máy"),
    ("factory", "nhà máy"),
    ("manufacturing", "sản xuất"),
    ("businessunit", "đơn vị kinh doanh"),
    ("unit", "đơn vị"),
    ("order", "đơn hàng"),
    ("salesorder", "đơn bán"),
    ("price", "giá"),
    ("key", "khóa"),
)


def _field_meaning(field_name: str) -> str:
    """Name-derived Vietnamese meaning for a column (grounded, no LLM)."""
    name = (field_name or "").strip().lower().replace(" ", "_")
    if not name:
        return ""
    if name in _FIELD_MEANING_MAP:
        return _FIELD_MEANING_MAP[name]
    parts = [p for p in re.split(r"[_\W]+", name) if p]
    vn: list[str] = []
    for p in parts:
        for frag, v in _FIELD_FRAGMENT_VN:
            if p == frag or p.startswith(frag):
                if v not in vn:
                    vn.append(v)
                break
    if vn:
        return " ".join(vn)
    return f"dữ liệu của trường {field_name} (theo tên trường)"


def _build_grounded_fallback(intent: QueryIntent, results: Sequence[Any]) -> str:
    """Deterministic metadata-grounded fallback when the LLM provider fails.

    The Fireworks/NVIDIA provider intermittently times out on the corporate
    network; instead of returning the generic "lỗi khi tạo câu trả lời" string,
    list the already-resolved entities so the user still gets a grounded,
    retrieval-level answer.
    """
    valid = [r for r in results if (r.name or "").strip()]
    if not valid:
        return ""
    lines: list[str] = []
    for _i, _r in enumerate(valid[:8], 1):
        _pl = _r.payload or {}
        _name = _r.name or ""
        _bit = f"{_i}. **{_name}**"
        _plat = (_pl.get("platform") or "").strip()
        _etype = (_pl.get("entity_type") or _r.entity_type or "").strip()
        _parts = []
        if _etype:
            _parts.append(_etype)
        if _plat:
            _parts.append(f"nền tảng {_plat}")
        if _parts:
            _bit += f" ({', '.join(_parts)})"
        _desc = (_pl.get("description") or "").strip()
        if _desc:
            _bit += f" — {_desc[:180]}"
        lines.append(_bit)
        lines.append("")
    if intent == QueryIntent.TERM_TO_DATASETS:
        return ("Các entity liên quan trong metadata DataHub:\n\n"
                + "\n".join(lines).strip())
    return "Trong metadata DataHub hiện có các entity liên quan:\n\n" + "\n".join(lines).strip()


async def _term_domain_map(entity_repo) -> dict[str, set[str]]:
    """Map glossary-term URN -> canonical dataset domains linking to it.

    The catalog is static during a session, so the map is cached for the
    process lifetime.
    """
    cached = _TERM_DOMAIN_CACHE["term_domains"]
    if cached is not None:
        return cached
    term_domains: dict[str, set[str]] = {}
    try:
        datasets = await entity_repo.list_by_type("dataset", limit=100000)
    except Exception:  # noqa: BLE001
        return term_domains
    for e in datasets:
        pl = e.payload or {}
        dom = (pl.get("domain") or "").strip()
        if not dom:
            continue
        for tu in (pl.get("glossary_terms") or []):
            if not tu:
                continue
            term_domains.setdefault(tu, set()).add(dom)
    _TERM_DOMAIN_CACHE["term_domains"] = term_domains
    _TERM_DOMAIN_CACHE["built_at"] = time.time()
    return term_domains


async def _term_linked_datasets(entity_repo) -> dict[str, list[str]]:
    """Map glossary-term URN -> dataset names (across every domain)."""
    key = "term_datasets"
    cached = _TERM_DOMAIN_CACHE.get(key)
    if cached is not None:
        return cached
    term_datasets: dict[str, list[str]] = {}
    try:
        datasets = await entity_repo.list_by_type("dataset", limit=100000)
    except Exception:  # noqa: BLE001
        return term_datasets
    for e in datasets:
        pl = e.payload or {}
        name = (e.name or "").strip()
        if not name:
            continue
        for tu in (pl.get("glossary_terms") or []):
            if not tu:
                continue
            term_datasets.setdefault(tu, []).append(name)
    _TERM_DOMAIN_CACHE[key] = term_datasets
    return term_datasets


async def _glossary_concept_members(entity_repo, concept: str) -> list[dict]:
    """Glossary terms belonging to a concept family (name, description, URN)."""
    keywords = _GLOSSARY_CONCEPT_KEYWORDS.get(concept)
    if not keywords:
        return []
    try:
        terms = await entity_repo.list_by_type("glossary_term", limit=100000)
    except Exception:  # noqa: BLE001
        return []
    out: list[dict] = []
    for t in terms:
        name = (t.name or "").strip()
        if not name:
            continue
        blob = _norm_vn(name)
        if any(k in blob for k in keywords):
            pl = t.payload or {}
            out.append({
                "urn": t.urn,
                "name": name,
                "description": (pl.get("description") or "").strip(),
            })
    return out


async def _domain_scoped_term_answer(question: str, ctx: "ChatContext",
                                     results: Sequence[Any]) -> tuple | None:
    """Domain-scoped glossary answer for a concept family.

    Handles "Demand là gì?" (no domain -> list every family member and ask for
    the domain), "Demand trong domain SẢN XUẤT là gì?" (pick the member whose
    linked datasets belong to that domain) and "so sánh Demand giữa A và B"
    (per-domain resolution, UNKNOWN when a domain has no clear member).
    Returns the (answer_text, citations, docs, context_xml, confidence) tuple
    when the question targets a concept family, else ``None`` to fall through
    to the generic term definition path.
    """
    if not results:
        return None
    q = _norm_vn(question)
    if not re.search(r"là gì|la gi|nghĩa|nghia|định nghĩa|dinh nghia|giới thiệu|"
                     r"so sánh|so sanh|compare|comparison", q):
        return None
    concept = next(
        (c for c, kws in _GLOSSARY_CONCEPT_KEYWORDS.items()
         if any(k in q for k in kws)),
        None,
    )
    if concept is None:
        return None
    entity_repo = ctx.entity_repo
    members = await _glossary_concept_members(entity_repo, concept)
    if not members:
        return None
    term_domains = await _term_domain_map(entity_repo)

    domains: list[str] = []
    access = getattr(ctx, "access", None)
    if access is not None:
        try:
            domains = await access.detect_requested_domains(question)
        except Exception:  # noqa: BLE001
            domains = []

    def _member_for_domain(domain: str) -> dict | None:
        dkey = _norm_vn(domain)
        for m in members:
            for d in term_domains.get(m["urn"], set()):
                if _norm_vn(d) == dkey:
                    return m
        return None

    def _member_lines(members_: list[dict]) -> str:
        lines = []
        for _i, _m in enumerate(members_, 1):
            _d = ", ".join(sorted(term_domains.get(_m["urn"], set()))) or "chưa xác định"
            lines.append(f"{_i}. **{_m['name']}** (`{_m['urn']}`) — domain: {_d}")
        return "\n".join(lines)

    answer_text: str | None = None
    if len(domains) == 1:
        m = _member_for_domain(domains[0])
        if m:
            _term_ds = await _term_linked_datasets(entity_repo)
            _ds = [
                n for n in _term_ds.get(m["urn"], [])
                if n
            ]
            answer_text = (
                f"Trong domain **{domains[0]}**, **{concept}** tương ứng với "
                f"thuật ngữ **{m['name']}** (`{m['urn']}`):\n\n{m['description']}"
            )
            if _ds:
                answer_text += f"\n\nLiên quan dataset: **{_ds[0]}**."
        else:
            answer_text = (
                f"Không có thuật ngữ **{concept}** rõ ràng trong domain "
                f"**{domains[0]}** trong DataHub → UNKNOWN."
            )
    elif len(domains) >= 2 and re.search(r"so sánh|so sanh|compare|so với|so voi|khác gì|khac gi|khác nhau|khac nhau|khác biệt|khac biet|phân biệt|phan biet|khác|khac", q):
        parts = []
        for dom in domains:
            m = _member_for_domain(dom)
            if m:
                _desc = (m.get("description") or "").strip()
                if len(_desc) > 300:
                    _desc = _desc[:300] + "..."
                parts.append(
                    f"- **Domain {dom.upper()}**:\n  Thuật ngữ tương ứng: **{m['name']}** (`{m['urn']}`).\n  *Định nghĩa:* {_desc}"
                )
            else:
                parts.append(
                    f"- **Domain {dom.upper()}**:\n  Hiện chưa có thuật ngữ chuyên biệt cho **{concept}** trong DataHub (UNKNOWN). Trong nghiệp vụ bán hàng / thương mại, Demand thường đại diện cho nhu cầu thị trường, đơn hàng hoặc dự báo doanh số."
                )
        answer_text = f"Sự khác biệt về định nghĩa **{concept}** giữa các domain:\n\n" + "\n\n".join(parts)
    else:
        # The query may name ONE family member exactly ("Nhu cầu linh kiện
        # là gì?") — answer that term directly instead of re-listing the whole
        # family (the concept keyword also matches the member's own name).
        named_members = [
            m for m in members if _norm_vn(m["name"]) in q
        ]
        if len(named_members) == 1:
            m = named_members[0]
            _term_ds = await _term_linked_datasets(entity_repo)
            _ds = [n for n in _term_ds.get(m["urn"], []) if n]
            answer_text = (
                f"Thuật ngữ **{m['name']}** (`{m['urn']}`):\n\n{m['description']}"
            )
            if _ds:
                answer_text += f"\n\nLiên quan dataset: **{_ds[0]}**."
        else:
            answer_text = (
                f"Thuật ngữ **{concept}** có nhiều định nghĩa khác nhau trong "
                f"DataHub ({len(members)} term liên quan):\n\n{_member_lines(members)}\n\n"
                "Cần nêu rõ domain (SẢN XUẤT / KINH DOANH / LOGISTIC / ...) để chọn "
                "đúng định nghĩa."
            )
    if not answer_text:
        return None
    citations: list = []
    docs, context_xml = build_context(results)
    log.info("domain_scoped_glossary", question=question[:100],
             concept=concept, domains=domains, members=len(members))
    return (answer_text, citations, docs, context_xml, "high")


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
        from app.services.interaction_logger import InteractionLogger

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
        self._interaction_logger = InteractionLogger(session)
        self._last_denied_names: list[str] = []


    def _upload_service(self):
        from app.services.image_upload import ImageUploadService

        return ImageUploadService(
            self._ctx.session, vision_service=self._ctx.conversation_vision,
        )

    async def _log_interaction_async(self, op: str, **kwargs: Any) -> None:
        """Write interaction log using a dedicated session to avoid autoflush conflicts.

        ``op`` is ``"request"`` or ``"response"``.
        In test mode (APP_ENV=test) the write is skipped entirely.
        """
        import os
        if os.getenv("APP_ENV") == "test":
            return
        try:
            from app.services.interaction_logger import InteractionLogger
            from database.session import async_session_factory

            async with async_session_factory() as bg_session:
                logger = InteractionLogger(bg_session)
                if op == "request":
                    await logger.log_request(**kwargs)
                elif op == "response":
                    await logger.log_response(**kwargs)
                await bg_session.commit()
        except Exception:  # noqa: BLE001
            log.warning("interaction_log_async_failed", op=op)

    async def _postprocess_response(

        self,
        res: ChatResponse,
        t_start: float,
        uid: str,
        cid: str,
        question: str,
    ) -> ChatResponse:
        if res.response_time_ms is None:
            res.response_time_ms = int((time.perf_counter() - t_start) * 1000)

        try:
            from sqlalchemy import select, update as sa_update
            from database.models import ConversationHistory

            result = await self._ctx.session.execute(
                select(ConversationHistory)
                .where(
                    ConversationHistory.user_id == uid,
                    ConversationHistory.conversation_id == cid,
                )
                .order_by(ConversationHistory.id.desc())
                .limit(1)
            )
            latest = result.scalars().first()
            if latest:
                rs = dict(latest.render_state or {})
                rs["response_time_ms"] = res.response_time_ms
                if res.intent:
                    rs["intent"] = res.intent
                if res.trace_id:
                    rs["trace_id"] = res.trace_id
                if res.confidence:
                    rs["confidence"] = res.confidence
                if res.entities:
                    rs["entities"] = [e.model_dump() for e in res.entities]
                if res.citations:
                    rs["citations"] = [
                        c.model_dump() if hasattr(c, "model_dump") else dict(c)
                        for c in res.citations
                    ]
                if res.lineage:
                    rs["lineage"] = res.lineage.model_dump()
                if res.selected_action:
                    rs["selected_action"] = res.selected_action

                latest.render_state = rs
                await self._ctx.session.commit()

        except Exception as exc:
            log.exception("postprocess_response_render_state_failed", trace_id=res.trace_id, error=str(exc))


        return res

    async def _background_ragas_eval(

        self, trace_id: str, question: str, answer: str, contexts: list, history: list | None = None
    ) -> None:
        """Run RAGAS evaluation in background. Never raises, never blocks chat.

        Uses a fresh database session to avoid conflicts with the request session.
        Creates job and notification linked to the evaluation.
        When history is provided, uses conversation-aware evaluation.
        """
        import os
        if os.getenv("APP_ENV") == "test":
            return

        from database.repositories.job_repository import JobRepository
        from database.repositories.notification_repository import NotificationRepository
        from database.session import async_session_factory

        try:
            from evaluation.ragas_evaluator import evaluate_interaction

            # Create a fresh session for background evaluation
            async with async_session_factory() as bg_session:
                job_repo = JobRepository(bg_session)
                notif_repo = NotificationRepository(bg_session)

                # Create job and notification for this evaluation
                user_id = getattr(self._ctx, "user", None).user_id if self._ctx and hasattr(self._ctx, "user") else None
                job = await job_repo.create(
                    type="ragas_evaluation",
                    title="RAGAS Evaluation",
                    message=f"Starting evaluation for trace {trace_id[:8]}...",
                    user_id=user_id,
                    job_metadata={"trace_id": trace_id},
                )

                await notif_repo.create(
                    job_id=job.id,
                    user_id=user_id or "system",
                    type="ragas_evaluation",
                    title="RAGAS Evaluation",
                    message="Starting evaluation...",
                    status="running",
                )

                from app.services.interaction_logger import InteractionLogger

                # Convert ContextDocument objects to strings for RAGAS
                ctx_strings = []
                for ctx in contexts:
                    if isinstance(ctx, str):
                        ctx_strings.append(ctx)
                    elif hasattr(ctx, "content"):
                        ctx_strings.append(ctx.content)
                    else:
                        ctx_strings.append(str(ctx))

                bg_logger = InteractionLogger(bg_session)

                await bg_logger.set_evaluation_status(trace_id, "RUNNING")

                if history:
                    from evaluation.ragas_evaluator import evaluate_conversation_turn
                    result = await evaluate_conversation_turn(
                        question=question,
                        answer=answer,
                        retrieved_contexts=ctx_strings,
                        conversation_history=history,
                        reference="\n".join(ctx_strings) if ctx_strings else None,
                        timeout_seconds=120.0,
                    )
                else:
                    result = await evaluate_interaction(
                        question=question,
                        answer=answer,
                        retrieved_contexts=ctx_strings,
                        reference="\n".join(ctx_strings) if ctx_strings else None,
                        timeout_seconds=120.0,
                    )

                await bg_logger.update_ragas_scores(
                    trace_id=trace_id,
                    faithfulness=result.faithfulness,
                    faithfulness_status=result.faithfulness_status,
                    answer_relevancy=result.answer_relevancy,
                    answer_relevancy_status=result.answer_relevancy_status,
                    context_precision=result.context_precision,
                    context_precision_status=result.context_precision_status,
                    context_recall=result.context_recall,
                    context_recall_status=result.context_recall_status,
                    evaluation_model=result.evaluation_model,
                    evaluation_error=result.error,
                )

                # Mark job as success and update notification status
                await job_repo.mark_success(job.id)

                await bg_session.commit()
                log.info("ragas_background_eval_done", trace_id=trace_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("ragas_background_eval_failed", trace_id=trace_id, error=str(exc))
            try:
                async with async_session_factory() as err_session:
                    err_repo = JobRepository(err_session)
                    notif_repo = NotificationRepository(err_session)
                    # Try to find and update existing job/notif
                    if 'job' in dir() and job is not None:
                        await err_repo.mark_failed(job.id, str(exc))
                    if 'notif' in dir() and 'notif' in dir():
                        pass  # notification already created with running status
                    await err_session.commit()
            except Exception:  # noqa: BLE001
                pass

    async def _generate_or_fallback(
        self, generator, question: str, results: Sequence[Any],
        intent: QueryIntent, history: list | None, on_token,
        recommendation,
    ) -> tuple:
        """LLM generation with a deterministic, metadata-grounded fallback.

        The Fireworks/NVIDIA provider intermittently times out on the corporate
        network; instead of surfacing the generic "lỗi khi tạo câu trả lời"
        string, fall back to a grounded listing of the already-resolved metadata
        so the user still receives a retrieval-level answer with provenance.
        """
        if on_token:
            answer_text, citations, docs, context_xml, confidence = (
                await generator.generate_stream(
                    question, results, intent, history=history,
                    on_token=on_token, recommendation=recommendation,
                )
            )
        else:
            answer_text, citations, docs, context_xml, confidence = (
                await generator.generate(
                    question, results, intent, history=history,
                    recommendation=recommendation,
                )
            )
        if answer_text and "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời" not in answer_text:
            return answer_text, citations, docs, context_xml, confidence
        fallback = _build_grounded_fallback(intent, results)
        if not fallback:
            # Nothing to fall back on: surface the no-evidence response, never
            # the provider error string (a user must not see "đã xảy ra lỗi"
            # when the real situation is that no metadata was retrieved).
            from guardrails.validation import NO_EVIDENCE_RESPONSE
            return NO_EVIDENCE_RESPONSE, citations, docs, context_xml, "low"
        docs, context_xml = build_context(results)
        log.info("generation_fallback_deterministic", intent=intent.value,
                 question=question[:100], entities=len(results))
        return fallback, [], docs, context_xml, "medium"


    async def answer(self, question: str, user: UserContext | None = None,
                     conversation_id: str | None = None,
                     suggested_name: str | None = None,
                     model: str | None = None,
                     selected_action: str | None = None,
                     images: list[str] | None = None,
                     ragas_enabled: bool = True,
                     on_status: Callable[[str], Awaitable[None]] | None = None,
                     on_token: Callable[[str], Awaitable[None]] | None = None) -> ChatResponse:
        trace_id = uuid.uuid4().hex[:12]
        cid = conversation_id or trace_id
        _t_start = time.perf_counter()
        user_ctx = user or UserContext(user_id="anonymous", is_admin=False)
        uid = user_ctx.user_id

        res = await self._answer_impl(
            question=question, user=user, conversation_id=conversation_id,
            suggested_name=suggested_name, model=model,
            selected_action=selected_action, images=images,
            ragas_enabled=ragas_enabled, on_status=on_status,
            on_token=on_token, trace_id=trace_id, cid=cid,
            _t_start=_t_start, user_ctx=user_ctx, uid=uid,
        )
        return await self._postprocess_response(res, _t_start, uid, cid, question)

    async def _answer_impl(
        self, question: str, user: UserContext | None,
        conversation_id: str | None, suggested_name: str | None,
        model: str | None, selected_action: str | None,
        images: list[str] | None, ragas_enabled: bool,
        on_status: Callable[[str], Awaitable[None]] | None,
        on_token: Callable[[str], Awaitable[None]] | None,
        trace_id: str, cid: str, _t_start: float, user_ctx: UserContext, uid: str,
    ) -> ChatResponse:
        # Log incoming request (uses dedicated session to avoid autoflush conflicts)
        await self._log_interaction_async(
            "request", trace_id=trace_id,
            question=question, user_id=user_ctx.user_id,
            conversation_id=cid, selected_action=selected_action, model=model,
        )


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

        # H7: Parse query into structured QuerySpec and classify follow-up type.
        # This replaces the regex-based _is_contextual_followup() for the
        # structured path and provides merge logic for follow-ups.
        try:
            new_query_spec = parse_query(question, selected_action=selected_action)
            prev_query_spec = self._ctx.memory.get_query_spec(uid, cid)
            prev_entity = (prev_query_spec or {}).get("entity_name")
            _followup_type = classify_followup_type(question, prev_query_spec, prev_entity)
            merged_spec = merge_query_specs(prev_query_spec, new_query_spec)
            _query_spec_dict = merged_spec.to_dict()
        except Exception:
            log.exception("query_spec_parse_error", trace_id=trace_id, question=question[:100])
            new_query_spec = None
            prev_query_spec = None
            _followup_type = "NEW_QUERY"
            _query_spec_dict = None
            merged_spec = None

        # H8: If this is a clarification response, check for pending clarification
        # state in ConversationMemory to get the actual pending query spec.
        if _followup_type == "CLARIFICATION_RESPONSE":
            pending_clarification = self._ctx.memory.get_clarification_state(uid, cid)
            if pending_clarification and pending_clarification.pending_query_spec:
                _query_spec_dict = pending_clarification.pending_query_spec
                self._ctx.memory.clear_clarification_state(uid, cid)
                log.info("clarification_response_resolved", trace_id=trace_id,
                         clarification_type=pending_clarification.clarification_type)

        # H7: query_spec_dict and _followup_type are now passed explicitly
        # to add_turn_db() at the critical call sites below (no context vars).

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

        # Guardrails: scope restriction (#5) and prompt injection in user input (#16).
        out_of_scope = self._ctx.guardrails.enforce_scope(question)
        if out_of_scope:
            log.info("chat_out_of_scope", trace_id=trace_id, question=question[:100])
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question, out_of_scope,
                query_spec=_query_spec_dict, followup_type=_followup_type,
            )
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

        if decision == "clarify":
            answer_text = resolution.clarification or (
                "Xin lỗi, tôi chưa rõ bạn muốn làm gì. Bạn có thể làm rõ thêm yêu cầu được không?"
            )
            log.info("route_clarify", trace_id=trace_id, intent=intent.value,
                     selected_action=selected_action, answer=answer_text[:120])
            # H8: Persist clarification state — store pending query spec + candidates
            # so the next user message can be matched back to the original query.
            if _query_spec_dict:
                candidates = []
                if hasattr(resolution, "candidates") and resolution.candidates:
                    candidates = [
                        {"name": getattr(c, "name", str(c)),
                         "entity_type": getattr(c, "entity_type", None),
                         "urn": getattr(c, "urn", None)}
                        for c in resolution.candidates
                    ]
                self._ctx.memory.set_clarification_state(
                    uid, cid,
                    pending_query_spec=_query_spec_dict,
                    candidates=candidates,
                    clarification_type="entity_disambiguation",
                )
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question, answer_text,
                query_spec=_query_spec_dict, followup_type=_followup_type,
            )
            _processing_ms = int((time.perf_counter() - _t_start) * 1000)
            await self._log_interaction_async(
                "response", trace_id=trace_id, answer=answer_text, intent=intent.value,
                confidence="low", ambiguous=True, insufficient_context=True,
                processing_time_ms=_processing_ms, routing_decision="clarify",
            )
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="low",
                ambiguous=True, insufficient_context=True,
                trace_id=trace_id, conversation_id=cid,
            )

        # --- Confirmation/Denial of previous suggestion ---
        # When the user confirms a suggestion ("đúng rồi", "yes"), rewrite the
        # question with the confirmed entity and proceed normally.
        # When the user denies ("không", "khác"), ask for clarification.
        if decision == "confirm":
            # H8: Check if there's a pending clarification state — use the
            # pending query spec as the base, merging with the user's selection.
            pending_clarification = self._ctx.memory.get_clarification_state(uid, cid)
            if pending_clarification and pending_clarification.pending_query_spec:
                _query_spec_dict = pending_clarification.pending_query_spec
                self._ctx.memory.clear_clarification_state(uid, cid)
                log.info("route_confirm_clarification_resolved", trace_id=trace_id,
                         clarification_type=pending_clarification.clarification_type,
                         conversation_id=cid)

            confirmed_entity = resolution.entity_hint
            if confirmed_entity:
                # Rewrite question with confirmed entity
                query = f"{confirmed_entity}"
                entity_hint = confirmed_entity
                log.info("route_confirm", trace_id=trace_id, intent=intent.value,
                         entity=confirmed_entity, conversation_id=cid)
            else:
                # Confirm without entity — proceed with original query
                log.info("route_confirm_no_entity", trace_id=trace_id,
                         intent=intent.value, conversation_id=cid)
        elif decision == "deny":
            answer_text = (
                "Bạn muốn hỏi về entity nào khác? Vui lòng nhập tên entity bạn muốn tìm."
            )
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question, answer_text,
                query_spec=_query_spec_dict, followup_type=_followup_type,
            )
            _processing_ms = int((time.perf_counter() - _t_start) * 1000)
            await self._log_interaction_async(
                "response",
                trace_id=trace_id, answer=answer_text, intent=intent.value,
                confidence="low", ambiguous=True, insufficient_context=True,
                processing_time_ms=_processing_ms, routing_decision="deny",
            )
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent=intent.value, confidence="low",
                ambiguous=True, insufficient_context=True,
                trace_id=trace_id, conversation_id=cid,
            )

        # Multi-hop chain ("từ report capacity → định nghĩa → cột → công thức →
        # nguồn dữ liệu thô", "trong domain X tìm report về Y, term, dataset và
        # lineage"): walk each hop from catalog metadata and mark missing hops
        # UNKNOWN. Re-detect on the raw question — the resolver normalizes the
        # new taxonomy intent down to FIND_ENTITY/SCHEMA_LOOKUP/LINEAGE.
        if _MULTI_HOP_CHAIN_RE.search(question):
            chain_resp = await self._ctx.flows.multi_hop_chain_flow(
                uid, cid, question, trace_id)
            if chain_resp is not None:
                await self._ctx.memory.add_turn_db(
                    self._ctx.session, uid, cid, question, chain_resp.answer)
                await _emit("done")
                return chain_resp

        # Retrieval / generation runs on the effective question: the raw message,
        # or the action-framed question when the action supplies the missing context.
        query = resolution.effective_question or question
        entity_hint = suggested_name or resolution.entity_hint or new_query_spec.entity_name
        if concept_phrase:
            entity_hint = concept_phrase

        # Query Understanding (opt-in): read the effective question + conversation
        # context (evidence, active entity, schema fields, catalog names) into a
        # structured JSON contract — focus_field/property, thinking and
        # decomposition needs, anaphora target. Every consumer below treats it as
        # advice only (never an order); when disabled or failed None means the
        # keyword/regex + coreference heuristics run unchanged.
        understanding = None
        validation = None
        qu_apply = settings.QU_ENABLED and not settings.QU_SHADOW_MODE
        if settings.QU_ENABLED or settings.QU_SHADOW_MODE:
            from retrieval.validator import (
                apply_validation,
                build_grounding_context,
                validate_understanding,
            )
            _ground = await build_grounding_context(
                self._ctx.memory, self._ctx.entity_repo, uid, cid,
                active_entities, trace_id,
            )
            understanding = await understand_query(
                query, llm=self._ctx.llm, history=history,
                evidence=_ground.evidence, active_entity=_ground.active_entity,
                field_names=_ground.field_names, catalog_names=_ground.catalog_names,
            )
            if understanding is not None:
                validation = validate_understanding(
                    understanding,
                    schema_fields=_ground.field_names,
                    catalog_names=_ground.catalog_names,
                    active_entity=_ground.active_entity,
                    has_evidence_for_active=_ground.has_evidence_for_active,
                    trace_id=trace_id,
                )
                log.info(
                    "query_understanding",
                    trace_id=trace_id,
                    question=query[:100],
                    focus_field=understanding.focus_field,
                    property=understanding.property,
                    is_field_property=understanding.is_field_property_question,
                    needs_thinking=understanding.needs_thinking,
                    needs_decomposition=understanding.needs_decomposition,
                    sub_questions=len(understanding.sub_questions),
                    anaphora_target=understanding.anaphora_target,
                    confidence=understanding.confidence,
                    parse_confidence=understanding.parse_confidence,
                    source=understanding.source,
                    complexity_reason=understanding.complexity_reason,
                    validator=validation.to_dict() if validation else None,
                )
            if understanding is not None and qu_apply:
                # Merge the guardrail verdict into the contract the router reads:
                # drop ungrounded fields / entities, embargo unsafe sub-questions.
                understanding = apply_validation(understanding, validation)
            elif understanding is not None and not qu_apply:
                # Shadow mode: measure the contract + validator without applying
                # any routing decision, so regex behaviour is preserved exactly.
                understanding = None

        log.info("chat_request", trace_id=trace_id, intent=intent.value,
                 question=question[:100], conversation_id=cid)

        if intent == QueryIntent.GREETING:
            import random
            answer_text = random.choice(_GREETING_RESPONSES)
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            _processing_ms = int((time.perf_counter() - _t_start) * 1000)
            await self._log_interaction_async("response",
                trace_id=trace_id, answer=answer_text, intent=intent.value,
                confidence="high", processing_time_ms=_processing_ms,
            )
            res = ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid, response_time_ms=_processing_ms,
            )
            return await self._postprocess_response(res, _t_start, uid, cid, question)

        if intent == QueryIntent.CHITCHAT:
            cleaned = question.lower().strip().rstrip("?!.")
            answer_text = _CHITCHAT_RESPONSES.get(
                cleaned, "Tôi là trợ lý DataHub, sẵn sàng giúp bạn!",
            )
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            _processing_ms = int((time.perf_counter() - _t_start) * 1000)
            await self._log_interaction_async("response",
                trace_id=trace_id, answer=answer_text, intent=intent.value,
                confidence="high", processing_time_ms=_processing_ms,
            )
            res = ChatResponse(
                answer=answer_text, intent=intent.value, confidence="high",
                trace_id=trace_id, conversation_id=cid, response_time_ms=_processing_ms,
            )
            return await self._postprocess_response(res, _t_start, uid, cid, question)


        # Guardrails: scope restriction (#5) and prompt injection in user input (#16).
        out_of_scope = self._ctx.guardrails.enforce_scope(question)
        if out_of_scope:
            log.info("chat_out_of_scope", trace_id=trace_id, question=question[:100])
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question, out_of_scope,
                query_spec=_query_spec_dict, followup_type=_followup_type,
            )
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
        if relevance != DataHubRelevance.DATAHUB:
            # Query-Understanding rescue: an explicit field-property question
            # ("quantity có kiểu dữ liệu gì?", "warehouse_id nằm ở bảng nào?")
            # is metadata scope even when the LLM relevance gate hesitates.
            if (understanding is not None
                    and (understanding.is_field_property_question
                         or understanding.focus_field is not None)):
                log.info("route_qu_relevance_rescued", trace_id=trace_id,
                         question=query[:100])
                relevance = DataHubRelevance.DATAHUB
            elif _is_datahub_relevant(query):
                log.info("route_ai_keyword_rescued", trace_id=trace_id, question=query[:100])
                relevance = DataHubRelevance.DATAHUB
            elif not re.search(
                    r"\b(dataset|bảng|bang|dashboard|report|báo cáo|bao cao)\b",
                    query, re.IGNORECASE):
                # Glossary-alias rescue: the question references a catalog term
                # by its English parenthetical alias ("Demand là gì?", "so sánh
                # Demand giữa SẢN XUẤT và KINH DOANH"). The alias word alone
                # carries no DataHub vocabulary, so neither the LLM relevance
                # gate nor the keyword heuristic sees it — but the catalog
                # lookup is deterministically resolvable. Keep it in scope so
                # the alias guard below can route it to TERM_DEFINITION instead
                # of a clarification.
                try:
                    _rel_alias = await self._entities.resolve_glossary_by_alias(
                        query, question=query, trace_id=trace_id)
                except Exception:  # noqa: BLE001
                    log.exception("relevance_alias_rescue_failed",
                                  trace_id=trace_id, question=query[:100])
                    _rel_alias = []
                if _rel_alias:
                    log.info("route_ai_alias_rescued", trace_id=trace_id,
                             question=query[:100])
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
                # Unify the intent label to the standard taxonomy: keep the
                # answer path (evidence_context) separate from what the
                # question actually asks. QU's read wins; otherwise map the
                # legacy path label deterministically.
                _evidence_response.intent = _unify_intent_label(
                    _evidence_response.intent, understanding,
                )
                _evidence_response.answer_path = "evidence_context"
                log.info("route_evidence_context", trace_id=trace_id,
                         question=query[:100],
                         evidence=_evidence_resolution.referenced_evidence_ids,
                         intent=_evidence_response.intent,
                         answer_path=_evidence_response.answer_path)
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
            query, uid, cid, trace_id, understanding=understanding,
        )
        if _field_property_response is not None:
            _field_property_response.intent = _unify_intent_label(
                _field_property_response.intent, understanding,
            )
            _field_property_response.answer_path = "field_property"
            log.info("route_field_property", trace_id=trace_id,
                     question=query[:100],
                     intent=_field_property_response.intent,
                     answer_path=_field_property_response.answer_path)
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

        # R1 — LLM-first intent & request understanding. The semantic classifier
        # is the PRIMARY intent analyzer: it runs BEFORE the Thinking gate so a
        # confident LLM intent (e.g. TERM_TO_DATASETS for "dataset chứa thông tin
        # khách hàng (PII) nào...", FIND_ENTITY for description-based discovery
        # "có báo cáo nào về X?") is never swallowed into a THINKING_OVERVIEW or
        # misrouted by the regex first-match-wins router. The keyword router
        # remains as a deterministic fast-path / validation layer: strong
        # structural intents (term linkage, count, lineage, owner, domain lists)
        # are preserved, and the LLM plan only overrides weak/ambiguous regex
        # intents (guarded by ``llm_intent_override``).
        llm_plan = None
        if (not resolution.framed
                and settings.INTENT_CLASSIFIER_ENABLED
                and not settings.USE_MOCK_LLM
                and intent_classifier.needs_semantic(query, intent.value)):
            llm_plan = await intent_classifier.classify(query, self._ctx.llm)
            if llm_plan is not None:
                override = intent_classifier.llm_intent_override(
                    intent.value, llm_plan, query,
                    has_field_identifier=_extract_field_identifier(query) is not None,
                )
                if override is not None and override != intent.value:
                    log.info("route_llm_intent_override", trace_id=trace_id,
                             question=query[:100], regex_intent=intent.value,
                             llm_intent=override, confidence=llm_plan.confidence)
                    intent = QueryIntent(override)
                # R1: the LLM plan is the primary request understanding. Keep it
                # as the active plan so downstream impact detection, planner and
                # response relabeling run on the LLM's contract, never on the
                # regex first-match-wins fallback.
                plan = llm_plan

        # R2b — Field-location reroute. "warehouse_id nằm trong những dataset
        # nào?", "X liên kết với bảng nào qua trường Y?" ask WHERE a column
        # lives. A FIND_ENTITY/GENERAL intent would answer with one unrelated
        # entity ("Báo cáo số tồn kho") instead of the listing of every dataset
        # carrying the field. Force SCHEMA_LOOKUP so the deterministic
        # field-location branch runs (resolve_field_lookup + listing render).
        if (not _ctx_followup
                and intent in (QueryIntent.FIND_ENTITY, QueryIntent.GENERAL,
                               QueryIntent.ENTITY_EXISTS, QueryIntent.SCHEMA_LOOKUP,
                               QueryIntent.TERM_DEFINITION, QueryIntent.TERM_TO_DATASETS)
                and _is_field_location_question(query)):
            intent = QueryIntent.SCHEMA_LOOKUP
            log.info("route_field_location", trace_id=trace_id,
                     question=query[:100], intent=QueryIntent.SCHEMA_LOOKUP.value)
        # R2e — Schema-and-Owner composite reroute. "cấu trúc schema của X và ai sở hữu?"
        # asks for both schema and ownership. Route to SCHEMA_LOOKUP so schema is rendered
        # and owner is appended deterministically.
        if (intent in (QueryIntent.OWNER_LOOKUP, QueryIntent.FIND_ENTITY, QueryIntent.GENERAL)
                and re.search(r"schema|cấu trúc|cau truc|cột|cot|các trường|cac truong", query, re.I)):
            intent = QueryIntent.SCHEMA_LOOKUP
            log.info("route_schema_owner_composite", trace_id=trace_id,
                     question=query[:100], intent=QueryIntent.SCHEMA_LOOKUP.value)

        # R2c — Term-to-datasets reroute. "tìm dataset tính/chứa/lưu <term>?"
        # asks which datasets carry a business concept (a glossary term). The
        # SCHEMA_LOOKUP/FIND_ENTITY flow would canonicalize the sentence into an
        # unrelated entity ("SA-Term" + field "ch"). When the concept after the
        # ask resolves to a glossary term, route TERM_TO_DATASETS so the
        # linked-datasets flow answers deterministically. Field-location asks
        # are excluded (their fields, not terms). Column-meaning asks are safe:
        # "trường X nghĩa là gì" never carries a dataset-ask verb so the pattern
        # below cannot match them.
        if (not _ctx_followup
                and intent in (QueryIntent.FIND_ENTITY, QueryIntent.GENERAL,
                               QueryIntent.ENTITY_EXISTS, QueryIntent.SCHEMA_LOOKUP,
                               QueryIntent.TERM_DEFINITION)
                and not _is_field_location_question(query)
                and _TERM_TO_DATASETS_ASK_RE.search(query)):
            _concept = _TERM_TO_DATASETS_ASK_RE.sub("", query).strip().rstrip("?")
            _concept = re.sub(
                r"^(?:tìm|tim|cho|hãy|hay)\s*", "", _concept
            ).strip()
            _concept = re.split(
                r",|\bcho biết\b|\bcho biet\b|\bvà term\b|\bva term\b|\b"
                r"liên quan\b|\blien quan\b",
                _concept,
            )[0].strip()
            _concept = re.sub(
                r"\s+(?:và|va|nào|nao|định nghĩa|dinh nghia)$",
                "", _concept,
            ).strip()
            # R2c is about "which datasets carry term X?" ("dataset nào
            # tính/chứa/lưu doanh thu?"). An identify-by-description ask
            # ("bảng tính dự báo cung cấp hàng tuần theo từng part là dataset
            # nào?") names a report/table the user wants matched to a dataset -
            # the leftover is sentence description ("dự báo cung cấp hàng
            # tuần theo từng part") that would falsely resolve to an unrelated
            # glossary term ("CUNG ỨNG"). Those asks end in "X là dataset
            # nào/bảng nào" and must fall through to description discovery.
            if re.search(
                r"(?:là|la)\s+(?:dataset|bảng|bang|báo cáo|bao cao|report)"
                r"(?:\s+(?:nào|nao|gì|gi))?\s*[?!.]?$",
                _concept, re.I,
            ):
                _concept = ""
            if _concept:
                # R2c applies only to discovery asks that do NOT name a
                # concrete dataset ("dataset FCT_DMS_VEHICLE_INVENTORY lưu
                # trữ..."). A named dataset is a dataset-facts ask; the
                # "concept" leftover after stripping would be sentence noise
                # ("trữ dữ liệu gì? Cho biết các trường chính"). Only a token
                # that looks like an identifier (contains "_" or ".") counts -
                # "dataset tính nhu cầu..." has a verb, not a name.
                if not re.search(
                    r"\b(?:dataset|bảng|bang|báo cáo|bao cao)\s+"
                    r"[\"“”'`]?[A-Za-zÀ-ỹ_][\wÀ-ỹ_.-]*[_.][\wÀ-ỹ_.-]*",
                    query, re.I,
                ):
                    try:
                        _t_hits = await self._entities.resolve_glossary_by_concept(
                            _concept, question=query, trace_id=trace_id)
                        if not _t_hits:
                            _t_hits = await self._entities.resolve_glossary_by_alias(
                                _concept, question=query, trace_id=trace_id)
                    except Exception:  # noqa: BLE001
                        _t_hits = []
                    if _t_hits:
                        log.info("route_term_to_datasets_ask", trace_id=trace_id,
                                 question=query[:100], concept=_concept,
                                 term=_t_hits[0].name)
                        intent = QueryIntent.TERM_TO_DATASETS
                        if plan:
                            plan.intent = QueryIntent.TERM_TO_DATASETS

        # R2d — Discovery-phrasing reroute. "có báo cáo nào về chi phí bảo hành do
        # lỗi nhà cung cấp...?" is a description-based discovery ask (what
        # exists in the catalog). The LLM classifier is unstable here: it can
        # pick SCHEMA_LOOKUP (which then abstains "I couldn't find"). Force
        # FIND_ENTITY so the deterministic discovery listing answers from the
        # retrieved candidates. Field-location and column-meaning asks are
        # excluded - they are schema questions, not existence listings.
        if (intent == QueryIntent.SCHEMA_LOOKUP and not _ctx_followup
                and not _is_field_location_question(query)
                and not _is_column_meaning_question(query)
                and re.search(
                    r"\b(?:có|co)\s+(?:báo cáo|bao cao|report|dataset|bảng|bang|"
                    r"dashboard)\s+nào\s+về\b|"
                    r"\bnào\s+liên quan đến\b",
                    query, re.I,
                )):
            intent = QueryIntent.FIND_ENTITY
            log.info("route_discovery_phrasing", trace_id=trace_id,
                     question=query[:100], intent=QueryIntent.FIND_ENTITY.value)

        # R3 — Glossary-alias guard. Users reference catalog terms by their
        # English parenthetical alias ("Demand là gì?", "so sánh Demand giữa
        # SẢN XUẤT và KINH DOANH"). Such questions often land on GENERAL (they
        # carry comparison / selection phrasing) and would be swallowed by the
        # thinking layer, which returns a THINKING_OVERVIEW with no term entity.
        # When the question resolves to a glossary term by alias and names no
        # dataset / dashboard / report, force the TERM_DEFINITION flow so the
        # structured glossary path returns the term.
        if intent == QueryIntent.GENERAL and not _ctx_followup \
                and not re.search(
                    r"\b(dataset|bảng|bang|dashboard|report|báo cáo|bao cao)\b",
                    query, re.IGNORECASE):
            try:
                _alias_hits = await self._entities.resolve_glossary_by_alias(
                    query, question=query, trace_id=trace_id)
            except Exception:  # noqa: BLE001
                log.exception("glossary_alias_guard_failed", trace_id=trace_id,
                              question=query[:100])
                _alias_hits = []
            if _alias_hits:
                log.info("route_glossary_alias", trace_id=trace_id,
                         question=query[:100],
                         intent=QueryIntent.TERM_DEFINITION.value)
                intent = QueryIntent.TERM_DEFINITION

        # R3 — Formula-of-column guard. "công thức tính của column X?" asks for
        # the business formula of a column / metric. The formula (and KPI
        # definition) lives in the glossary TERM named X ("Coverage Date" ->
        # "Coverage Date = (Số ngày làm việc từ Stock Date → Last Day Cover) - 2").
        # SCHEMA_LOOKUP canonicalizes "column Coverage Date" into an unrelated
        # dataset and answers "no formula". When the question names a column with
        # a formula/definition ask and the column name resolves to a glossary
        # term, force TERM_DEFINITION so the deterministic term answer returns
        # the grounded formula instead of a schema-lookup miss.
        if intent == QueryIntent.SCHEMA_LOOKUP and not _ctx_followup:
            # A field-location question ("dataset nào chứa trường X?") asks WHERE
            # the column lives - the SCHEMA_LOOKUP listing answers it. The column
            # token must not be hijacked into a glossary-term formula resolution.
            if _is_field_location_question(query):
                pass
            # A column-MEANING question ("trường X nghĩa là gì?") asks the
            # field's meaning inside its dataset - answered by SCHEMA_LOOKUP's
            # column-definition branch, not by the glossary formula resolver.
            if _is_column_meaning_question(query):
                pass
            # Only actual formula asks ("công thức/cách tính/formula của X")
            # route the column to the glossary-term formula resolution.
            elif not re.search(
                r"công thức|cong thuc|formula|cách tính|cach tinh|cách",
                query, re.I,
            ):
                pass
            else:
                _col = None
                _cm = re.search(
                    r"\b(?:column|trường|truong|cột|cot|field|metric)\b[^\n]{0,10}?"
                    r"[\"“”'`]?(?P<col>[A-Za-zÀ-ỹ][A-Za-z0-9À-ỹ _\.\-]{1,50})[\"“”'`]?",
                    query, re.IGNORECASE,
                )
                if _cm:
                    _col = _cm.group("col").strip()
                else:
                    # Connector path: "công thức tính của X" / "formula của X" names the
                    # metric right after the connector. Cap the capture at sentence end
                    # and trim trailing filler so "của column Coverage Date." is not
                    # swallowed into the name.
                    _fm = re.search(
                        r"(?:công thức|cong thuc|formula|cách tính|cach tinh)[^\n]{0,25}?"
                        r"(?:của|cua|cho|tính|tinh)\s*"
                        r"(?:column|trường|truong|cột|cot|field|metric)?\s*"
                        r"[\"“”'`]?(?P<col>[A-Za-zÀ-ỹ][A-Za-z0-9À-ỹ _\.\-]{1,50})[\"“”'`]?",
                        query, re.IGNORECASE,
                    )
                    if _fm:
                        _col = _fm.group("col").strip()
                        _col = re.sub(r"\s+(?:của|cua|cho|trong|và|va|nào|nao)$", "", _col).strip()
                if _col:
                    try:
                        _col_term = await self._entities.resolve_with_expansion(
                            _col, query,
                            entity_type="glossary_term", trace_id=trace_id)
                    except Exception:  # noqa: BLE001
                        log.exception("formula_column_guard_failed", trace_id=trace_id,
                                      question=query[:100])
                        _col_term = None
                    if _col_term and _trusted_resolution(_col_term):
                        log.info("route_formula_column", trace_id=trace_id,
                                 question=query[:100], column=_col,
                                 intent=QueryIntent.TERM_DEFINITION.value)
                        intent = QueryIntent.TERM_DEFINITION

        _is_multihop_or_formula = bool(
            re.search(
                r"từ báo cáo|tu bao cao|công thức|cong thuc|nguồn dữ liệu|nguon du lieu|lineage|lấy từ đâu|lay tu dau|tính như thế nào|tinh nhu the nao",
                _norm_vn(query),
                re.I,
            )
        )
        if settings.THINKING_MODE_ENABLED and intent == QueryIntent.GENERAL \
                and not _ctx_followup and not _is_multihop_or_formula:

            _complex = bool(
                understanding is not None and understanding.needs_thinking
            )
            if not _complex:
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

        # Comparison: "so sánh A và B về schema, lineage, quality"
        # Extract ALL entities, resolve each independently, retrieve metadata
        # for each, then compare and generate a structured answer.
        if intent == QueryIntent.COMPARISON or resolution.chosen_tool == "comparison":
            from retrieval.query_parser import _extract_all_entities
            all_entity_names = _extract_all_entities(query)
            if len(all_entity_names) >= 2:
                comparison_response = await self._comparison_flow(
                    query, all_entity_names, user_ctx, trace_id, cid,
                    on_token=on_token, on_status=_emit,
                )
                if comparison_response is not None:
                    if selected_action and not comparison_response.selected_action:
                        comparison_response.selected_action = selected_action
                    await self._ctx.memory.add_turn_db(
                        self._ctx.session, uid, cid, query,
                        comparison_response.answer,
                    )
                    await _emit("done")
                    return comparison_response

        # SQL Generation: when the intent resolver picked the sql_generator tool
        # (explicit "Generate SQL" action, or a field/query request like
        # "truy vấn ... warehouse_id"), run the field-aware SQL pipeline instead
        # of generic entity search. An explicitly selected action always wins.
        if resolution.chosen_tool == "sql_generator" or intent == QueryIntent.SQL_GENERATION:
            sql_response = await self._flows.sql_generation_flow(
                query, user_ctx, trace_id, cid, entity_hint,
            )
            if sql_response is not None:
                if selected_action and not sql_response.selected_action:
                    sql_response.selected_action = selected_action
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
                if selected_action and not sync_response.selected_action:
                    sync_response.selected_action = selected_action
                await _emit("done")
                return sync_response

        # Data Quality Check: an explicit "quality" action, or a framed dataset
        # quality request, runs the deterministic quality report against DataHub
        # metadata and returns it as a rendered markdown answer plus the structured
        # report (carried on ChatResponse.quality_report) for the chat export UI.
        if resolution.chosen_tool == "quality_check" or selected_action == "quality" or (
            selected_action == "quality" and intent in _QUALITY_FAVORED_INTENTS
        ):
            quality_response = await self._flows.quality_check_flow(
                query, user_ctx, trace_id, cid, entity_hint,
            )
            if quality_response is not None:
                if selected_action and not quality_response.selected_action:
                    quality_response.selected_action = selected_action
                await _emit("done")
                return quality_response
            if selected_action == "quality":
                fallback_msg = (
                    "Tôi cần biết bạn muốn kiểm tra chất lượng cho thực thể nào. "
                    "Vui lòng nhập tên dataset hoặc dashboard (ví dụ: PVB QDAT, Dim_BaoCaoLayout)."
                )
                await _emit("done")
                return ChatResponse(
                    answer=fallback_msg, intent="QUALITY_CHECK", confidence="high",
                    ambiguous=False, insufficient_context=True, selected_action="quality",
                    trace_id=trace_id, conversation_id=cid,
                )

        # Metadata Report: an explicit "report" action or chosen_tool == "metadata_report"
        # or question explicitly requesting a metadata report.
        if (
            resolution.chosen_tool == "metadata_report"
            or selected_action == "report"
            or intent == QueryIntent.METADATA_REPORT
            or (_METADATA_REPORT_RE.search(query) and not is_ellipsis)
        ):
            report_response = await self._flows.metadata_report_flow(
                query, user_ctx, trace_id, cid, entity_hint,
            )
            if report_response is not None:
                if selected_action and not report_response.selected_action:
                    report_response.selected_action = selected_action
                await _emit("done")
                return report_response
            if selected_action == "report":
                fallback_msg = (
                    "Tôi cần biết bạn muốn tạo metadata report cho thực thể nào. "
                    "Vui lòng nhập tên dataset hoặc dashboard (ví dụ: PVB QDAT, Dim_BaoCaoLayout)."
                )
                await _emit("done")
                return ChatResponse(
                    answer=fallback_msg, intent="METADATA_REPORT", confidence="high",
                    ambiguous=False, insufficient_context=True, selected_action="report",
                    trace_id=trace_id, conversation_id=cid,
                )

        # How-to / System guidance questions without an explicit entity name:
        # answer conversationally / guide user how to use DataHub capabilities instead of searching random entities.
        if (intent == QueryIntent.GENERAL and not resolution.framed
                and re.search(r"^(?:làm thế nào|lam the nao|làm sao|lam sao|hướng dẫn|huong dan|cách nào|cach nao|như thế nào|nhu the nao|bằng cách nào|bang cach nao)\b", _norm_vn(query), re.I)
                and not _has_own_identifier(query)):
            log.info("route_howto_guidance", trace_id=trace_id, question=query[:100])
            await _emit("generate")
            answer_text = await generator.generate_conversational(query, on_token=on_token)
            if not answer_text or len(answer_text.strip()) < 10:
                answer_text = (
                    "Để sử dụng các tính năng tra cứu trên DataHub AI Chatbot:\n\n"
                    "1. **Tra cứu Lineage:** Bạn có thể nhập cú pháp `Lineage của dataset <tên_bảng>` (ví dụ: `Lineage của dataset PVB QDAT`) hoặc chọn chức năng **Data Lineage** trên giao diện.\n"
                    "2. **Kiểm tra chất lượng metadata:** Bạn có thể chọn chức năng **Quality Check** hoặc hỏi `Kiểm tra chất lượng metadata của dataset <tên_bảng>` để xem báo cáo đánh giá 8 tiêu chí chất lượng.\n"
                    "3. **Tra cứu Schema & Owner:** Bạn có thể hỏi trực tiếp như `Cấu trúc schema của bảng <tên_bảng> và ai là người sở hữu?`."
                )
            await self._ctx.memory.add_turn_db(self._ctx.session, uid, cid, question, answer_text)
            await _emit("done")
            return ChatResponse(
                answer=answer_text, intent="HOW_TO", confidence="high",
                ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

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

        # Generic metadata listing: "dataset nào có lineage?", "dataset nào không có owner?"
        # Skip if intent is already a known listing/count intent (handled by existing flow)
        if intent not in _DETERMINISTIC_LISTING_INTENTS:
            metadata_listing = await self._try_metadata_listing(
                query, user_ctx, trace_id, cid, _t_start=_t_start
            )

            if metadata_listing is not None:
                return metadata_listing

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
            lines = [f"Có tổng cộng {count} {entity_type_label} trong hệ thống.\n"]
            for plat, names in sorted(platforms.items()):
                sample = sorted(names)
                lines.append(f"**{plat}:**")
                for name in sample[:15]:
                    lines.append(f"- {name}")
                if len(sample) > 15:
                    lines.append(f"- ... và {len(sample) - 15} {entity_type_label} khác")
                lines.append("")
            answer_text = mask_secrets("\n".join(lines).strip())

            entity_list = []
            for e in entities:
                entity_list.append(
                EntityItem(
                    urn=e.urn, name=e.display_name or e.name, url=e.datahub_url,
                    entity_type=e.entity_type, platform=e.platform, domain=e.domain,
                    description=e.description, environment=e.environment,
                )
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
        # only ambiguous cases. The R1 LLM-first gate above already ran the
        # classifier when eligible, so skip the duplicate LLM call.
        if plan is None:
            plan = intent_classifier.regex_plan(query)
        if (llm_plan is None
                and not resolution.framed
                and intent_classifier.needs_semantic(query, intent.value)
                and settings.INTENT_CLASSIFIER_ENABLED
                and not settings.USE_MOCK_LLM):
            plan = await intent_classifier.classify(query, self._ctx.llm)
        impact_mode = plan.intent == "IMPACT"

        # Domain-constrained discovery: "chỉ nêu ... domain TÀI CHÍNH về giá
        # thành/ngân sách" asks for a filtered listing, not an ambiguous pick.
        if not impact_mode:
            _dcd = await self._listing.domain_constrained_discovery(
                query, trace_id, cid,
            )
            if _dcd is not None:
                await self._ctx.memory.add_turn_db(
                    self._ctx.session, uid, cid, query, _dcd.answer,
                )
                return _dcd

        # Query-planner path: plans with explicit executable steps (composite /
        # LLM-planned multi-step questions) go through the DAG tool orchestrator
        # (parallel branches + retries). Single-intent plans keep the direct
        # structured path below for lower latency.
        #
        # Query-Understanding decomposition: when the LLM reads the question as
        # several independent sub-questions and no plan steps exist yet, build a
        # composite plan so the DAG executor resolves each sub-question's entity
        # in parallel branches instead of one generic search.
        if (understanding is not None and understanding.needs_decomposition
                and understanding.sub_questions and not plan.steps):
            from retrieval.query_models import PlanStep
            _qu_steps: list[PlanStep] = []
            for _sq in understanding.sub_questions:
                _sq_name = intent_classifier.regex_plan(_sq).primary_entity
                if _sq_name:
                    _qu_steps.append(PlanStep(
                        op="resolve_entity", params={"name": _sq_name},
                        purpose=f"query understanding sub-question: {_sq[:80]}",
                    ))
            if _qu_steps:
                from retrieval.query_models import QueryPlan
                plan = QueryPlan(
                    intent="COMPOSITE_QUERY",
                    entity_refs=list(dict.fromkeys(
                        (p.params or {}).get("name", "") for p in _qu_steps
                    )),
                    entity_type=plan.entity_type,
                    filter=plan.filter,
                    direction=plan.direction,
                    confidence="medium",
                    steps=_qu_steps,
                    source="query_understanding",
                )
                log.info("query_understanding_decompose", trace_id=trace_id,
                         question=query[:100],
                         sub_questions=len(understanding.sub_questions),
                         steps=len(_qu_steps))

        _t0 = time.perf_counter()
        planner_results: list[SearchResult] = []
        # Deterministic two-dataset schema analysis (join keys / common fields
        # between X and Y, "field join với Z là gì") supersedes the generic DAG
        # entity-resolution: it must report the REAL shared column names, not
        # whatever single entity the planner happened to resolve first.
        if (settings.QUERY_PLANNER_ENABLED
                and (plan.steps or plan.intent in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY"))
                and _looks_like_join(query)):
            join_results = await self._retrieval.schema_join_lookup(
                query, trace_id=trace_id,
            )
            if join_results:
                planner_results = join_results
                intent = QueryIntent.SCHEMA_LOOKUP
                log.info("route_planner_dag", trace_id=trace_id,
                         question=query[:100], intent=plan.intent,
                         steps=len(plan.steps), result_count=len(join_results),
                         mode="schema_join")
        if (settings.QUERY_PLANNER_ENABLED
                and (plan.steps or plan.intent in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY"))
                and not planner_results):
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
                    # Strip the entity-kind noun that precedes the name so
                    # "còn bảng fact_part_movement thì sao?" / "còn trường
                    # warehouse_id thì sao?" resolve "fact_part_movement" /
                    # "warehouse_id" — never a literal "bang ..." identifier.
                    entity_from_q = re.sub(
                        r"^(?:bảng|bang|table|dataset|trường|truong|field|"
                        r"cột|cot|các|cac|những|nhung)\s+",
                        "", entity_from_q,
                    ).strip()
                    inferred_entity = entity_from_q if entity_from_q else None
                    inferred_type: str | None = None
                else:
                    inferred_entity, inferred_type = await self._entities.resolve_followup_entity(
                        uid, cid, query, history, active_entities,
                    )
                # QU rescue: when the coreference pipeline could not bind the
                # pronoun/demonstrative to an earlier-turn entity, trust the
                # LLM's anaphora target for this conversation (never invented).
                if (not inferred_entity and understanding is not None
                        and understanding.anaphora_target):
                    inferred_entity = understanding.anaphora_target
                    log.info("route_qu_anaphora", trace_id=trace_id,
                             question=query[:100], target=inferred_entity)
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
                    # Bare-ellipsis follow-ups ("còn X thì sao?") must NOT run
                    # under the fresh intent the keyword router assigned to the
                    # raw sentence ("còn bảng fact_part_movement thì sao" ->
                    # LINEAGE). They inherit the PREVIOUS turn's tool instead
                    # (the else branch below), so "thì sao" after a schema fetch
                    # re-retrieves the new entity's schema, not its lineage.
                    if intent in (QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
                                  QueryIntent.ENTITY_DOMAIN,
                                  QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
                                  QueryIntent.SCHEMA_LOOKUP, QueryIntent.DATAHUB_URL,
                                  QueryIntent.ENTITY_EXISTS, QueryIntent.DOMAIN_QUERY,
                                  QueryIntent.PLATFORM_QUERY, QueryIntent.TAG_QUERY,
                                  QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST) \
                            and not is_ellipsis:
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
                    acl_filter = None
                    if self._ctx.auth_service:
                        acl_filter = await self._ctx.auth_service.build_opensearch_acl_filter(user_ctx)
                    results = await self._ctx.hybrid_search.search(query, trace_id=trace_id, acl_filter=acl_filter)
                log.info("route_hybrid", trace_id=trace_id, question=query[:100],
                         intent=intent.value, result_count=len(results))

                # Multi-hop question expansion (e.g. report + lineage + formula)
                if results and re.search(r"nguồn dữ liệu|nguon du lieu|lấy từ đâu|lay tu dau|lineage|upstream|nguồn gốc|nguon goc", query, re.I):
                    from retrieval.hybrid_search import _entity_payload_to_text
                    for r in list(results):
                        entity_db = await self._ctx.entity_repo.get_by_urn(r.urn)
                        if entity_db:
                            upstreams = list(entity_db.payload.get("upstreams") or [])
                            if not upstreams:
                                try:
                                    up = await self._ctx.source.get_lineage(entity_db.urn, direction="upstream")
                                    upstreams = [rel["entity"]["urn"] for rel in up.get("relationships", []) if (rel.get("entity") or {}).get("urn")]
                                except Exception:
                                    pass
                            for u in upstreams:
                                rel_ent = await self._ctx.entity_repo.get_by_urn(u)
                                if rel_ent and not any(res.urn == u for res in results):
                                    name = (rel_ent.display_name or rel_ent.name)
                                    content = _entity_payload_to_text(rel_ent.entity_type, rel_ent.payload or {})
                                    results.append(SearchResult(
                                        urn=rel_ent.urn, entity_type=rel_ent.entity_type,
                                        name=name, score=0.85, datahub_url=rel_ent.datahub_url,
                                        payload={"content": f"Nguồn dữ liệu đầu vào (Upstream raw data): {content}"},
                                    ))

                if results and re.search(r"công thức|cong thuc|cách tính|cach tinh|formula|coverage date", query, re.I):
                    _f_id = _extract_field_identifier(query)
                    if _f_id:
                        g_res = await self._ctx.entity_resolver.resolve(_f_id, entity_type="glossary_term", trace_id=trace_id)
                        if g_res.candidates:
                            g_results = await self._ctx.entities.resolve_all_exact_to_results(g_res, trace_id=trace_id)
                            for gr in g_results:
                                if not any(res.urn == gr.urn for res in results):
                                    results.append(gr)


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
                if extracted and not _is_noisy_entity(extracted):
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
                if value and value not in _ANAPHORA_WORDS and not _is_noisy_entity(value):
                    suggestion = await self._entities.suggest_entity(value, None, query, trace_id)
            elif intent in (QueryIntent.LINEAGE, QueryIntent.OWNER_LOOKUP,
                            QueryIntent.ENTITY_DOMAIN, QueryIntent.SCHEMA_LOOKUP,
                            QueryIntent.TERM_TO_DATASETS, QueryIntent.ENTITY_EXISTS):
                # A picked function (Data Lineage, quality, …) with no matching
                # entity -> friendly, grounded "not found" answer ONLY when a clean
                # non-noisy entity name was explicitly extracted.
                extracted = _extract_name(query, _TERM_REMOVE_WORDS)
                if extracted and not _is_noisy_entity(extracted) and extracted not in _ANAPHORA_WORDS:
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
                    _processing_ms = int((time.perf_counter() - _t_start) * 1000)
                    await self._log_interaction_async("response",
                        trace_id=trace_id, answer=not_found, intent=intent.value,
                        confidence="high", processing_time_ms=_processing_ms,
                        entity_hint=extracted,
                        resolution_state="not_found",
                    )
                    return ChatResponse(
                        answer=not_found, intent=intent.value, confidence="high",
                        ambiguous=False, insufficient_context=False,
                        trace_id=trace_id, conversation_id=cid,
                    )
            if suggestion is not None and not _is_noisy_entity(getattr(suggestion, "original", "")):
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
                _processing_ms = int((time.perf_counter() - _t_start) * 1000)
                await self._log_interaction_async("response",
                    trace_id=trace_id, answer=answer_text, intent=intent.value,
                    confidence="high", processing_time_ms=_processing_ms,
                    entity_hint=suggestion.original,
                    entity_resolved_name=suggestion.suggested,
                    resolution_state="suggested",
                )
                return ChatResponse(
                    answer=answer_text, intent=intent.value, confidence="high",
                    ambiguous=False, insufficient_context=False,
                    trace_id=trace_id, conversation_id=cid,
                    suggestion=suggestion,
                )

        # Fallback to hybrid search if structured retrieval yielded no results
        # for a natural language or complex multi-hop question.
        if not results:
            acl_filter = None
            if self._ctx.auth_service:
                acl_filter = await self._ctx.auth_service.build_opensearch_acl_filter(user_ctx)
            results = await self._ctx.hybrid_search.search(query, trace_id=trace_id, acl_filter=acl_filter)
            log.info("route_hybrid_fallback", trace_id=trace_id, question=query[:100],
                     intent=intent.value, result_count=len(results))


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

            results_domain_filtered = await self._ctx.auth_service.filter_results_by_domain(
                user_ctx, results, _result_domain
            )
            accessible = await self._ctx.auth_service.filter_accessible_urns(
                user_ctx, [r.urn for r in results_domain_filtered]
            )

            # Audit denied access:
            for r in results:
                if r.urn not in accessible:
                    await self._ctx.auth_service.can_view_entity(user_ctx, r.urn)

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
        # ask a clarification instead of randomly choosing one. Multi-entity
        # questions ("so sánh giữa A và B", schema-join analysis) legitimately
        # produce several results with near-equal scores - those are the answer,
        # not ambiguity, so they must skip the clarification.
        #
        # Decision-aware gate: several common multi-candidate cases are NOT real
        # ambiguity and must resolve instead of clarify:
        #  (1) every candidate carries the SAME display name ("Coverage Date"
        #      resolving to two same-named terms, "fact_sale_orders" on several
        #      platforms). Repeating one name three times in a clarify is noise -
        #      the answer is to ground on every same-named candidate / the top one.
        #  (2) description-based discovery (FIND_ENTITY: "có báo cáo nào về X?")
        #      asks what exists; the top candidate + caveat IS the answer.
        #  (3) field-location questions ("dataset nào chứa trường X?") ask for a
        #      listing; the top-N datasets containing the field are the answer.
        _multi_entity_join = any(
            (r.payload or {}).get("join_analysis") for r in results
        )
        _distinct_names = {
            (r.name or "").strip().lower() for r in results if (r.name or "").strip()
        }
        _same_name_tie = bool(
            len(results) > 1
            and len(_distinct_names) == 1
            and all((r.name or "").strip() for r in results[:4])
        )
        _field_location_question = (
            intent in (QueryIntent.SCHEMA_LOOKUP, QueryIntent.TERM_DEFINITION)
            and _is_field_location_question(question_for_gen)
        )
        _term_in_dataset_question = (
            intent == QueryIntent.TERM_DEFINITION
            and _is_term_in_dataset_question(question_for_gen)
        )
        _concept_family_question = bool(
            intent == QueryIntent.TERM_DEFINITION
            and any(
                k in _norm_vn(question_for_gen)
                for kws in _GLOSSARY_CONCEPT_KEYWORDS.values()
                for k in kws
            )
        )
        _is_formula_question = bool(
            re.search(
                r"công thức|cong thuc|cách tính|cach tinh|formula|tính như thế nào|tinh nhu the nao|tính bằng gì|tinh bang gi|được tính|duoc tinh",
                _norm_vn(question_for_gen),
                re.I,
            )
        )
        ambiguous = (
            len(results) > 1
            and not _multi_entity_join
            and not _same_name_tie
            and not _field_location_question
            and not _term_in_dataset_question
            and not _concept_family_question
            and not _is_formula_question
            and intent != QueryIntent.FIND_ENTITY
            and abs(results[0].score - results[1].score) < 0.15
            and results[1].score > 0.5
        )

        if _same_name_tie:
            # Collapse same-named datasets to a single representative (they are
            # the same table mirrored on several platforms). Same-named glossary
            # terms are kept as-is: E-001/L-001 expect every definition.
            _seen_names: set[str] = set()
            _deduped: list[SearchResult] = []
            for _r in results:
                _key = ((_r.name or "").strip().lower(),
                        (_r.payload or {}).get("entity_type") or _r.entity_type)
                if _r.entity_type == "glossary_term" or _key not in _seen_names:
                    _seen_names.add(_key)
                    _deduped.append(_r)
            results = _deduped
            log.info("chat_same_name_tie_resolved", trace_id=trace_id,
                     intent=intent.value, deduped=len(results),
                     question=question_for_gen[:100], conversation_id=cid)
        if ambiguous and intent in _AMBIGUOUS_CLARIFY_INTENTS:
            options = " hoặc ".join(f"'{r.name}'" for r in results[:3])
            clarification = (
                f"Có nhiều entity trùng khớp với yêu cầu của bạn: {options}. "
                "Bạn muốn hỏi về entity nào?"
            )
            entity_list = [
                EntityItem(
                    urn=r.urn, name=r.name, url=r.datahub_url,
                    entity_type=r.entity_type,
                    platform=(r.payload or {}).get("platform"),
                    domain=(r.payload or {}).get("domain"),
                    description=(r.payload or {}).get("description"),
                    environment=(r.payload or {}).get("environment"),
                )
                for r in results if r.name
            ]
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, question_for_gen, clarification,
            )
            log.info("chat_ambiguous_clarification", trace_id=trace_id, intent=intent.value,
                     top=results[0].name, runner_up=results[1].name, conversation_id=cid)
            _processing_ms = int((time.perf_counter() - _t_start) * 1000)
            await self._log_interaction_async("response",
                trace_id=trace_id, answer=clarification, intent=intent.value,
                confidence="low", ambiguous=True, processing_time_ms=_processing_ms,
                result_count=len(results), entity_resolved_name=results[0].name,
                resolution_state="ambiguous",
            )
            return ChatResponse(
                answer=clarification, intent=intent.value, entities=entity_list,
                confidence="low", ambiguous=True, insufficient_context=False,
                trace_id=trace_id, conversation_id=cid,
            )

        short_answer = None if impact_mode else _short_negative_answer(intent, results, question_for_gen)
        if short_answer is not None:
            entity_list = [
                EntityItem(
                    urn=r.urn, name=r.name, url=r.datahub_url,
                    entity_type=r.entity_type,
                    platform=(r.payload or {}).get("platform"),
                    domain=(r.payload or {}).get("domain"),
                    description=(r.payload or {}).get("description"),
                    environment=(r.payload or {}).get("environment"),
                )
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
        _discovery_phrasing = bool(re.search(
            r"liệt kê|liet ke|danh sách|danh sach|list\b|\bgồm những|gom nhung|"
            r"có những|co nhung|những .{0,20} nào|nhung .{0,20} nao|"
            r"nào về|nao ve|nào là|nao la|có .{0,15} nào|co .{0,15} nao|"
            r"liên quan đến|den ve|staging|thô\b|tho\b|raw\b|nguồn|nguon\b"
            r"|(?:là|la)\s+(?:dataset|bảng|bang|báo cáo|bao cao|report)\s+"
            r"(?:nào|nao|gì|gi)",
            _norm_vn(question_for_gen), re.I,
        ))
        _asked_type = _detect_entity_type(question_for_gen)
        if (intent in (QueryIntent.FIND_ENTITY, QueryIntent.GENERAL)
                and (results or _asked_type) and not impact_mode
                and _discovery_phrasing
                and (intent == QueryIntent.FIND_ENTITY or _asked_type)):
            # Staging/raw ask ("dataset thô (staging) nào chứa dữ liệu X?"):
            # replace the report-view results with the raw stg_* datasets that
            # actually carry the subject (deterministic schema scan).
            if re.search(
                r"\bthô\b|tho\b|staging|raw\b|nguồn|nguon\b",
                _norm_vn(question_for_gen), re.I,
            ):
                _stg_results = await self._retrieval.resolve_staging_datasets(
                    question_for_gen, trace_id)
                if _stg_results:
                    results = _stg_results
            # Discovery re-rank: hybrid search interleaves vector-only matches
            # ("[LOG]...") ABOVE the exact token-matched entities
            # ("Report_Supply_Capacity", "fact_supplier_capacity"). For a
            # listing ask the entities whose NAME shares the question's
            # distinctive tokens are the actual hits - surface them first, then
            # keep the rest of the original ranking.
            # A listing ask that names the wanted type ("còn dashboard nào về
            # PFEP...", "có dataset nào về X?") should surface that type first:
            # the follow-up switches from a glossary term (prior turn) to
            # dashboards/datasets, and the plain ranking would leak the prior
            # turn's glossary terms or unrelated report views into the list.
            if _asked_type:
                _type_rank = lambda r: (  # noqa: E731
                    0 if (r.payload or {}).get("entity_type") == _asked_type
                    or r.entity_type == _asked_type else 1
                )
                results = sorted(results, key=lambda r: (_type_rank(r), -r.score))
                # A listing ask that names the wanted type may still lack that
                # type entirely: the vector path is diluted by the contextual
                # sentence ("còn dashboard nào về PFEP cho nhà máy khác?") and
                # the strict token-discovery threshold (>=3.0 hits) drops a
                # single-name-token target ("PFEP" dashboards = 2.0). Supplement
                # with a permissive, type-scoped token search so the ask's type
                # is actually represented.
                from retrieval.discovery import TokenDiscovery
                from retrieval.hybrid_search import _entity_payload_to_text
                _supp = await TokenDiscovery(
                    self._ctx.entity_repo).discover(
                    question_for_gen, top_k=6, min_hits=2.0,
                    entity_types=(_asked_type,), trace_id=trace_id)
                _have_urns = {r.urn for r in results}
                _extra = []
                for _e in _supp:
                    if _e.urn in _have_urns:
                        continue
                    _have_urns.add(_e.urn)
                    _payload = dict(_e.payload or {})
                    _payload.setdefault(
                        "content", _entity_payload_to_text(
                            _e.entity_type, _payload))
                    _extra.append(SearchResult(
                        urn=_e.urn, entity_type=_e.entity_type,
                        name=_e.display_name or _e.name, score=1.0,
                        datahub_url=_e.datahub_url, payload=_payload))
                results = _extra + results
            _q_words = {
                w for w in re.findall(
                    r"[a-z0-9]{4,}", _norm_vn(question_for_gen))
                if w not in {"cong", "biet", "khong", "giua", "nhan", "trach"}
            }
            # A Vietnamese description ("dự báo cung cấp hàng tuần theo từng
            # part") names a technical entity whose NAME is in English tokens
            # ("rpt_survey_weekly_supply_capacity"). The token expansion maps
            # the Vietnamese phrase onto those tokens ("cung cấp hàng tuần" ->
            # "weekly supply", "dự báo" -> "forecast/survey"); include them so
            # the exact technical target surfaces instead of unrelated
            # Vietnamese-named reports sharing a word.
            from retrieval.discovery import expand_query_tokens
            _q_tokens = expand_query_tokens(question_for_gen)
            _expanded = {
                w for w in " ".join(_q_tokens).replace("_", " ").lower().split()
                if len(w) >= 4
            }
            _q_words |= _expanded
            if _q_words:
                _hit_name = lambda r: sum(  # noqa: E731
                    1 for w in _q_words
                    if w in _norm_vn(r.name or "")
                )
                _scored = sorted(
                    results, key=lambda r: (-_hit_name(r), -r.score))
                results = _scored
            # Discovery / listing questions ("liệt kê ... về X", "có báo cáo
            # nào về X?") ask what exists in the catalog. The retrieval already
            # found the relevant entities; list them deterministically. Letting
            # the LLM judge "relevance" here is what made it abstain with
            # NO_EVIDENCE_RESPONSE ("I couldn't find this information") even
            # when real warranty/defect datasets were retrieved.
            _fe = []
            _seen_fe: set[str] = set()
            for _r in results[:8]:
                _pl = _r.payload or {}
                _t = (_pl.get("entity_type") or _r.entity_type or "").strip()
                _n = _r.name or ""
                _key = (_n.lower(), _t)
                if not _n or _key in _seen_fe:
                    continue
                _seen_fe.add(_key)
                _plat = (_pl.get("platform") or "").strip()
                _bit = f"- **{_n}**"
                _parts = []
                if _t:
                    _parts.append(_t)
                if _plat:
                    _parts.append(f"nền tảng {_plat}")
                if _parts:
                    _bit += f" ({', '.join(_parts)})"
                _fe.append(_bit)
            if _fe:
                answer_text = (
                    "Các entity trong metadata DataHub liên quan đến yêu cầu "
                    f"của bạn:\n\n{chr(10).join(_fe)}"
                    + (
                        "\n\nCó thể còn nhiều entity liên quan khác trong metadata."
                        if len(results) > 8 else ""
                    )
                )
                citations = []
                docs, context_xml = build_context(results)
                confidence = "high"
                if on_token:
                    await on_token(answer_text)
                log.info("find_entity_deterministic", trace_id=trace_id,
                         entity_count=len(_fe), question=question_for_gen[:100],
                         conversation_id=cid)
        elif intent == QueryIntent.LINEAGE and results and not impact_mode:
            # Deterministic answer from the SAME payload that drives the SVG.
            answer_text, citations, lineage_main = await self._lineage.build_lineage_answer(
                results[0],
            )
            docs = []
            context_xml = ""
            confidence = "high"
            if on_token:
                await on_token(answer_text)
        elif intent == QueryIntent.TERM_DEFINITION and results and not impact_mode:
            # Compound term + domain-scoped asset ask ("PFEP là gì và dashboard
            # PFEP nào thuộc domain LOGISTIC?"): after the term answer, also list
            # the dashboards/datasets of the named domain whose name carries the
            # term token. Grounded in the resolved term and real domain metadata.
            _compound_extra = ""
            _asset_compound = re.search(
                r"(?:và|va|cũng như|cung nhu)\s+(?:dashboard|dataset|report|"
                r"báo cáo|bao cao)[^?]{0,30}?"
                r"(?:thuộc|thuoc)\s+(?:domain|lĩnh vực|linh vuc)\s+"
                r"([\wÀ-ỹ]+)",
                question_for_gen, re.I,
            )
            if _asset_compound:
                try:
                    _comp_domain = _asset_compound.group(1).strip().upper()
                    _term0 = next(
                        (r for r in results
                         if (r.payload or {}).get("entity_type") == "glossary_term"),
                        results[0],
                    )
                    _term_tok = ((_term0.name or "").split("(")[0]).strip()
                    _tok = re.split(r"\s+", _term_tok)[0] if _term_tok else ""
                    _assets: list[str] = []
                    _seen_a: set[str] = set()
                    for _d in await self._ctx.entity_repo.list_by_domain(_comp_domain):
                        _dn = _d.display_name or _d.name or ""
                        if not _dn:
                            continue
                        if _tok and _tok.upper() in _dn.upper() and _dn.lower() not in _seen_a:
                            _seen_a.add(_dn.lower())
                            _assets.append(_dn)
                    if _assets:
                        _compound_extra = (
                            f"\n\nTrong domain **{_comp_domain}**, "
                            f"{'dashboard/dataset' if len(_assets) > 1 else 'dashboard/dataset'} "
                            f"liên quan **{_tok}**: {', '.join(_assets)}."
                        )
                except Exception:  # noqa: BLE001
                    log.exception("term_compound_assets_failed", trace_id=trace_id,
                                  question=question_for_gen[:100])
            # Deterministic term answer: a glossary term's own description
            # answers "Term X là gì?" / "Term X trong domain Y" / "so sánh
            # term X giữa ..." directly from the catalog entry. The LLM
            # generator is not needed and, for comparison phrasing, tends to
            # report low confidence. Build the answer from the term metadata so
            # the response is always grounded and high-confidence.
            # Same-named terms ("Coverage Date" x2, "Demand" across domains)
            # legitimately resolve to SEVERAL catalog entries - render EVERY
            # definition (each with its URN) instead of arbitrarily picking the
            # first. A named-dataset compound ("công thức X trong dataset Y")
            # grounds the answer on the dataset too.
            # Concept families ("Demand") are disambiguated by the domain named
            # in the question, or listed in full when no domain is given.
            _dom_scoped = await _domain_scoped_term_answer(
                question_for_gen, self._ctx, results,
            )
            if _dom_scoped:
                answer_text, citations, docs, context_xml, confidence = _dom_scoped
                if on_token:
                    await on_token(answer_text)
            else:
                _term_results = [
                    r for r in results
                    if (r.payload or {}).get("entity_type") == "glossary_term"
                    and ((r.payload or {}).get("description") or "").strip()
                ]
                if _term_results:
                    _blocks: list[str] = []
                    if len(_term_results) > 1:
                        _blocks.append(
                            f"Thuật ngữ **{_term_results[0].name}** có "
                            f"{len(_term_results)} định nghĩa khác nhau trong "
                            "DataHub:"
                        )
                    _linked_terms = await _term_linked_datasets(self._ctx.entity_repo)
                    for _i, _tr in enumerate(_term_results, 1):
                        _tp = _tr.payload or {}
                        _tname = _tr.name or _tp.get("display_name") or ""
                        _tdesc = (_tp.get("description") or "").strip()
                        _tds = [n for n in _linked_terms.get(_tr.urn, []) if n]
                        _tds_suffix = (
                            f"\n\nLiên quan dataset: **{', '.join(_tds[:3])}**."
                            if _tds else ""
                        )
                        if len(_term_results) > 1:
                            _blocks.append(
                                f"{_i}. **{_tname}** "
                                f"(`{_tr.urn}`):\n\n{_tdesc}{_tds_suffix}"
                            )
                        else:
                            _blocks.append(
                                f"Thuật ngữ **{_tname}** (`{_tr.urn}`): "
                                f"{_tdesc}{_tds_suffix}"
                            )
                    _ds_hits = [
                        r for r in results
                        if (r.payload or {}).get("entity_type") == "dataset"
                    ]
                    if _ds_hits:
                        _blocks.insert(
                            0,
                            f"Trong dataset **{_ds_hits[0].name}**, "
                            f"**{_term_results[0].name}** được định nghĩa như sau:",
                        )
                    answer_text = "\n\n".join(_blocks)
                    citations = []
                    docs, context_xml = build_context(results)
                    confidence = "high"
                    if on_token:
                        await on_token(answer_text)
                else:
                    _term = results[0]
                    _term_payload = (_term.payload or {}) if _term.payload else {}
                    _term_desc = (_term_payload.get("description") or "").strip()
                    if _term_payload.get("entity_type") == "glossary_term" and _term_desc:
                        _term_name = _term.name or _term_payload.get("display_name") or ""
                        _linked_terms = await _term_linked_datasets(self._ctx.entity_repo)
                        _tds = [n for n in _linked_terms.get(_term.urn, []) if n]
                        _tds_suffix = (
                            f"\n\nLiên quan dataset: **{', '.join(_tds[:3])}**."
                            if _tds else ""
                        )
                        answer_text = (
                            f"Thuật ngữ **{_term_name}** (`{_term.urn}`): "
                            f"{_term_desc}{_tds_suffix}"
                        )
                        citations = []
                        docs, context_xml = build_context(results)
                        confidence = "high"
                        if on_token:
                            await on_token(answer_text)
                    else:
                        answer_text, citations, docs, context_xml, confidence = (
                            await self._generate_or_fallback(
                                generator, question_for_gen, results, intent,
                                history=history, on_token=on_token,
                                recommendation=recommendation,
                            )
                        )
            if _compound_extra:
                answer_text = f"{answer_text}\n{_compound_extra}"
                if on_token:
                    await on_token(_compound_extra)
        elif intent == QueryIntent.DOCUMENT_QA and results and not impact_mode:
            # Deterministic document-detail answer: a document entity's own
            # description answers "tài liệu X mô tả điều gì?" directly. Prefer
            # a document-typed result when the top hit is a same-named dashboard
            # or dataset.
            _doc = next(
                (r for r in results if (r.payload or {}).get("entity_type") == "document"),
                results[0],
            )
            _doc_payload = (_doc.payload or {}) if _doc.payload else {}
            _doc_desc = (_doc_payload.get("description") or "").strip()
            if _doc.entity_type == "document" and _doc_desc:
                _doc_name = _doc.name or (_doc_payload.get("display_name")) or ""
                answer_text = f"Tài liệu **{_doc_name}** mô tả: {_doc_desc}"
                citations = []
                docs, context_xml = build_context(results)
                confidence = "high"
                if on_token:
                    await on_token(answer_text)
            else:
                answer_text, citations, docs, context_xml, confidence = (
                    await self._generate_or_fallback(
                        generator, question_for_gen, results, intent,
                        history=history, on_token=on_token,
                        recommendation=recommendation,
                    )
                )
        elif intent == QueryIntent.ENTITY_DOMAIN and results and not impact_mode:
            # Deterministic role/domain/owner answer from the resolved metadata:
            # always names the real domain (and owner when the question asks for
            # it) instead of relying on the LLM to paraphrase a payload.
            _payload = (results[0].payload or {}) if results[0].payload else {}
            _domain = (_payload.get("domain") or "").strip()
            _parts = []
            if _domain:
                _parts.append(f"thuộc lĩnh vực/domain **{_domain}**")
            else:
                _parts.append("chưa có domain được ghi nhận trong metadata")
            if re.search(r"\bowner\b|sở hữu|so huu|chủ|chu\b|vai trò|vai tro", query, re.I):
                _owners = [
                    (o.get("name") or "").strip()
                    for o in (_payload.get("owners") or []) if (o.get("name") or "")
                ]
                if _owners:
                    _parts.append(f"có owner: {', '.join(_owners)}")
                else:
                    _parts.append("hiện không có người sở hữu (owner)")
            answer_text = f"Dataset **{results[0].name}** {', '.join(_parts)}."
            citations = []
            docs, context_xml = build_context(results)
            confidence = "high"
            if on_token:
                await on_token(answer_text)
        elif intent == QueryIntent.SCHEMA_LOOKUP and results and not impact_mode:
            # Deterministic schema listing from the resolved metadata: always
            # names the actual fields instead of asking the LLM to paraphrase
            # (or a mock to drop them). When the retrieval produced a cross-
            # dataset join analysis ("liên kết/trường chung giữa X và Y"), that
            # answer supersedes the bare field list.
            if _is_field_location_question(question_for_gen):
                # "dataset nào chứa trường X?" — the results are the datasets
                # carrying the field. List them with a many-results warning; the
                # field itself was named by the user and every result is a real
                # home of the column.
                _field_name = _extract_field_identifier(question_for_gen)
                if not _field_name:
                    _field_name = (results[0].name or "")
                _names: list[str] = []
                _seen_n: set[str] = set()
                for _r in results:
                    _n = _r.name or ""
                    if _n and _n.lower() not in _seen_n:
                        _seen_n.add(_n.lower())
                        _names.append(_n)
                _sample = ", ".join(_names[:10])
                _count_txt = (
                    f" ({len(_names)} dataset)"
                    if len(_names) > 1 else ""
                )
                answer_text = (
                    f"Trường **{_field_name}** được tìm thấy trong "
                    f"{len(_names)} dataset{_count_txt}: {_sample}."
                    + (
                        f"\n\nTrường này xuất hiện ở {len(results)} dataset "
                        "trong metadata (rất phổ biến). Danh sách trên chỉ "
                        "là mẫu đại diện."
                        if len(results) > 10 else ""
                    )
                )
                citations = []
                docs, context_xml = build_context(results)
                confidence = "high"
                if on_token:
                    await on_token(answer_text)
                log.info("schema_field_location", trace_id=trace_id,
                         field=_field_name, datasets=len(_names),
                         question=question_for_gen[:100])
            elif _is_column_meaning_question(question_for_gen):
                # "trường X trong dataset Y nghĩa là gì?" — confirm the field
                # exists in the resolved dataset and state its (name-derived)
                # meaning, grounded in the schema metadata.
                _field_ident = _extract_field_identifier(question_for_gen)
                _col_payload = (results[0].payload or {}) if results[0].payload else {}
                _col_entries = (_col_payload.get("schema_fields") or [])
                _col_entry = None
                if _field_ident:
                    _col_fnorm = _field_ident.strip().lower().replace(" ", "_")
                    _col_entry = next(
                        (f for f in _col_entries
                         if (f.get("name") or "").strip().lower().replace(" ", "_")
                         == _col_fnorm),
                        None,
                    )
                _col_dataset = results[0].name or ""
                if _col_entry:
                    _col_desc = (_col_entry.get("description") or "").strip()
                    _col_type = (_col_entry.get("type") or "").strip()
                    if _col_desc:
                        _meaning_txt = f"Ý nghĩa: {_col_desc}."
                    else:
                        # No field description in the catalog: state the
                        # name-derived meaning WITH provenance so it is not
                        # mistaken for a fabricated definition.
                        _meaning_txt = (
                            "Trường này không có mô tả chi tiết trong metadata; "
                            f"theo tên trường: "
                            f"{_field_meaning(_field_ident or '')}."
                        )
                    answer_text = (
                        f"Trường **{_field_ident}** tồn tại trong dataset "
                        f"**{_col_dataset}**"
                        + (f" (kiểu **{_col_type}**)" if _col_type else "")
                        + f". {_meaning_txt}"
                    )
                elif _field_ident and _col_entries:
                    # The field was NOT found in the resolved dataset's schema.
                    # Never fabricate its existence: state the honest result and
                    # give the name-derived meaning only as an aside, clearly
                    # sourced to the name, not to the dataset's metadata.
                    answer_text = (
                        f"Trường **{_field_ident}** không xuất hiện trong schema "
                        f"của dataset **{_col_dataset}**. "
                        f"Theo tên trường, {_field_ident} có thể mang ý nghĩa: "
                        f"{_field_meaning(_field_ident)}."
                    )
                elif _field_ident:
                    answer_text = (
                        f"Dataset **{_col_dataset}** chưa có schema fields trong "
                        "metadata; không thể xác nhận trường "
                        f"**{_field_ident}** có tồn tại trong dataset này hay "
                        "không."
                    )
                else:
                    answer_text = (
                        f"Dataset **{_col_dataset}** chứa trường được hỏi; "
                        "trường này không có mô tả chi tiết trong metadata; "
                        "theo tên trường: "
                        f"{_field_meaning(_field_ident or '') or 'chưa xác định'}."
                    )
                citations = []
                docs, context_xml = build_context(results)
                confidence = "high"
                if on_token:
                    await on_token(answer_text)
                log.info("schema_column_meaning", trace_id=trace_id,
                         field=_field_ident or "", dataset=_col_dataset,
                         question=question_for_gen[:100])
            else:
                _payload = (results[0].payload or {}) if results[0].payload else {}
                _schema_fields = [
                    {
                        "name": (f.get("name") or "").strip(),
                        "type": (f.get("type") or "").strip(),
                    }
                    for f in (_payload.get("schema_fields") or [])
                    if (f.get("name") or "").strip()
                ]
                # Flat list of "name — type" strings for display
                _schema_fields_names = [
                    f"{f.get('name', '') or ''} — {f.get('type', '') or ''}"
                    for f in (_payload.get("schema_fields") or [])
                    if (f.get("name") or "").strip()
                ]
                _join_analysis = _payload.get("join_analysis")
                if _join_analysis:
                    answer_text = _join_analysis.strip()
                    # A join question that also names the primary key
                    # ("field khóa chính là gì, field join với dim_warehouse là gì")
                    # must state the PK too — the join listing only shows shared
                    # FK/join columns, not the table's own key.
                    if re.search(r"khóa chính|khoa chinh|primary key|pk\b", query, re.I):
                        _pk = next(
                            (f for f in (_payload.get("schema_fields") or [])
                             if (f.get("name") or "").strip().lower().endswith("_id")),
                            None,
                        ) or next(
                            iter(_payload.get("schema_fields") or []), None,
                        )
                        if _pk and ( _pk.get("name") or "").strip():
                            _pk_name = (_pk.get("name") or "").strip()
                            _pk_type = (_pk.get("type") or "").strip()
                            _pk_type_txt = (
                                f" (kiểu **{_pk_type}**)" if _pk_type else ""
                            )
                            answer_text = (
                                f"Dataset **{results[0].name}** có khóa chính là "
                                f"**{_pk_name}**{_pk_type_txt}.\n\n" + answer_text
                            )
                    citations = []
                    docs, context_xml = build_context(results)
                    confidence = "high"
                    if on_token:
                        await on_token(answer_text)
                elif _schema_fields:
                    # Build human-readable field list with name and type
                    field_lines = []
                    for sf in _schema_fields:
                        name = sf.get("name", "") or ""
                        ftype = sf.get("type", "") or ""
                        if name and ftype:
                            field_lines.append(f"{name} — {ftype}")
                        elif name:
                            field_lines.append(name)
                        elif ftype:
                            field_lines.append(ftype)
                    field_str = ", ".join(field_lines[:10])
                    answer_text = (
                        f"Dataset **{results[0].name}** có các trường: "
                        f"{field_str}."
                    )
                    # A composite ask that also names ONE field and its data type
                    # ("... field có batch_number hay không, và kiểu dữ liệu của
                    # nó") must state that field's type too — the plain field list
                    # alone does not carry it.
                    if re.search(
                        r"kiểu\s+dữ\s+liệu|kieu\s+du\s+lieu|data\s*type|datatype|"
                        r"kiểu\s+gì|kieu\s+gi|là\s+kiểu\s+gì|la\s+kieu\s+gi",
                        query, re.I,
                    ):
                        _schema_entries = (_payload.get("schema_fields") or [])
                        _entity_norm = (results[0].name or "").strip().lower().replace(" ", "_")
                        _field_norm = None
                        for _tok in re.findall(
                            r"[A-Za-z0-9]+_[A-Za-z0-9_]+", query,
                        ):
                            _tn = _tok.strip().lower().replace(" ", "_")
                            if _tn == _entity_norm:
                                continue
                            if any(
                                (f.get("name") or "").strip().lower().replace(" ", "_")
                                == _tn for f in _schema_entries
                            ):
                                _field_norm = _tn
                                break
                        if _field_norm:
                            _entry = next(
                                (f for f in _schema_entries
                                 if (f.get("name") or "").strip().lower().replace(" ", "_")
                                 == _field_norm),
                                None,
                            )
                            _ftype = (_entry or {}).get("type") if _entry else None
                            if _ftype:
                                answer_text += (
                                    f" Field **{_entry.get('name')}** có kiểu dữ "
                                    f"liệu: **{_ftype}**."
                                )
                    if re.search(
                        r"glossary|glossar|thuật ngữ|thuat ngu|giải thích|giai thich|"
                        r"định nghĩa|dinh nghia|term",
                        query, re.I,
                    ):
                        _terms = [t for t in (_payload.get("glossary_terms") or []) if t]
                        if _terms:
                            answer_text += (
                                f" Glossary terms của dataset: {', '.join(_terms)}."
                            )
                        else:
                            answer_text += (
                                " Dataset này chưa có glossary term nào được gắn."
                            )
                    if re.search(
                        r"\bdomain\b|lĩnh vực|linh vuc|miền|mien|thuộc về|thuoc ve",
                        query, re.I,
                    ):
                        _domain_val = (_payload.get("domain") or "").strip()
                        if _domain_val:
                            answer_text += (
                                f" Dataset này thuộc lĩnh vực/domain **{_domain_val}**."
                            )
                        else:
                            answer_text += (
                                " Dataset này chưa có domain được ghi nhận trong metadata."
                            )
                    if re.search(
                        r"\bowner\b|sở hữu|so huu|chủ|chu\b|ai là người|ai la nguoi|người quản lý|nguoi quan ly",
                        query, re.I,
                    ):
                        _owners = [o for o in (_payload.get("owners") or []) if o]
                        if _owners:
                            answer_text += (
                                f" Người sở hữu (owner): {', '.join(_owners)}."
                            )
                        else:
                            answer_text += (
                                " Dataset hiện chưa có thông tin người sở hữu (owner)."
                            )
                    citations = []
                    docs, context_xml = build_context(results)
                    confidence = "high"
                    if on_token:
                        await on_token(answer_text)
                else:
                    answer_text, citations, docs, context_xml, confidence = (
                        await self._generate_or_fallback(
                            generator, question_for_gen, results, intent,
                            history=history, on_token=on_token,
                            recommendation=recommendation,
                        )
                    )
        else:
            answer_text, citations, docs, context_xml, confidence = (
                await self._generate_or_fallback(
                    generator, question_for_gen, results, intent,
                    history=history, on_token=on_token,
                    recommendation=recommendation,
                )
            )

        if intent == QueryIntent.DATAHUB_URL:
            urls = [d.url for d in docs if d.url]
            if urls:
                url_block = "\n".join(f"- {u}" for u in dict.fromkeys(urls))
                answer_text = f"{answer_text.rstrip()}\n\nLink DataHub:\n{url_block}"

        _results_by_urn = {r.urn: r for r in results if r.urn}
        entity_list = []
        for d in docs:
            if not d.entity_name:
                continue
            _r = _results_by_urn.get(d.entity_urn)
            entity_list.append(EntityItem(
                urn=d.entity_urn, name=d.entity_name, url=d.url,
                entity_type=_r.entity_type if _r else None,
                platform=((_r.payload or {}).get("platform") if _r else None),
                domain=((_r.payload or {}).get("domain") if _r else None),
                description=((_r.payload or {}).get("description") if _r else None),
                environment=((_r.payload or {}).get("environment") if _r else None),
            ))
        # Field-location listings ("dataset nào chứa trường X?") may match far
        # more datasets than the capped context docs carry. Expose every
        # matching dataset as an entity so the full answer is not silently
        # truncated to the first MAX_CONTEXT_CHUNKS rows.
        if (intent == QueryIntent.SCHEMA_LOOKUP
                and _is_field_location_question(question_for_gen)
                and results and not impact_mode):
            _seen_list: set[str] = set()
            _full_list: list[EntityItem] = []
            for _r in results:
                _key = (_r.urn or "").strip()
                if _r.name and _key not in _seen_list:
                    _seen_list.add(_key)
                    _full_list.append(EntityItem(
                        urn=_r.urn, name=_r.name, url=_r.datahub_url,
                        entity_type=_r.entity_type,
                        platform=(_r.payload or {}).get("platform"),
                        domain=(_r.payload or {}).get("domain"),
                        description=(_r.payload or {}).get("description"),
                        environment=(_r.payload or {}).get("environment"),
                    ))
            if _full_list:
                entity_list = _full_list
        if intent == QueryIntent.LINEAGE and results and not entity_list:
            lineage_data = await self._lineage.build_lineage_data(results[0])
            if lineage_data:
                entity_list = [
                    EntityItem(urn=n.urn, name=n.name, url=n.url, entity_type=n.entity_type)
                    for n in (lineage_data.upstreams + lineage_data.downstreams)
                ] + [
                    EntityItem(urn=lineage_data.entity_urn,
                               name=lineage_data.entity_name,
                               url=lineage_data.entity_url)
                ]
            elif results[0].urn:
                _r0 = results[0]
                entity_list = [
                    EntityItem(
                        urn=_r0.urn, name=_r0.name, url=_r0.datahub_url,
                        entity_type=_r0.entity_type,
                        platform=((_r0.payload or {}).get("platform") if _r0 else None),
                        domain=((_r0.payload or {}).get("domain") if _r0 else None),
                        description=((_r0.payload or {}).get("description") if _r0 else None),
                        environment=((_r0.payload or {}).get("environment") if _r0 else None),
                    )
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

        # Log response for admin audit (includes context snapshot for RAGAS)
        _processing_ms = int((time.perf_counter() - _t_start) * 1000)
        # Always capture docs as a list (may be empty if no results/filtered),
        # so the interaction log and RAGAS evaluation always have a snapshot.
        _ctx_snap: list = docs if isinstance(docs, list) else []
        await self._log_interaction_async(
            "response",
            trace_id=trace_id,
            answer=answer_text,
            intent=intent.value,
            confidence=confidence,
            ambiguous=ambiguous,
            insufficient_context=insufficient_context,
            result_count=len(results),
            top_score=results[0].score if results else None,
            citation_count=len(citations),
            processing_time_ms=_processing_ms,
            message_intent=resolution.message_intent.value if resolution.message_intent else None,
            routing_decision=resolution.decision,
            chosen_tool=resolution.chosen_tool,
            entity_hint=entity_hint,
            entity_resolved_name=results[0].name if results else None,
            entity_resolved_urn=results[0].urn if results else None,
            retrieved_contexts=_ctx_snap,
        )

        # Trigger async RAGAS evaluation (fire-and-forget, never blocks chat)
        if _ctx_snap and ragas_enabled:
            # Build conversation history for context-aware RAGAS evaluation
            _conv_history = []
            if history:
                for h_q, h_a in history:
                    _conv_history.append({"question": h_q, "answer": h_a})
            asyncio.create_task(
                self._background_ragas_eval(trace_id, question_for_gen, answer_text, _ctx_snap, _conv_history)
            )

        lineage: LineageData | None = None
        # Only populate lineage graph visualization payload if the user explicitly
        # requested/selected "Visualize Data Lineage" (selected_action == "lineage").
        # If the user asks a normal lineage question without selecting the visualization action,
        # the response is returned as rich text only.
        if (
            selected_action == "lineage"
            and intent == QueryIntent.LINEAGE
            and results
            and not impact_mode
        ):
            lineage = await self._lineage.build_lineage_data(results[0])

        # Build render_state for conversation persistence (structured data
        # that the frontend needs to re-render entity cards, lineage, etc.)
        _render_state: dict = {}
        _render_state["response_time_ms"] = _processing_ms
        if entity_list:
            _render_state["entities"] = [e.model_dump() for e in entity_list]
        if citations:
            _render_state["citations"] = [c.to_dict() for c in citations]
        if lineage:
            _render_state["lineage"] = lineage.model_dump()
        if selected_action:
            _render_state["selected_action"] = selected_action
        if confidence:
            _render_state["confidence"] = confidence
        if ambiguous:
            _render_state["ambiguous"] = ambiguous
        if insufficient_context:
            _render_state["insufficient_context"] = insufficient_context
        if intent:
            _render_state["intent"] = intent.value
        _render_state["trace_id"] = trace_id

        # Persist render_state into conversation_history for hydration on reload
        try:
            await self._ctx.session.execute(
                sa_update(ConversationHistory).where(
                    ConversationHistory.user_id == uid,
                    ConversationHistory.conversation_id == cid,
                    ConversationHistory.question == question_for_gen,
                ).values(render_state=_render_state or None)
            )
            await self._ctx.session.commit()
        except Exception:
            log.warning("render_state_persist_failed", trace_id=trace_id)

        await _emit("done")

        res = ChatResponse(
            answer=answer_text,
            intent=plan.intent if (
                impact_mode
                or (plan.source == "classifier" and intent.value == "GENERAL")
            ) else intent.value,
            entities=entity_list,
            citations=[CitationItem(**c.to_dict()) for c in citations],
            confidence=confidence,
            ambiguous=ambiguous,
            insufficient_context=insufficient_context,
            trace_id=trace_id,
            conversation_id=cid,
            lineage=lineage,
            selected_action=selected_action,
            response_time_ms=_processing_ms,
        )
        return await self._postprocess_response(res, _t_start, uid, cid, question_for_gen)



    async def _try_metadata_listing(
        self,
        question: str,
        user_ctx: UserContext,
        trace_id: str,
        cid: str,
        _t_start: float = 0.0,
    ) -> ChatResponse | None:
        """Try to parse and execute a generic metadata listing query.

        Handles "dataset nào có X?", "dataset nào không có X?",
        "dataset nào thuộc domain Y?" patterns.

        Returns ChatResponse if a metadata query was parsed, else None.
        """
        from guardrails.sanitizer import mask_secrets

        mq = parse_metadata_query(question)
        if mq is None:
            return None

        log.info(
            "metadata_listing_detected",
            trace_id=trace_id,
            query=mq.to_dict(),
            message=question[:100],
        )

        engine = MetadataFilterEngine(self._ctx.session)
        result = await engine.execute(mq)

        # Apply RBAC filtering
        if self._ctx.auth_service:
            entities = await self._ctx.auth_service.filter_entities_by_domain(
                user_ctx, result.entities
            )
            accessible = await self._ctx.auth_service.filter_accessible_urns(
                user_ctx, [e.urn for e in entities]
            )
            result.entities = [e for e in entities if e.urn in accessible]
            result.returned_count = len(result.entities)

        answer_text = mask_secrets(result.to_answer_text())

        entity_list = [
            EntityItem(
                urn=e.urn, name=e.display_name or e.name, url=e.datahub_url,
                entity_type=e.entity_type, platform=e.platform, domain=e.domain,
                description=e.description, environment=e.environment,
            )
            for e in result.entities
        ]

        await self._ctx.memory.add_turn_db(
            self._ctx.session, user_ctx.user_id, cid, question, answer_text,
        )

        res = ChatResponse(
            answer=answer_text,
            intent="METADATA_LISTING",
            entities=entity_list,
            confidence="high",
            ambiguous=False,
            insufficient_context=False,
            trace_id=trace_id,
            conversation_id=cid,
        )
        return await self._postprocess_response(res, _t_start, user_ctx.user_id, cid, question)


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
        understanding=None,
    ) -> "ChatResponse | None":
        """Answer a self-contained field question that names its own entity and
        field ("warehouse_id của fact_inventory_movement có kiểu dữ liệu gì?")
        directly from the resolved dataset's schema metadata.

        When Query Understanding is enabled, its JSON contract rescues
        field-property questions the regex router could not parse (single-word
        fields like "quantity", or a bare column token without the "của <entity>"
        clause): the LLM-supplied ``focus_field`` + ``property`` drive the same
        deterministic schema answer.

        Returns ``None`` (falls through to the search pipeline) when no explicit
        ``entity.field`` pair can be extracted, the entity can't be trusted, or
        the dataset has no usable ``schema_fields``.
        """
        from app.services.chat.field_ops import answer_field_op, find_field_entry

        def _norm_field(f: str) -> str:
            return (f or "").strip().lower().replace(" ", "_")

        # Field-LOCATION questions ("dataset nào chứa trường X?", "trường X
        # nằm trong những dataset nào?") ask WHERE a column lives - a listing
        # of every dataset carrying it, answered by the SCHEMA_LOOKUP listing
        # branch with a many-results warning. The direct field-op path would
        # collapse the results to a handful of dim_ tables and miss the true
        # count. Route them to the listing branch instead.
        if _is_field_location_question(query):
            return None

        op = parse_field_operation(query)
        ellipsis_field: str | None = None
        if op is None or op.op == "find_field":
            # QU rescue: the question explicitly targets one field property but
            # the field token was not snake_case / not in a "field của entity"
            # clause. The LLM's focus_field + property are the missing pair.
            if (understanding is not None
                    and understanding.is_field_property_question
                    and understanding.focus_field
                    and understanding.property):
                op = FieldOp(
                    op="get_property",
                    property=understanding.property,
                    field=understanding.focus_field,
                )
            else:
                # Bare-ellipsis field follow-up: "còn trường warehouse_id thì
                # sao?" after a schema listing carries no "field của entity"
                # clause and no explicit property — the named field is the
                # target, and the property inherits the previous field-property
                # turn (default: data type). It must NOT fall through to the
                # search pipeline which canonicalizes the whole sentence into a
                # dataset name ("con truong warehouse id thi sao").
                _em = re.search(
                    r"\b(?:con|the con|vay|vao)\b",
                    _norm_vn(query),
                )
                if _em:
                    _fm = re.search(
                        r"(?:trường|truong|field|cột|cot)\s+[\"“”'`]?"
                        r"([a-z0-9_]{2,}(?:\.[a-z0-9_]+)*)",
                        query, re.I,
                    )
                    if _fm:
                        ellipsis_field = _fm.group(1)
                if ellipsis_field:
                    op = FieldOp(op="get_property", property="data_type",
                                 field=ellipsis_field)
                else:
                    # Bare field-property with no "field của entity" clause and
                    # no ellipsis ("kiểu dữ liệu của trường VIN_NUM là gì?"):
                    # the parser cannot tokenize underscore identifiers on its
                    # own, so detect the property + the bare identifier directly.
                    from retrieval.evidence import detect_field_property
                    _prop2 = detect_field_property(query)
                    _bid = _extract_field_identifier(query)
                    if _prop2 and _bid:
                        op = FieldOp(op="get_property", property=_prop2,
                                     field=_bid)
                    else:
                        return None
        field = op.field if (op is not None and op.field) else ellipsis_field
        if not field:
            return None
        entity_name, _ef = extract_field_entity(query)
        if not entity_name and understanding is not None and understanding.entity_refs:
            entity_name = understanding.entity_refs[0]

        entity_db = None
        if entity_name:
            resolution = await self._ctx.entity_resolver.resolve(
                entity_name, entity_type="dataset", trace_id=trace_id,
            )
            if resolution is None or not _trusted_resolution(resolution):
                # Same-named datasets across platforms ("fact_sale_orders" on
                # redshift AND several powerbi containers) resolve as a tie with no
                # ``resolved``. Every candidate carries the same display name the
                # user typed, so the top one is the field's home — never clarify.
                if (resolution is not None and resolution.ambiguous
                        and resolution.candidates
                        and len({(c.name or "").strip().lower()
                                 for c in resolution.candidates[:4]}) == 1):
                    resolution.resolved = resolution.candidates[0]
                else:
                    return None
            entity_db = await self._ctx.entity_repo.get_by_urn(resolution.resolved.urn)
        else:
            # "còn trường X thì sao" / bare field after a schema turn: bind to
            # the conversation's schema evidence that actually contains the
            # field, so the type/meaning is answered about the ACTIVE dataset —
            # never a fresh silent re-search.
            _evidence = self._ctx.memory.get_evidence(uid, cid) or []
            for _ev in reversed(_evidence):
                _evd = _ev.get("structured") or {}
                _ev_fields = [f for f in (_evd.get("fields") or []) if f]
                if any(_norm_field(f) == _norm_field(field) for f in _ev_fields):
                    entity_db = await self._ctx.entity_repo.get_by_urn(
                        _ev.get("entity_urn"))
                    if entity_db is not None:
                        break
        if entity_db is None:
            # Bare field with no dataset in the question and no conversation
            # context ("kiểu dữ liệu của trường VIN_NUM là gì?"): locate every
            # dataset carrying the field and answer the type from real schema
            # metadata — never an unrelated entity's "no schema" answer.
            locate = await self._retrieval.resolve_field_lookup(field, trace_id)
            if not locate:
                return None
            _types: dict[str, str] = {}
            _names: list[str] = []
            _seen: set[str] = set()
            for _r in locate:
                _rsf = (_r.payload or {}).get("schema_fields") or []
                _r_entry = find_field_entry(_rsf, field)
                _rtype = ((_r_entry or {}).get("type") or "").strip()
                _rname = (_r.name or "").strip()
                if _rname and _rname.lower() not in _seen:
                    _seen.add(_rname.lower())
                    _names.append(_rname)
                if _rtype and _rtype not in _types:
                    _types[_rtype] = _rname
            if not _types:
                return None
            text = (
                f"Trường **{field}** có kiểu dữ liệu **{' / '.join(_types)}** "
                f"trong {len(_names)} dataset: {', '.join(_names[:8])}."
            )
            intent_label = {
                "data_type": "CONTEXT_FIELD_TYPE",
                "native_data_type": "CONTEXT_FIELD_TYPE",
                "description": "CONTEXT_FIELD_DESCRIPTION",
            }.get(op.property or "", "CONTEXT_FIELD_PROPERTY")
            await self._ctx.memory.add_turn_db(
                self._ctx.session, uid, cid, query, text,
            )
            return ChatResponse(
                answer=text,
                intent=intent_label,
                confidence="high",
                ambiguous=False,
                insufficient_context=False,
                trace_id=trace_id,
                conversation_id=cid,
            )
        schema_fields = (entity_db.payload or {}).get("schema_fields") or []
        display = entity_db.display_name or entity_db.name
        text = answer_field_op(
            schema_fields, display,
            FieldOp(op="get_property", property=op.property or "data_type",
                    field=field),
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

    # ------------------------------------------------------------------ #
    # Comparison flow
    # ------------------------------------------------------------------ #

    async def _comparison_flow(
        self,
        query: str,
        entity_names: list[str],
        user_ctx: UserContext | None,
        trace_id: str,
        cid: str,
        on_token: Callable | None = None,
        on_status: Callable | None = None,
    ) -> ChatResponse | None:
        """Compare multiple entities side-by-side.

        Steps:
          1. Resolve each entity name to a catalog entry (URN + metadata)
          2. Retrieve schema, lineage, quality, domain for each
          3. Generate a structured comparison answer via LLM
        """
        if on_status:
            await on_status("retrieve")

        from retrieval.hybrid_search import HybridSearch

        resolved_entities: list[dict[str, Any]] = []
        failed_entities: list[str] = []

        # Step 1: Resolve each entity independently
        for name in entity_names:
            try:
                res = await self._ctx.entity_resolver.resolve(name, entity_type=None, trace_id=trace_id)
                if res and res.resolved:
                    best = res.resolved
                    resolved_entities.append({
                        "name": name,
                        "resolved_name": getattr(best, "display_name", None) or getattr(best, "name", str(best)),
                        "urn": best.urn,
                        "entity_type": best.entity_type,
                        "score": 1.0,
                    })
                else:
                    results = await self._ctx.hybrid_search.search(name, entity_type=None)
                    if results:
                        best_res = results[0]
                        resolved_entities.append({
                            "name": name,
                            "resolved_name": best_res.name,
                            "urn": best_res.urn,
                            "entity_type": best_res.entity_type,
                            "score": best_res.score,
                        })
                    else:
                        failed_entities.append(name)
            except Exception:  # noqa: BLE001
                log.exception("comparison_resolve_failed", entity=name, trace_id=trace_id)
                failed_entities.append(name)

        if not resolved_entities:
            entity_list = ", ".join(entity_names)
            answer = (
                f"Không tìm thấy entity nào trong số: {entity_list}. "
                "Vui lòng kiểm tra lại tên và thử lại."
            )
            return ChatResponse(
                answer=answer, intent="COMPARISON", confidence="low",
                ambiguous=False, insufficient_context=True,
                trace_id=trace_id, conversation_id=cid,
            )

        # Step 2: Retrieve metadata for each resolved entity
        entity_details: list[dict[str, Any]] = []
        for ent in resolved_entities:
            detail: dict[str, Any] = {
                "name": ent["resolved_name"],
                "urn": ent["urn"],
                "entity_type": ent["entity_type"],
                "schema": [],
                "lineage": {"upstreams": [], "downstreams": []},
                "domain": None,
                "owner": None,
                "description": None,
                "tags": [],
                "glossary_terms": [],
            }
            try:
                db_entity = await self._ctx.entity_repo.get_by_urn(ent["urn"])
                if db_entity:
                    payload = db_entity.payload or {}
                    detail["schema"] = payload.get("schema_fields") or []
                    detail["domain"] = db_entity.domain
                    detail["description"] = db_entity.description
                    detail["owner"] = payload.get("owner") or (payload.get("owners")[0] if payload.get("owners") else None)
                    detail["tags"] = payload.get("tags") or []
                    detail["glossary_terms"] = payload.get("glossary_terms") or []
            except Exception:  # noqa: BLE001
                log.exception("comparison_detail_failed", urn=ent["urn"], trace_id=trace_id)

            # Lineage
            try:
                lineage_data = await self._ctx.source.get_lineage(
                    ent["urn"], direction="both", depth=1,
                )
                for rel in lineage_data.get("relationships", []):
                    entity_info = rel.get("entity", {})
                    node = {
                        "name": entity_info.get("urn", ""),
                        "type": entity_info.get("type", "unknown"),
                    }
                    if rel.get("type") == "UPSTREAM":
                        detail["lineage"]["upstreams"].append(node)
                    elif rel.get("type") == "DOWNSTREAM":
                        detail["lineage"]["downstreams"].append(node)
            except Exception:  # noqa: BLE001
                log.exception("comparison_lineage_failed", urn=ent["urn"], trace_id=trace_id)

            if not detail["lineage"]["upstreams"] and not detail["lineage"]["downstreams"]:
                db_ent = await self._ctx.entity_repo.get_by_urn(ent["urn"])
                if db_ent and db_ent.payload:
                    for u in db_ent.payload.get("upstreams") or []:
                        detail["lineage"]["upstreams"].append({"name": u, "type": "dataset"})
                    for d in db_ent.payload.get("downstreams") or []:
                        detail["lineage"]["downstreams"].append({"name": d, "type": "dataset"})

            entity_details.append(detail)

        # Step 3: Build comparison prompt and generate answer
        import json as _json

        entities_text = _json.dumps(entity_details, ensure_ascii=False, indent=2, default=str)

        # Extract what aspects to compare from the query
        compare_aspects: list[str] = []
        _ASPECT_PATTERNS = [
            (r"schema|field|column|cột|trường", "schema"),
            (r"quality|chất lượng|chat luong|kém|sạch", "quality"),
            (r"lineage|upstream|downstream|nguồn|nguon", "lineage"),
            (r"owner|sở hữu|so huu|thuộc về ai", "owner"),
            (r"domain|lĩnh vực|linh vuc|miền|mien", "domain"),
            (r"description|mô tả|mo ta|nội dung", "description"),
            (r"tag|nhãn|nhan|gắn tag", "tags"),
            (r"glossary|term|thuật ngữ|thuat ngu|khái niệm", "glossary"),
        ]
        query_lower = query.lower()
        for pattern, aspect in _ASPECT_PATTERNS:
            if re.search(pattern, query_lower):
                compare_aspects.append(aspect)
        if not compare_aspects:
            compare_aspects = ["schema", "quality", "lineage", "domain"]

        comparison_prompt = (
            f"Bạn là trợ lý metadata. Hãy so sánh các entity sau dựa trên "
            f"các khía cạnh: {', '.join(compare_aspects)}.\n\n"
            f"Dữ liệu entities:\n{entities_text}\n\n"
            f"Câu hỏi gốc: {query}\n\n"
            f"Yêu cầu:\n"
            f"1. Liệt kê thông tin thực tế từ dữ liệu cho mỗi entity\n"
            f"2. So sánh rõ ràng giữa các entity\n"
            f"3. Đưa ra recommendation có căn cứ\n"
            f"4. Chỉ dùng thông tin có trong dữ liệu, KHÔNG bịa đặt\n"
            f"5. Trả lời bằng tiếng Việt, format markdown\n"
        )

        if on_status:
            await on_status("generate")

        try:
            answer_text = await self._ctx.llm.generate(
                comparison_prompt,
            )
        except Exception:  # noqa: BLE001
            log.exception("comparison_llm_failed", trace_id=trace_id)
            answer_text = ""

        if answer_text and answer_text.strip().startswith("{"):
            try:
                parsed_ans = _json.loads(answer_text)
                if isinstance(parsed_ans, dict) and "answer" in parsed_ans:
                    answer_text = str(parsed_ans["answer"])
            except Exception:
                pass

        if not answer_text or not answer_text.strip():
            answer_text = self._deterministic_comparison(entity_details, compare_aspects)

        answer_text = mask_secrets(answer_text)

        # Record evidence for each entity
        for ent in resolved_entities:
            await self._evidence.record_active_entities(
                uid=user_ctx.user_id if user_ctx else "anonymous",
                cid=cid, results=[], question=query, extra=[{
                    "name": ent["resolved_name"],
                    "urn": ent["urn"],
                    "entity_type": ent["entity_type"],
                }],
            )

        return ChatResponse(
            answer=answer_text,
            intent="COMPARISON",
            confidence="high",
            ambiguous=len(resolved_entities) < 2,
            insufficient_context=bool(failed_entities),
            trace_id=trace_id,
            conversation_id=cid,
            entities=[
                {
                    "urn": ent["urn"],
                    "name": ent["resolved_name"],
                    "url": f"https://datahub.vinfastauto.com/dataset/{ent['urn']}",
                }
                for ent in resolved_entities
            ],
        )

    def _deterministic_comparison(
        self,
        entity_details: list[dict[str, Any]],
        aspects: list[str],
    ) -> str:
        """Fallback comparison when LLM fails — render structured markdown from metadata."""
        lines: list[str] = []
        lines.append("### So sánh entities\n")

        for ent in entity_details:
            lines.append(f"#### {ent['name']}")
            lines.append(f"- **URN**: `{ent['urn']}`")
            lines.append(f"- **Type**: {ent['entity_type']}")
            if ent.get("domain"):
                lines.append(f"- **Domain**: {ent['domain']}")
            if ent.get("owner"):
                lines.append(f"- **Owner**: {ent['owner']}")
            if ent.get("description"):
                lines.append(f"- **Description**: {ent['description'][:200]}")

            if "schema" in aspects and ent.get("schema"):
                lines.append(f"- **Schema** ({len(ent['schema'])} fields):")
                for f in ent["schema"][:10]:
                    fname = f.get("name", "?")
                    ftype = f.get("type", f.get("native_data_type", "?"))
                    lines.append(f"  - `{fname}` ({ftype})")
                if len(ent["schema"]) > 10:
                    lines.append(f"  - ... và {len(ent['schema']) - 10} trường khác")

            if "lineage" in aspects:
                up = ent["lineage"]["upstreams"]
                down = ent["lineage"]["downstreams"]
                if up or down:
                    lines.append(f"- **Lineage**: {len(up)} upstream, {len(down)} downstream")
                else:
                    lines.append("- **Lineage**: Không có lineage được ghi nhận")

            if "tags" in aspects and ent.get("tags"):
                lines.append(f"- **Tags**: {', '.join(ent['tags'][:5])}")

            if "glossary" in aspects and ent.get("glossary_terms"):
                lines.append(f"- **Glossary**: {', '.join(ent['glossary_terms'][:5])}")

            lines.append("")

        lines.append("### Kết luận")
        lines.append("So sánh trên dựa trên metadata thực tế từ catalog.")
        return "\n".join(lines)

