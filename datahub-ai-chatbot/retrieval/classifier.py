"""Semantic intent classifier.

The classifier asks the LLM to interpret a user question about DataHub metadata
into a structured ``QueryPlan`` (intent, entity refs, filters, direction, params,
composite flag). It defaults to the existing keyword/regex router when the LLM is
unavailable, disabled, or yields a low-confidence / unparsable result, so the
chat pipeline degrades gracefully instead of hard-failing.
"""

from __future__ import annotations

import json
import re

import structlog

from config.prompts import SEMANTIC_INTENT_PROMPT
from config.settings import settings
from llm.base import BaseLLM
from retrieval.intent import classify_intent
from retrieval.query_models import QueryFilter, QueryParams, QueryPlan

log = structlog.get_logger()

# Intent strings the LLM may emit, mapped onto the service vocabulary.
VALID_INTENTS = {
    "TERM_DEFINITION", "FIND_ENTITY", "OWNER_LOOKUP", "TERM_TO_DATASETS",
    "LINEAGE", "LINEAGE_UPSTREAM", "LINEAGE_DOWNSTREAM",
    "IMPACT", "IMPACT_ANALYSIS", "RECURSIVE_IMPACT",
    "SCHEMA_LOOKUP", "FIELD_LOOKUP", "DATASET_LOOKUP", "DOMAIN_LOOKUP",
    "COMPOSITE_QUERY", "GRAPH_QUERY", "RELATED_DATASETS",
    "SEMANTIC_SEARCH", "MULTI_ENTITY_QUERY",
    "ENTITY_DOMAIN", "COUNT_ENTITIES",
    "DOMAIN_QUERY", "PLATFORM_QUERY", "TAG_QUERY", "ENTITIES_BY_OWNER",
    "CERTIFIED_LIST", "DOCUMENT_QA", "DATAHUB_URL", "ENTITY_EXISTS",
    "LISTING", "GREETING", "CHITCHAT", "GENERAL", "COMPARISON",
}

# Normalize a classifier-returned intent to the intent the service executes.
_INTENT_CANON: dict[str, str] = {
    "IMPACT_ANALYSIS": "IMPACT",
    "RECURSIVE_IMPACT": "IMPACT",
    "LINEAGE_UPSTREAM": "LINEAGE",
    "LINEAGE_DOWNSTREAM": "LINEAGE",
    "DATASET_LOOKUP": "FIND_ENTITY",
    "DOMAIN_LOOKUP": "ENTITY_DOMAIN",
    "FIELD_LOOKUP": "SCHEMA_LOOKUP",
    "RELATED_DATASETS": "FIND_ENTITY",
    "GRAPH_QUERY": "GENERAL",
    "SEMANTIC_SEARCH": "GENERAL",
    "MULTI_ENTITY_QUERY": "GENERAL",
}


def _canon_intent(intent: str) -> str:
    return _INTENT_CANON.get(intent, intent)

_DIMENSIONS = {"domain", "platform", "tag", "owner", "certified"}

# Deterministic pre-checks that run before/alongside the LLM so a clear
# downstream-impact question is never miscast as plain LINEAGE.
_IMPACT_RE = re.compile(
    r"(ảnh hưởng|anh huong|bị\s?tác động|bi tac dong|impact|cascade|dây chuyền|day chuyen|"
    r"who\s+(uses|consumes|depends on)|phụ thuộc xuống|phu thuoc xuong|lan\s+truyền|lan truyen|"
    r"mức độ rủi ro|muc do rui ro|rủi ro.*khi|rui ro.*khi|risk\s+level|"
    r"điều gì.*dùng|dieu gi.*dung|"
    r"(?:xóa|xoá|xoa|delete|drop|remove|thay đổi|thay doi)\b[^\n]{0,90}?"
    r"(?:thì sao|thi sao|thế nào|the nao|ra gì|ra gi|sẽ ra sao|se ra sao|what happens|"
    r"what would happen|consequence|effect|xảy ra gì|xay ra gi)|"
    r"(?:ảnh hưởng|anh huong|impact|affected|effect)\b[^\n]{0,90}?"
    r"(?:của việc xóa|cua viec xoa|of (?:deleting|dropping|removing)|khi (?:xóa|xoa|delete))|"
    r"(?:xóa|xoá|xoa|delete|drop|remove|thay đổi|thay doi)\b[^\n]{0,80}?"
    r"(?:ảnh hưởng|anh huong|impact|affected))",
    re.I,
)
_LINEAGE_RE = re.compile(
    r"(lineage|linage|nguồn|nguon|upstream|downstream|dòng dữ liệu|dong du lieu|"
    r"data flow|luồng dữ liệu|luong du lieu|gửi dữ liệu|gui du lieu|đẩy dữ liệu|day du lieu|"
    r"chảy sang|chay sang|truyền dữ liệu|truyen du lieu)",
    re.I,
)
_DIRECTION_RE = re.compile(r"(downstream|xuống|xuoi|xuong|dưới|sang|toi|tới)", re.I)


_SCHEMA_PLACEHOLDER = re.compile(
    r'^\s*\{\s*"type"\s*:\s*"(?:object|array)"\s*\}\s*$', re.I
)


def _is_schema_placeholder(obj: object) -> bool:
    """True when ``obj`` is the JSON-schema descriptor the LLM sometimes echoes
    (e.g. ``{"type": "object"}``) instead of a real answer payload.

    Root cause: Fireworks is forced into ``response_format={"type": "json_object"}``
    and, when the model produces only the schema shape, the parser would otherwise
    treat it as a valid plan/generation payload, leaking ``{"type":"object"}``.
    """
    if isinstance(obj, dict):
        return set(obj.keys()) == {"type"}
    if isinstance(obj, str) and _SCHEMA_PLACEHOLDER.match(obj):
        return True
    return False


def _first_json(raw: str) -> object:
    """Extract the first JSON value (object or array) from ``raw``."""
    if not raw:
        return None
    if _SCHEMA_PLACEHOLDER.match(raw):
        return None
    try:
        parsed = json.loads(raw)
        return None if isinstance(parsed, dict) and _is_schema_placeholder(parsed) else parsed
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == opener:
                depth += 1
            elif cleaned[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        candidate = json.loads(cleaned[start:i + 1])
                        if _is_schema_placeholder(candidate):
                            break
                        return candidate
                    except json.JSONDecodeError:
                        break
    return None


def _clean_entities(refs: object) -> list[str]:
    if not refs:
        return []
    if isinstance(refs, str):
        return [refs.strip()] if refs.strip() else []
    if isinstance(refs, (list, tuple)):
        out: list[str] = []
        for r in refs:
            if isinstance(r, str) and r.strip():
                out.append(r.strip())
            elif isinstance(r, (int, float)):
                out.append(str(r))
        return out
    return []


def _parse_llm_plan(raw: str) -> QueryPlan | None:
    data = _first_json(raw)
    if not isinstance(data, dict):
        return None
    intent = str(data.get("intent") or "").strip().upper()
    if intent not in VALID_INTENTS:
        intent = "GENERAL"
    intent = _canon_intent(intent)

    f = data.get("filter") or {}
    dimension = (f.get("dimension") or "").strip().lower() if isinstance(f, dict) else ""
    if dimension not in _DIMENSIONS:
        dimension = None
    qfilter = QueryFilter(
        dimension=dimension,
        value=(f.get("value") or None) if isinstance(f, dict) else None,
    )

    params = data.get("params") or {}
    params = params if isinstance(params, dict) else {}
    depth = params.get("depth")
    top_k = params.get("top_k")
    try:
        depth = int(depth) if depth not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        depth = None
    try:
        top_k = int(top_k) if top_k not in (None, "") else None
    except (TypeError, ValueError):
        top_k = None

    direction = (data.get("direction") or "").strip().lower()
    if direction not in ("upstream", "downstream", "both"):
        direction = None
    entity_type = (data.get("entity_type") or "").strip().lower() or None
    if entity_type not in ("dataset", "dashboard", "glossary_term", "document"):
        entity_type = None

    conf = (data.get("confidence") or "").strip().lower()
    if conf not in ("high", "medium", "low"):
        conf = "medium"

    return QueryPlan(
        intent=intent,
        entity_refs=_clean_entities(data.get("entity_refs")),
        entity_type=entity_type,
        filter=qfilter,
        direction=direction,
        params=QueryParams(depth=depth, top_k=top_k, raw=params),
        is_composite=bool(data.get("is_composite")),
        confidence=conf,
        source="classifier",
    )


def _regex_entity(question: str) -> list[str]:
    """Lightweight entity-name guess for the regex fallback (no imports)."""
    q = question.strip().strip("?.!")
    if not q:
        return []
    # Drop common leading verbs/prepositions and question words.
    stop = [
        "cho toi biet", "xin cho biet", "hay cho biet", "trinh bay", "mo ta",
        "tim hieu", "hieu", "roliệt", "liet ke", "danh sach", "list", "show",
        "huong dan", "giai thich", "don sac", "biet", "ve", "cua", "va",
        "la", "gi", "nao", "giup", "nhung", "cac", "dinh nghia ve",
    ]
    name = question.lower()
    for w in stop:
        name = name.replace(w, " ")
    import unicodedata
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    tokens = [t for t in re.split(r"[\s,_\-.:]+", norm) if t]
    keep = [t for t in tokens if len(t) > 2]
    if not keep:
        return []
    return [" ".join(keep)]


_COMPARE_RE = re.compile(
    r"\b(?:so sánh|so sanh|compare|comparison|comparing|phù hợp hơn|phu hop hon|đối chiếu|doi chieu|khác nhau|khac nhau|versus|\bvs\.?)\b",
    re.I,
)


def _regex_plan(question: str) -> QueryPlan:
    """Build a ``QueryPlan`` from the existing keyword/regex router."""
    if _COMPARE_RE.search(question):
        return QueryPlan(
            intent="COMPARISON",
            entity_refs=_regex_entity(question),
            direction=None,
            confidence="high",
            source="regex",
        )

    intent = classify_intent(question)

    if _IMPACT_RE.search(question):
        return QueryPlan(
            intent="IMPACT",
            entity_refs=_regex_entity(question),
            direction="downstream",
            confidence="medium",
            source="regex",
        )

    if intent in ("LINEAGE", "GENERAL") and _LINEAGE_RE.search(question):
        direction = "downstream" if _DIRECTION_RE.search(question) else "both"
        return QueryPlan(
            intent="LINEAGE",
            entity_refs=_regex_entity(question),
            direction=direction,
            confidence="medium",
            source="regex",
        )

    return QueryPlan(
        intent=intent.value,
        entity_refs=_regex_entity(question),
        direction=None,
        confidence="medium",
        source="regex",
    )


def regex_plan(question: str) -> QueryPlan:
    """Fast, deterministic fallback plan built from the keyword router (no LLM)."""
    return _regex_plan(question)


# Regex intents the router decides deterministically and that must NOT be
# downgraded by a weaker LLM label (e.g. term->datasets must never become a
# generic FIND_ENTITY — the linkage signal is exact).
_STRONG_REGEX_INTENTS = {
    "TERM_TO_DATASETS", "COUNT_ENTITIES", "LINEAGE", "OWNER_LOOKUP",
    "ENTITY_DOMAIN", "DOMAIN_QUERY", "PLATFORM_QUERY", "TAG_QUERY",
    "CERTIFIED_LIST", "LISTING", "GREETING", "CHITCHAT", "DATAHUB_URL",
    "ENTITIES_BY_OWNER", "IMPACT", "COMPARISON",
}

# LLM intents allowed to REPLACE a weak regex intent for routing. Kept to the
# labels that resolve ambiguous discovery / linkage questions the regex router
# first-match-wins mistakes (R1: the LLM, not the regex, is the primary intent
# analyzer; regex stays as fast-path + validation).
_LLM_OVERRIDE_CAPABLE = {"FIND_ENTITY", "TERM_TO_DATASETS", "COMPARISON"}

_SCHEMA_ANCHOR_RE = re.compile(
    r"(?:trường|cột|cột|field|column)\b[^\n]{0,30}?"
    r"\b(?:của|cua|trong|trong|nào|nao|la gi|nghĩa|nghia)\b",
    re.I,
)


def llm_intent_override(regex_intent: str, plan: QueryPlan, question: str,
                        has_field_identifier: bool = False) -> str | None:
    """Routing intent when the LLM plan should replace the regex ``regex_intent``.

    Returns the canonical intent string, or None to keep the regex routing.
    Guards (never let the LLM downgrade a precise signal):
    - the plan must come from the LLM with high/medium confidence;
    - strong structural regex intents (term linkage, count, lineage, owner,
      domain/platform/tag lists, impact...) stay on regex;
    - SCHEMA_LOOKUP with an explicit field/property anchor stays SCHEMA_LOOKUP
      even when the LLM broadens it to FIND_ENTITY.
    """
    if plan is None or plan.source != "classifier":
        return None
    if plan.confidence not in ("high", "medium"):
        return None
    llm_intent = plan.intent
    if llm_intent not in _LLM_OVERRIDE_CAPABLE:
        return None
    if regex_intent in _STRONG_REGEX_INTENTS:
        return None
    if regex_intent == "SCHEMA_LOOKUP":
        if has_field_identifier or _SCHEMA_ANCHOR_RE.search(question):
            return None
    return llm_intent if llm_intent != regex_intent else None


def needs_semantic(question: str, intent: str) -> bool:
    """Whether the LLM classifier is worth running for ``question``.

    Runs for ambiguous / lineage / impact / discovery-shaped questions where the
    keyword router's first-match-wins can misfire (e.g. a description-based
    "có báo cáo nào về X?" misread as SCHEMA_LOOKUP because of a stray word).
    Deterministic fast-path intents (count, listing, term linkage...) skip the
    LLM call to keep the common path cheap.
    """
    if question and _IMPACT_RE.search(question):
        return True
    return intent in (
        "GENERAL", "LINEAGE", "FIND_ENTITY", "DOCUMENT_QA",
        "SCHEMA_LOOKUP", "ENTITY_EXISTS", "COMPARISON",
    )


async def classify(question: str, llm: BaseLLM) -> QueryPlan:
    """Classify ``question`` into a ``QueryPlan``.

    Uses the LLM when enabled (and real); otherwise the regex router.
    """
    if not settings.INTENT_CLASSIFIER_ENABLED or settings.USE_MOCK_LLM:
        plan = _regex_plan(question)
        log.info("semantic_intent", question=question[:100], intent=plan.intent,
                 source="regex", entities=len(plan.entity_refs))
        return plan

    try:
        raw = await llm.generate(question, system_prompt=SEMANTIC_INTENT_PROMPT)
    except Exception:  # noqa: BLE001
        log.exception("semantic_intent_failed", question=question[:120])
        return _regex_plan(question)

    plan = _parse_llm_plan(raw) or _regex_plan(question)
    log.info("semantic_intent", question=question[:120], intent=plan.intent,
             source=plan.source, entities=len(plan.entity_refs), composite=plan.is_composite)
    return plan
