"""Semantic intent resolution layer.

A user may drive the chatbot by typing freely or by picking a predefined UI action
from the "+" menu (e.g. *Impact Analysis*, *Data Lineage*, *Generate SQL*). A menu
pick is an *intent hint*, never a mandatory execution path. This module merges three
signals — the raw user message, the selected action and the conversation context —
into one routing decision so both interaction styles converge on the same behaviour:

    User Message + Selected Action + Conversation Context
        -> Intent Resolution
            -> Query Planning (carried in the returned ``QueryPlan``)
                -> Tool Selection (reported via ``chosen_tool``)
                    -> Retrieval / LLM (handled by the caller)

Decision rules
--------------
- ``agree``    : the message matches the selected action (or provides the entity the
                 action needs, possibly referred to by an anaphor resolved from history).
- ``override`` : the message expresses a different, explicit request that conflicts with
  the selected action. The user's explicit wording always wins.
- ``clarify``  : neither signal is clear enough to act on. Ask for clarification.
- ``no_action``: no menu action was selected; route purely on the message.

The layer is deterministic (fast, no LLM) on the common path and only asks the LLM to
disambiguate genuinely ambiguous ``GENERAL`` messages that still contain an entity token,
where the keyword router cannot tell a bare "entity under the action" from "a different
capability". On LLM failure it falls back to the deterministic decision.
"""

from __future__ import annotations

import re as _re
import unicodedata
from dataclasses import dataclass

import structlog

from config.prompts import ACTION_RESOLUTION_PROMPT
from config.settings import settings
from llm.base import BaseLLM
from retrieval.classifier import _first_json, regex_plan
from retrieval.confirmation import ConfirmationDetector
from retrieval.entity_detection import EntityNameDetector
from retrieval.intent import QueryIntent, classify_intent, normalize_intent
from retrieval.query_models import QueryPlan

log = structlog.get_logger()

_ANAPHORA_EN = {"this", "that", "it", "its", "the one", "this one", "that one", "these", "those"}
_ANAPHORA_VI = {"do", "no", "ay", "nay", "day", "kia", "no", "bang", "bang do"}

# Words that mark the message as describing a *capability* rather than a bare entity
# name, so the heuristic entity-hint parser does not mistake them for an entity.
_CAPABILITY_VERBS = _re.compile(
    r"(đánh giá|danh gia|kiểm tra|kiem tra|chất lượng|chat luong|quality|impact|"
    r"ảnh hưởng|anh huong|lineage|linage|schema|cột|cot|trường|truong|field|column|"
    r"report|báo cáo|bao cao|sql|generate|sinh lệnh|sinh|tạo|tao|tìm|tim|liệt kê|liet ke|"
    r"danh sách|danh sach|list|show|xem|mô tả|mo ta|có bao nhiêu|co bao nhieu|how many|"
    r"thuộc|thuoc|owner|sở hữu|so huu|certified|xác nhận|xac nhan|bia|related|liên quan|"
    r"viết|viet|làm thơ|lam tho|thơ|tho|giúp|giup|muốn|muon|hỏi|hoi|cho biết|cho biet|"
    r"bạn|ban|tôi|toi|em|anh|chị|chi|bài|bai)",
    _re.I,
)
_QUESTION_WORDS = _re.compile(
    r"(là gì|la gi|nào|nao|ai|what|which|how|why|who|của|cua|cho tôi|toi|bạn|ban)",
    _re.I,
)


# --------------------------------------------------------------------------- #
# Action registry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ActionSpec:
    kind: str
    title: str
    prompt: str  # retrieval framing used when only the entity is given
    canonical_intent: str  # intent routed to when the message only supplies the entity
    expected_intents: frozenset[str]  # message-only intents that "agree" with the action
    entity_type: str | None
    tool: str
    clarification: str                   # question the assistant asks when intent is unclear


_ACTIONS: dict[str, ActionSpec] = {
    "search": ActionSpec(
        kind="search",
        title="Search Dataset",
        prompt="Tìm dataset ",
        canonical_intent="FIND_ENTITY",
        expected_intents=frozenset({
            "FIND_ENTITY", "DATASET_LOOKUP", "LISTING", "SEMANTIC_SEARCH",
            "RELATED_DATASETS", "MULTI_ENTITY_QUERY", "COMPOSITE_QUERY",
            "DOMAIN_QUERY", "PLATFORM_QUERY", "TAG_QUERY", "ENTITIES_BY_OWNER",
            "GENERAL",
        }),
        entity_type="dataset",
        tool="hybrid_search",
        clarification=(
            "Bạn muốn tìm dataset nào? Hãy cho tôi biết tên dataset, cột, owner "
            "hoặc tag để tôi tìm giúp bạn."
        ),
    ),
    "sql": ActionSpec(
        kind="sql",
        title="Generate SQL",
        prompt="Generate SQL cho dataset ",
        canonical_intent="SQL_GENERATION",
        expected_intents=frozenset({
            "FIND_ENTITY", "DATASET_LOOKUP", "SCHEMA_LOOKUP",
            "SQL_GENERATION", "GENERAL", "TERM_DEFINITION",
        }),
        entity_type="dataset",
        tool="sql_generator",
        clarification=(
            "Tôi cần biết bạn muốn sinh SQL cho dataset nào. Hãy nhập tên dataset "
            "(ví dụ: sales_order)."
        ),
    ),
    "impact": ActionSpec(
        kind="impact",
        title="Impact Analysis",
        prompt="Impact analysis cho dataset ",
        canonical_intent="IMPACT",
        expected_intents=frozenset({
            "IMPACT", "RECURSIVE_IMPACT", "IMPACT_ANALYSIS", "LINEAGE",
            "GENERAL", "TERM_DEFINITION",
        }),
        entity_type="dataset",
        tool="recursive_impact",
        clarification="Bạn muốn đánh giá ảnh hưởng hạ nguồn (impact analysis) cho dataset nào?",
    ),

    "lineage": ActionSpec(
        kind="lineage",
        title="Data Lineage",
        prompt="Data lineage của dataset ",
        canonical_intent="LINEAGE",
        expected_intents=frozenset({
            "LINEAGE", "LINEAGE_UPSTREAM", "LINEAGE_DOWNSTREAM", "IMPACT",
            "GENERAL", "TERM_DEFINITION", "FIND_ENTITY", "DATASET_LOOKUP",
        }),
        entity_type="dataset",
        tool="lineage",
        clarification=(
            "Bạn muốn xem lineage của dataset nào? Hãy cho tên dataset (ví dụ: "
            "dim_warehouse)."
        ),
    ),
    "quality": ActionSpec(
        kind="quality",
        title="Data Quality Check",
        prompt="Data quality check cho dataset ",
        canonical_intent="QUALITY_CHECK",
        expected_intents=frozenset({
            "QUALITY_CHECK", "FIND_ENTITY", "DATASET_LOOKUP", "GENERAL",
            "TERM_DEFINITION", "SCHEMA_LOOKUP",
        }),
        entity_type="dataset",
        tool="quality_check",
        clarification="Bạn muốn đánh giá chất lượng metadata (data quality) của dataset nào?",
    ),
    "report": ActionSpec(
        kind="report",
        title="Metadata Report",
        prompt="Metadata report cho dataset ",
        canonical_intent="METADATA_REPORT",
        expected_intents=frozenset({
            "METADATA_REPORT", "FIND_ENTITY", "DATASET_LOOKUP", "GENERAL",
            "TERM_DEFINITION", "SCHEMA_LOOKUP",
        }),
        entity_type="dataset",
        tool="metadata_report",
        clarification="Bạn muốn tạo metadata report cho dataset nào?",
    ),
}

# Canonical intents that are unambiguously about metadata. Any of these in the raw
# message is treated as an explicit user request that overrides a conflicting action.
_EXPLICIT_METADATA_INTENTS = frozenset({
    QueryIntent.FIND_ENTITY, QueryIntent.DATASET_LOOKUP, QueryIntent.FIELD_LOOKUP,
    QueryIntent.SCHEMA_LOOKUP, QueryIntent.TERM_DEFINITION, QueryIntent.OWNER_LOOKUP,
    QueryIntent.DOMAIN_LOOKUP, QueryIntent.LINEAGE_UPSTREAM, QueryIntent.LINEAGE_DOWNSTREAM,
    QueryIntent.IMPACT_ANALYSIS, QueryIntent.RECURSIVE_IMPACT, QueryIntent.COMPOSITE_QUERY,
    QueryIntent.GRAPH_QUERY, QueryIntent.RELATED_DATASETS, QueryIntent.SEMANTIC_SEARCH,
    QueryIntent.MULTI_ENTITY_QUERY, QueryIntent.TERM_TO_DATASETS, QueryIntent.LINEAGE,
    QueryIntent.IMPACT, QueryIntent.ENTITY_DOMAIN, QueryIntent.COUNT_ENTITIES,
    QueryIntent.DOMAIN_QUERY, QueryIntent.TAG_QUERY, QueryIntent.PLATFORM_QUERY,
    QueryIntent.ENTITIES_BY_OWNER, QueryIntent.CERTIFIED_LIST, QueryIntent.DOCUMENT_QA,
    QueryIntent.DATAHUB_URL, QueryIntent.ENTITY_EXISTS, QueryIntent.LISTING,
    QueryIntent.SQL_GENERATION, QueryIntent.QUALITY_CHECK, QueryIntent.METADATA_REPORT,
})

_INTENT_TOOL: dict[QueryIntent, str] = {
    QueryIntent.IMPACT: "recursive_impact",
    QueryIntent.LINEAGE: "lineage",
    QueryIntent.SCHEMA_LOOKUP: "schema_lookup",
    QueryIntent.FIELD_PROPERTY: "schema_lookup",
    QueryIntent.TERM_DEFINITION: "glossary_lookup",
    QueryIntent.OWNER_LOOKUP: "owner_lookup",
    QueryIntent.ENTITY_EXISTS: "existence",
    QueryIntent.COUNT_ENTITIES: "count_entities",
    QueryIntent.TERM_TO_DATASETS: "term_to_datasets",
    QueryIntent.DOCUMENT_QA: "document_qa",
    QueryIntent.DOMAIN_QUERY: "list_by_dimension",
    QueryIntent.PLATFORM_QUERY: "list_by_dimension",
    QueryIntent.TAG_QUERY: "list_by_dimension",
    QueryIntent.ENTITIES_BY_OWNER: "list_by_dimension",
    QueryIntent.CERTIFIED_LIST: "list_by_dimension",
    QueryIntent.LISTING: "list_by_type",
    QueryIntent.ENTITY_DOMAIN: "resolve_entity",
    QueryIntent.DATAHUB_URL: "resolve_entity",
    QueryIntent.FIND_ENTITY: "resolve_entity",
    QueryIntent.DATASET_LOOKUP: "resolve_entity",
    QueryIntent.FIELD_LOOKUP: "schema_lookup",
    QueryIntent.DOMAIN_LOOKUP: "resolve_entity",
    QueryIntent.SQL_GENERATION: "sql_generator",
    QueryIntent.QUALITY_CHECK: "quality_check",
    QueryIntent.METADATA_REPORT: "metadata_report",
    QueryIntent.COMPARISON: "comparison",
}

# Listing detection mirrors chat_service._detect_listing so the resolver can
# recognize LISTING messages even though the keyword classifier has no dedicated
# LISTING rule yet.
_LISTING_TYPES = r'(dataset|dashboard|glossary(?:\s+terms?)?|documents?|tài liệu|tai lieu)'
_LISTING_TYPES_EN = r'(datasets|dashboards|glossary\s+terms|documents)'
_LISTING_PREFIX = r'(?:(?:trong|in)\s+(?:hệ thống|he thong|system)\s+)?'

_LISTING_PATTERNS = [
    _re.compile(
        rf'^{_LISTING_PREFIX}(?:có các|các)\s+{_LISTING_TYPES}\s+(?:gì|nào)\??$',
        _re.I,
    ),
    _re.compile(rf'^{_LISTING_PREFIX}(?:có các|các)\s+{_LISTING_TYPES}\s*$', _re.I),
    _re.compile(rf'^liệt kê\s+(?:các\s+)?{_LISTING_TYPES}\s*$', _re.I),
    _re.compile(rf'^list\s+(?:all\s+)?{_LISTING_TYPES_EN}\s*$', _re.I),
    _re.compile(rf'^danh sách\s+(?:các\s+)?{_LISTING_TYPES}\s*$', _re.I),
    _re.compile(rf'^show\s+(?:all\s+)?{_LISTING_TYPES_EN}\s*$', _re.I),
    _re.compile(rf'^{_LISTING_PREFIX}có những {_LISTING_TYPES} nào\??$', _re.I),
]


def _detect_listing(message: str) -> bool:
    cleaned = message.lower().strip().rstrip("?!.")
    return any(p.match(cleaned) for p in _LISTING_PATTERNS)


def _norm(s: str) -> str:
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    try:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:  # noqa: BLE001
        pass
    return _re.sub(r"\s+", " ", s).strip()


def _anon_is_anaphora(message: str) -> bool:
    """True when the message is a reference to a previous turn (đó/nó/ấy/này/this/that…)."""
    m = _norm(message)
    return bool(_re.search(r"\b(?:do|no|ay|nay|day|kia)\b", m)) or any(
        w in message.lower().split() for w in _ANAPHORA_EN if len(w) > 2
    )


def _has_entity(message: str) -> bool:
    """Heuristic: does the message carry something that looks like a concrete entity name?"""
    if not message:
        return False
    if _re.search(r"[A-Za-z0-9_]{2,}(?:\.[A-Za-z0-9_]+)+", message):
        return True
    if _re.search(r"[a-z0-9]{2,}_[a-z0-9_]+", message, _re.I):
        return True
    n = _norm(message)
    words = [w for w in _re.split(r"[\s,;:]+", n) if w and len(w) > 1]
    if not words or len(words) > 3:
        return False
    if _CAPABILITY_VERBS.search(n) or _QUESTION_WORDS.search(n):
        return False
    return True


_ACTION_PREFIX_RE = _re.compile(
    r"^(?:(?:cho tôi xem|cho toi xem|cho xem|xem|vẽ|ve|hiển thị|hien thi|tạo|tao|kiểm tra|kiem tra|đánh giá|danh gia|phân tích|phan tich)\s+)?"
    r"(?:visualize\s+)?(?:data\s+)?(?:lineage|linage|impact(?:\s+analysis)?|quality(?:\s+check)?|metadata\s+report|report|generate\s+sql|sql|search(?:\s+dataset)?|tìm\s+kiếm|tim\s+kiem|tìm|tim|tra\s+cứu|tra\s+cuu)\s*"
    r"(?:(?:của|cho|cua|of|for)\s+)?"
    r"(?:(?:dataset|dashboard|glossary(?:\s+term)?|document|bảng|bang|tài liệu|tai lieu)\s+)?"
    r"([A-Za-z0-9][A-Za-z0-9 _\-.'&]{1,80})$",
    _re.I,
)


def _extract_entity(message: str) -> str | None:
    """Best-guess entity token from the message (snake/dotted token, else short phrase)."""
    clean_msg = message.strip().rstrip("?.!,;:")

    # 0. Action prefix stripping (e.g. "Lineage của dataset PVB QDAT", "lineage PVB QDAT", "Impact PVB QDAT")
    m_act = _ACTION_PREFIX_RE.match(clean_msg)
    if m_act:
        cand = m_act.group(1).strip()
        if len(cand) >= 2 and not _re.match(
            r"^(?:cho|cua|của|of|for|the|a|an|này|đó|nay|do|không|khong|tồn|ton|tại|tai)$", cand, _re.I
        ):
            return cand

    # 1. Dotted path (schema.table)
    for m in _re.finditer(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", message):
        tok = m.group(0)
        if not _re.match(r"^\d+\.\d+$", tok):
            return tok
    # 2. Snake_case identifier
    for m in _re.finditer(r"[A-Za-z0-9]{2,}_[A-Za-z0-9_]+", message):
        return m.group(0)

    # Metadata verb fragments and question particles that should not be part
    # of an entity name. Covers Vietnamese and English.
    _META_NOISE = {
        "co", "có", "khong", "không", "chua", "chưa", "thieu", "thiếu", "thuoc", "thuộc", "tren", "trên", "nao", "nào",
        "cung", "cũng", "nhung", "những", "va", "và", "hoac", "hoặc", "de", "để", "nay", "này", "do", "đó",
        "nhu", "như", "the", "thế", "gi", "gì", "gii", "la", "là", "duoc", "được", "ton tai", "tồn tại",
        "không tồn tại", "khong ton tai", "ko", "k",
    }

    # 0. Multi-word entity after Vietnamese/English dataset markers.
    for m in _re.finditer(
        r"(?:của|cho|cua|of|for|dataset|bang|bảng)\s+"
        r"(?:dataset\s+)?"
        r"([A-Za-z0-9][A-Za-z0-9 _\-.'&]{1,80})",
        message, _re.I,
    ):
        candidate = m.group(1).strip().rstrip("?.!,;:")
        # Skip if candidate is a stop word or too short
        if len(candidate) >= 2 and not _re.match(
            r"^(?:cho|cua|của|of|for|the|a|an|này|đó|nay|do|không|khong|tồn|ton|tại|tai)$", candidate, _re.I
        ):
            # Strip trailing metadata verb fragments: "account có lineage" → "account"
            words = candidate.split()
            clean = []
            for w in words:
                wl = w.lower()
                if wl in _META_NOISE or _re.match(r"^[co]+$", wl):
                    break
                clean.append(w)
            candidate = " ".join(clean) if clean else candidate
            if len(candidate) >= 2 and not _re.match(
                r"^(?:cho|cua|của|of|for|the|a|an|này|đó|nay|do|không|khong|tồn|ton|tại|tai)$", candidate, _re.I
            ):
                return candidate

    # 0b. Single-word entity after entity type keyword.
    _META_VERBS_Q = (
        r"có|co|không|khong|không có|khong co|chưa có|chua co|thiếu|thieu|thuộc|thuoc|"
        r"trên|tren|nào|nao|gì|gi|có thể|co the|được không|duoc khong|tồn tại|ton tai|bao nhiêu|bao nhieu"
    )
    m = _re.search(
        rf"(?:dataset|dashboard|glossary(?:\s+term)?|document|bảng|bang"
        rf"|tai lieu|tài liệu)\s+"
        rf"(?!{_META_VERBS_Q}\b)"
        r"([A-Za-z][A-Za-z0-9_\-]{0,40})",
        message, _re.I,
    )
    if m:
        candidate = m.group(1).strip().rstrip("?.!,;:")
        if len(candidate) >= 2 and not _re.match(
            r"^(?:cho|cua|của|of|for|the|a|an|này|đó|nay|do|không|khong|tồn|ton|tại|tai)$", candidate, _re.I
        ):
            return candidate

    # 3. Short phrase fallback
    if not _anon_is_anaphora(clean_msg):
        if _extract_entity_candidate := _short_phrase(message):
            return _extract_entity_candidate
    return None


def _short_phrase(message: str) -> str | None:
    if _anon_is_anaphora(message):
        return None
    n = _norm(message)
    if not n or _CAPABILITY_VERBS.search(n):
        return None
    words = [w for w in _re.split(r"[\s,;:]+", n) if w and len(w) > 1]
    if not words or len(words) > 3:
        return None
    return message.strip().strip("?.!,;:")


def _resolve_anaphora_from_history(history) -> str | None:
    """Recover the entity referenced by a follow-up (nó/ đó/ this) from recent turns.

    Delegates to the shared coreference resolver which prefers the dataset
    subject of the conversation (a turn mentioning a field like "warehouse_id"
    must not steal the anaphor away from "dim_warehouse").
    """
    from retrieval.coreference import resolve_entity_reference

    return resolve_entity_reference(history)


# Public helpers reused by tests / callers.
KNOWN_ACTIONS = frozenset(_ACTIONS)


# ---------------------------------------------------------------------------
# Resolution result
# ---------------------------------------------------------------------------
@dataclass
class IntentResolution:
    selected_action: str | None
    message_intent: QueryIntent
    intent: QueryIntent                       # final routed intent
    decision: str                             # no_action | agree | override | clarify
    confidence: str                           # high | medium | low
    override_reason: str | None
    chosen_tool: str | None
    entity_hint: str | None
    effective_question: str
    plan: QueryPlan | None
    clarification: str | None = None
    framed: bool = False                       # True when the plan was rebuilt from the action
    trace_id: str | None = None


@dataclass
class _LLMDecision:
    decision: str
    intent: str
    entity: str | None
    confidence: str
    reason: str | None


def _parse_llm_decision(raw: str) -> _LLMDecision | None:
    data = _first_json(raw)
    if not isinstance(data, dict):
        return None
    decision = str(data.get("decision") or "").strip().lower()
    if decision not in ("agree", "override", "clarify"):
        return None
    conf = str(data.get("confidence") or "").strip().lower()
    if conf not in ("high", "medium", "low"):
        conf = "low"
    intent = str(data.get("intent") or "").strip().upper()
    entity = data.get("entity")
    entity = str(entity).strip() if isinstance(entity, str) and entity.strip() else None
    reason = data.get("reason")
    reason = str(reason).strip() if isinstance(reason, str) and reason.strip() else None
    return _LLMDecision(decision=decision, confidence=conf, entity=entity,
                        intent=intent, reason=reason)


def _intent_enum(key: str) -> QueryIntent:
    try:
        return QueryIntent[key]
    except (KeyError, ValueError):
        return QueryIntent.GENERAL


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------
class IntentResolver:
    def __init__(self, llm: BaseLLM | None = None) -> None:
        self._llm = llm

    def _message_intent(self, message: str) -> QueryIntent:
        if _detect_listing(message):
            return QueryIntent.LISTING
        return normalize_intent(classify_intent(message))

    def _tool_for(self, intent: QueryIntent, plan: QueryPlan | None) -> str:
        if plan and (plan.steps or plan.intent in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY")):
            return "planner_dag"
        return _INTENT_TOOL.get(intent, "hybrid_search")

    @staticmethod
    def _finalize_plan(action: ActionSpec, plan: QueryPlan, intent: QueryIntent,
                       entity_hint: str | None, framed: bool) -> QueryPlan:
        if framed:
            refs = [e for e in [entity_hint] if e]
            return QueryPlan(
                intent=intent.value,
                entity_refs=refs,
                entity_type=action.entity_type,
                direction="downstream" if intent == QueryIntent.IMPACT else None,
                confidence="high",
                source="action",
            )
        if entity_hint and not plan.entity_refs:
            plan.entity_refs = [entity_hint]
        if plan.intent != intent.value:
            plan.intent = intent.value
        return plan

    async def _llm_decision(self, action: ActionSpec, message: str,
                            history, trace_id: str | None) -> _LLMDecision | None:
        if self._llm is None or settings.USE_MOCK_LLM:
            return None
        context_rows = "\n".join(
            f"user: {q}\nassistant: {a}" for (q, a) in (history or [])[-4:]
        ) or "(empty)"
        system_prompt = ACTION_RESOLUTION_PROMPT.format(
            action=action.title, action_kind=action.kind,
            message=message, history=context_rows,
        )
        try:
            raw = await self._llm.generate(message, system_prompt=system_prompt)
        except Exception:  # noqa: BLE001
            log.exception("intent_resolver_llm_failed", trace_id=trace_id, action=action.kind)
            return None
        decision = _parse_llm_decision(raw)
        if decision is None:
            log.warning("intent_resolver_llm_unparsed", trace_id=trace_id,
                        action=action.kind, raw=(raw or "")[:120])
        return decision

    async def resolve(self, message: str, selected_action: str | None = None,
                      history: list[tuple[str, str]] | None = None,
                      trace_id: str | None = None) -> IntentResolution:
        # --- 0. Check for confirmation/denial of previous suggestion ---
        # Stateless detection: reads conversation history, no server-side state.
        if history:
            detector = ConfirmationDetector()
            confirmation = detector.detect(message, history)
            if confirmation.action in ("confirm", "deny"):
                log.info("confirmation_detected", trace_id=trace_id,
                         action=confirmation.action,
                         entity=confirmation.entity_name,
                         confidence=confirmation.confidence,
                         reason=confirmation.reason)
                return IntentResolution(
                    selected_action=selected_action,
                    message_intent=QueryIntent.GENERAL,
                    intent=QueryIntent.GENERAL,
                    decision=confirmation.action,
                    confidence="high" if confirmation.confidence >= 0.8 else "medium",
                    chosen_tool="hybrid_search",
                    entity_hint=confirmation.entity_name,
                    effective_question=message,
                    plan=regex_plan(message),
                    framed=False,
                    trace_id=trace_id,
                    override_reason=confirmation.reason,
                )

        msg_intent = self._message_intent(message)
        plan = regex_plan(message)

        # --- Entity name detection ---
        # When the query looks like an entity name (snake_case, dotted path,
        # quoted, high proper-noun ratio) AND no action is selected, override
        # the intent to FIND_ENTITY so it routes through entity resolution fast path.
        # When an action IS selected, let the existing action-routing logic handle it.
        if not selected_action or selected_action not in _ACTIONS:
            detector = EntityNameDetector()
            entity_signal = detector.detect(message)
            if (entity_signal.is_entity_name
                    and msg_intent in (QueryIntent.GENERAL, QueryIntent.SCHEMA_LOOKUP)
                    and entity_signal.extracted_tokens):
                entity_hint = " ".join(entity_signal.extracted_tokens)
                msg_intent = QueryIntent.FIND_ENTITY
                plan.intent = QueryIntent.FIND_ENTITY
                log.info("entity_name_detected", trace_id=trace_id,
                         question=message[:100], signals=entity_signal.signals,
                         confidence=entity_signal.confidence,
                         entity_hint=entity_hint)

        if not selected_action or selected_action not in _ACTIONS:
            chosen = self._tool_for(msg_intent, plan)
            return IntentResolution(
                selected_action=selected_action, message_intent=msg_intent,
                intent=msg_intent, decision="no_action", confidence="high",
                chosen_tool=chosen, entity_hint=None, effective_question=message,
                plan=plan, framed=False, trace_id=trace_id, override_reason=None,
            )

        action = _ACTIONS[selected_action]
        intent = _intent_enum(action.canonical_intent)
        decision = "agree"
        confidence = "high"
        eff_question = message
        entity_hint: str | None = None
        override_reason: str | None = None
        framed = False
        clarification: str | None = None

        anaphor_entity = None
        if _anon_is_anaphora(message):
            anaphor_entity = _resolve_anaphora_from_history(history)

        extracted_ent = _extract_entity(message)

        # --- 1. Explicit conversational / clear request overrides the action ----
        if msg_intent in (QueryIntent.GREETING, QueryIntent.CHITCHAT):
            decision, confidence = "override", "high"
            intent = msg_intent
            override_reason = (
                f"message is {msg_intent.value.lower()}; the explicit conversational "
                f"request wins over the selected action '{selected_action}'"
            )
        # --- 2. Explicit conflicting metadata intent overrides action -----------
        elif (
            msg_intent in _EXPLICIT_METADATA_INTENTS
            and msg_intent.value not in action.expected_intents
            and msg_intent not in (
                QueryIntent.GENERAL,
                QueryIntent.FIND_ENTITY,
                QueryIntent.DATASET_LOOKUP,
            )
            and (extracted_ent or anaphor_entity or _has_entity(message))
        ):
            decision, confidence = "override", "high"
            intent = msg_intent
            entity_hint = extracted_ent or anaphor_entity
            override_reason = (
                f"message expresses explicit intent {msg_intent.value}, which conflicts with "
                f"the selected action '{selected_action}'; prioritizing the user's explicit request"
            )

        # --- 3. Anaphoric follow-up ("nó", "this", "dataset này") -> resolve from history ---
        elif anaphor_entity:
            entity_hint = anaphor_entity
            decision, confidence, intent = "agree", "high", _intent_enum(action.canonical_intent)
            eff_question = f"{action.prompt.strip()} {anaphor_entity}".strip()
            framed = True
        # --- 4. Entity provided in message (short or full query) under the action ---
        elif extracted_ent:
            entity_hint = extracted_ent
            decision, confidence, intent = "agree", "high", _intent_enum(action.canonical_intent)
            eff_question = f"{action.prompt.strip()} {extracted_ent}".strip()
            framed = True
        # --- 5. Message has no explicit entity but is under an active action context ---
        else:
            if selected_action == "search":
                # General semantic discovery search / listing
                decision, confidence = "agree", "high"
                intent = QueryIntent.LISTING if msg_intent == QueryIntent.LISTING else QueryIntent.FIND_ENTITY
                eff_question = message
                entity_hint = message
                framed = False
            elif _anon_is_anaphora(message):
                hist_entity = _resolve_anaphora_from_history(history)
                if hist_entity:
                    entity_hint = hist_entity
                    decision, confidence, intent = "agree", "high", _intent_enum(action.canonical_intent)
                    eff_question = f"{action.prompt.strip()} {hist_entity}: {message}".strip()
                    framed = True
                else:
                    decision, confidence, intent = "clarify", "low", _intent_enum(action.canonical_intent)
                    clarification = action.clarification
            else:
                decision, confidence, intent = "clarify", "low", _intent_enum(action.canonical_intent)
                clarification = action.clarification


        if entity_hint and _anon_is_anaphora(entity_hint):
            ref_entity = _resolve_anaphora_from_history(history)
            if ref_entity:
                entity_hint = ref_entity
        elif not entity_hint and _anon_is_anaphora(message):
            ref_entity = _resolve_anaphora_from_history(history)
            if ref_entity:
                entity_hint = ref_entity

        plan = self._finalize_plan(action, plan, intent, entity_hint, framed)
        chosen_tool = self._tool_for(intent, plan)

        log.info(
            "intent_resolution",
            trace_id=trace_id,
            selected_action=selected_action,
            action_title=action.title,
            message_intent=msg_intent.value,
            intent=intent.value,
            decision=decision,
            confidence=confidence,
            chosen_tool=chosen_tool,
            override_reason=override_reason,
            entity_hint=entity_hint,
            framed=framed,
            plan_source=plan.source,
            message=message[:120],
        )

        return IntentResolution(
            selected_action=selected_action, message_intent=msg_intent, intent=intent,
            decision=decision, confidence=confidence, override_reason=override_reason,
            chosen_tool=chosen_tool, entity_hint=entity_hint,
            effective_question=eff_question, plan=plan, clarification=clarification,
            framed=framed,
        )
