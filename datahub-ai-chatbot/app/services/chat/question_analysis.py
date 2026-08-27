import re
from collections.abc import Sequence
from typing import Any

import structlog

from app.auth.models import UserContext
from config.settings import settings
from retrieval.entity_resolver import ResolutionResult
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent, _norm_vn

# Listing patterns - must NOT contain a specific entity name before the pattern
_LISTING_TYPES = r'(datasets?|dashboards?|glossary(?:\s+terms?)?|documents?|tài liệu|tai lieu)'
_LISTING_TYPES_EN = r'(datasets|dashboards|glossary\s+terms|documents)'
_LISTING_PREFIX = r'(?:(?:trong|in)\s+(?:hệ thống|he thong|system)\s+)?'

_LISTING_PATTERNS: list[re.Pattern] = [
    re.compile(
        rf'^{_LISTING_PREFIX}(?:có các|các)\s+{_LISTING_TYPES}\s+'
        r'(?:gì|nào)\??$',
        re.I,
    ),
    re.compile(rf'^{_LISTING_PREFIX}(?:có các|các)\s+{_LISTING_TYPES}\s*$', re.I),
    re.compile(rf'^liệt kê\s+(?:các\s+)?{_LISTING_TYPES}\s*$', re.I),
    re.compile(rf'^list\s+(?:all\s+)?{_LISTING_TYPES_EN}\s*$', re.I),
    re.compile(rf'^danh sách\s+(?:các\s+)?{_LISTING_TYPES}\s*$', re.I),
    re.compile(rf'^show\s+(?:all\s+)?{_LISTING_TYPES_EN}\s*$', re.I),
    re.compile(rf'^{_LISTING_PREFIX}có những {_LISTING_TYPES} nào\??$', re.I),
    # "có những document(s) (nào)?" — no verb, singular/plural type word.
    re.compile(
        rf'^{_LISTING_PREFIX}có (?:những|các)\s+{_LISTING_TYPES}'
        r'(?:\s+(?:nào|gì))?\s*\??$',
        re.I,
    ),
    # Trailing system scope is stripped by _detect_listing, but keep a direct
    # variant so the pattern also works without that normalisation.
    re.compile(
        rf'^{_LISTING_PREFIX}có những {_LISTING_TYPES} nào'
        r'(?:\s+(?:trong|in)\s+(?:hệ thống|he thong|system))?\s*\??$',
        re.I,
    ),
    re.compile(
        rf'^{_LISTING_PREFIX}(?:what|which)\s+{_LISTING_TYPES_EN}'
        r'(?:\s+are)?(?:\s+available)?(?:\s+in the system)?\s*\??$',
        re.I,
    ),
]

_LISTING_TYPE_MAP: dict[str, str] = {
    "dataset": "dataset",
    "dashboard": "dashboard",
    "glossary": "glossary_term",
    "glossary term": "glossary_term",
    "glossary_term": "glossary_term",
    "document": "document",
    "documents": "document",
    "tài liệu": "document",
    "tai lieu": "document",
    "tailieu": "document",
}

_FILTER_VALUE_PATTERNS: dict[QueryIntent, list[str]] = {
    QueryIntent.DOMAIN_QUERY: [
        r"(?:domain|mien|linh vuc)\s*[:=]?\s*([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
        r"(?:trong|thuoc|in|belonging to|belong to)\s+(?:the\s+)?"
        r"(?:domain|mien|linh vuc)\s+([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
    ],
    QueryIntent.PLATFORM_QUERY: [
        r"(?:platform|nen tang)\s*[:=]?\s*([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
        r"(?:tren|trong|on|in)\s+(?:platform|nen tang)?\s*([a-z0-9\.\-]+)",
    ],
    QueryIntent.TAG_QUERY: [
        r"(?:tag|tagged|with tag|co tag|duoc gan tag|voi tag|gan tag)\s*[:=]?\s*"
        r"([a-z0-9\.\-]+(?:\s+[a-z0-9\.\-]+)?)",
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
    QueryIntent.MISSING_DESCRIPTION,
    QueryIntent.MISSING_OWNER,
    QueryIntent.MISSING_DOMAIN,
}

_QUALITY_FAVORED_INTENTS = frozenset({
    QueryIntent.FIND_ENTITY,
    QueryIntent.DATASET_LOOKUP,
    QueryIntent.GENERAL,
    QueryIntent.QUALITY_CHECK,
})

_METADATA_REPORT_RE = re.compile(
    r"(?:metadata\s*report|báo\s*cáo\s*metadata|bao\s*cao\s*metadata|"
    r"report\s*metadata|tổng\s*quan\s*metadata|tong\s*quan\s*metadata)",
    re.I,
)

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
    r"danh sách (các )?domain|danh sách (các )?lĩnh vực|danh sach domain|"
    r"danh sach cac domain|danh sach linh vuc|"
    r"domain nào trong hệ thống|domain trong hệ thống|các domain trong hệ thống|"
    r"domain nao trong he thong|domain trong he thong|"
    r"có bao nhiêu domain|có bao nhiêu lĩnh vực|co bao nhieu domain|"
    r"how many domain)",
    re.I,
)

log = structlog.get_logger()

# Multi-hop chain: "từ report capacity → định nghĩa → cột → công thức → nguồn
# dữ liệu thô" (arrow chain) or "trong domain X tìm report về Y, term liên
# quan, dataset nguồn và lineage" (comma chain). Walked hop by hop, missing
# hops marked UNKNOWN. Must win over SCHEMA_LOOKUP / LINEAGE / TERM_DEFINITION.
_MULTI_HOP_CHAIN_RE = re.compile(
    r"(?:→|->|➔|⇒|arrow|chuỗi|chained|hop\b)|"
    r"(?:từ|tu|from)\s+[\w\.\- ]{1,40}\s*(?:→|->)|"
    r"(?:tìm|tim|find)\s+(?:report|báo cáo|bao cao)\b[^\n]{0,120}\b"
    r"(?:term|thuật ngữ|thuat ngu|lineage|nguồn|nguon|dataset nguồn)",
    re.I,
)

# Join / schema-relationship vocabulary. "Trong fact_sales_order, trường nào dùng
# để liên kết dim_warehouse?" is a schema-join question — the intent router hears
# "trường" and would otherwise run generic SCHEMA_LOOKUP that turns the whole
# sentence into an entity name.
_JOIN_SIGNAL_RE = re.compile(
    r"(?:liên kết|lien ket|\bjoin(s|ed|ing)?\b|khóa ngoại|khoa ngoai|"
    r"nối với|noi voi|\blink(?:ed|s)?\b|mối quan hệ giữa|moi quan he giua|"
    r"giữa .*\bvà\b.*(?:trường|field|dataset|bảng)|"
    r"between .*\band\b.*(?:field|column|dataset|table)|"
    r"relationship between|quan hệ giữa|relate|"
    r"trường nào chung|truong nao chung|trường chung|truong chung|"
    r"common (?:fields?|columns?|keys?)|shared (?:fields?|columns?|keys?)|"
    r"fields? in common|giống nhau|giong nhau)",
    re.IGNORECASE,
)
_JOIN_TOKEN_RE = re.compile(
    r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+|[a-z0-9]+_[a-z0-9_]+",
    re.IGNORECASE,
)
# Field-synchronisation / data-mapping questions: "warehouse_id được sync với
# gì?", "cột này được đồng bộ với những bảng nào?", "X map với gì?". These ask
# WHERE a column is duplicated across tables (the join keys), i.e. a deterministic
# schema-relationship answer, not a free-form topic overview.
_SYNC_RE = re.compile(
    r"(?:được\s+)?(?:sync(?:hronize|hronized|hronization)?|đồng bộ|dong bo|"
    r"map(?:ped|ping)?|ánh xạ|anh xa|liên kết dữ liệu|lien ket du lieu)\s*"
    r"(?:với|voi|sang|to|tu|theo)?\s*(?:những|those|which|bảng|bang|table)?\s*"
    r"(?:gì|gi|nao|nào|cái gì|cai gi|what)",
    re.IGNORECASE,
)
# Concept-to-dataset questions: "Có tồn tại dataset nào liên quan đến khái niệm
# doanh thu?" / "...khái niệm X" asks to map a business concept to the datasets
# that carry it (glossary-linked). These must route to TERM_TO_DATASETS, never to
# generic entity ambiguity or entity-existence checks.
_CONCEPT_TO_DATASETS_RE = re.compile(
    r"(?:^(?:cho tôi biết\s+)?[A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?\s+(?:được|duoc)\s+(?:sử dụng|su dung|dùng|dung|chứa|chua|lưu|luu|ghi nhận|ghi nhan)\s+(?:trong|ở|tai)\s+(?:các\s+|những\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao))"
    r"|(?:(?:có\s+|những\s+|tìm\s+|các\s+|danh sách\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)[^?]{0,50}?(?:liên quan|lien quan|relat(?:e|ed)?)\s*(?:đến|den|to)?\s*(?:khái niệm|khai niem|thuật ngữ|thuat ngu|concept|term)?)"
    r"|(?:(?:có\s+|những\s+|tìm\s+|các\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)[^?]{0,50}?(?:phục vụ|phuc vu|dùng để|dung de|có thể dùng để|co the dung de|dùng cho|dung cho|phân tích|phan tich|theo dõi|theo doi)\s+)"
    r"|(?:(?:có\s+|những\s+|tìm\s+|các\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)[^?]{0,50}?(?:chứa thông tin|chua thong tin|lưu thông tin|luu thong tin|có thông tin|co thong tin)\s+(?:về|ve)\s+)"
    r"|(?:(?:khái niệm|khai niem|thuật ngữ|thuat ngu|concept|term)\s+[A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?\s+(?:được|duoc|nằm|nam|có|co|liên quan|lien quan))",
    re.IGNORECASE,
)
# Term->datasets ASK: "tìm dataset tính/chứa/lưu nhu cầu linh kiện", "dataset
# nào dựa trên <term>". The concept after the ask verb is a glossary term whose
# linked datasets are the answer ("nhu cầu linh kiện" -> mrp_stock_req). Must
# NOT hijack field-location or column-meaning asks (guarded by the caller).
_TERM_TO_DATASETS_ASK_RE = re.compile(
    r"(?:dataset|bảng|bang|table)[^?]{0,40}?"
    r"\b(?:tính|tinh|chứa|chua|dựa|dua|lưu|luu|ghi|lấy|lay|nắm|nam)\b\s+",
    re.IGNORECASE,
)
# Extracts the concept phrase that follows concept-to-dataset patterns so the
# term->datasets flow resolves the right term.
_CONCEPT_PHRASE_RE = re.compile(
    r"(?:liên quan|lien quan|relat(?:e|ed)?)\s*(?:đến|den|to)?\s*"
    r"(?:khái niệm|khai niem|thuật ngữ|thuat ngu|concept|term)?\s*([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)"
    r"(?:\s+không|\s+khong|[.!?]|$)"
    r"|(?:khái niệm|khai niem|concept)\s+([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)(?:[.!?]|$)"
    r"|(?:term|thuật ngữ|thuat ngu)\s+(?:nào|nao)\s+liên quan\s*"
    r"(?:đến|den|to)?\s+([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)(?=\s+(?:và|va)\s+|\s*$)",
    re.IGNORECASE,
)


def extract_concept_phrase(question: str) -> str | None:
    """Extract concept name from concept-to-dataset discovery questions."""
    q = question.strip()
    m1 = re.search(
        r"^(?:cho tôi biết\s+)?([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)\s+(?:được|duoc)\s+(?:sử dụng|su dung|dùng|dung|chứa|chua|lưu|luu|ghi nhận|ghi nhan)\s+(?:trong|ở|tai)\s+(?:các\s+|những\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)",
        q, re.I,
    )
    if m1:
        return m1.group(1).strip()

    m2 = re.search(
        r"(?:có\s+|những\s+|tìm\s+|các\s+|danh sách\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)[^?]{0,50}?(?:liên quan|lien quan|relat(?:e|ed)?)\s*(?:đến|den|to)\s*(?:khái niệm|khai niem|thuật ngữ|thuat ngu|concept|term)?\s*([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)(?:\s+không|\s+khong|\?|$)",
        q, re.I,
    )
    if m2:
        res = m2.group(1).strip()
        res = re.sub(r"\s+(?:không|khong|\?)$", "", res, flags=re.I).strip()
        if res:
            return res

    m3 = re.search(
        r"(?:có\s+|những\s+|tìm\s+|các\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)[^?]{0,50}?(?:phục vụ|phuc vu|dùng để|dung de|có thể dùng để|co the dung de|dùng cho|dung cho|phân tích|phan tich|theo dõi|theo doi)\s+(?:phân tích\s+|theo dõi\s+)?([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)(?:\s+không|\s+khong|\?|$)",
        q, re.I,
    )
    if m3:
        res = m3.group(1).strip()
        res = re.sub(r"\s+(?:không|khong|\?)$", "", res, flags=re.I).strip()
        if res:
            return res

    m4 = re.search(
        r"(?:có\s+|những\s+|tìm\s+|các\s+)?(?:dataset|bảng|bang|table|dữ liệu|du lieu|báo cáo|bao cao)[^?]{0,50}?(?:chứa thông tin|chua thong tin|lưu thông tin|luu thong tin|có thông tin|co thong tin)\s+(?:về|ve)\s+([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)(?:\s+không|\s+khong|\?|$)",
        q, re.I,
    )
    if m4:
        res = m4.group(1).strip()
        res = re.sub(r"\s+(?:không|khong|\?)$", "", res, flags=re.I).strip()
        if res:
            return res

    m5 = re.search(
        r"(?:khái niệm|khai niem|thuật ngữ|thuat ngu|concept|term)\s+([A-Za-zÀ-ỹ0-9 \(\)\-_\.\/]+?)(?=\s+(?:được|duoc|nằm|nam|có|co|liên quan|lien quan)|\?|$)",
        q, re.I,
    )
    if m5:
        return m5.group(1).strip()

    return None


# --------------------------------------------------------------------------- #
# Contextual follow-up detection (anaphora + ellipsis + demonstratives).
#
# A follow-up such as "nó thuộc domain nào?", "bảng này thuộc về ai?",
# "có các trường nào?" or "dataset đó có glossary không?" carries NO entity of
# its own — it must be resolved against the conversation context BEFORE any
# router (thinking mode, hybrid search...) runs, otherwise it is re-searched as
# a brand-new query and answers about the wrong thing. This helper is the single
# gate that recognises those turns so the coreference-aware routing takes over.
# --------------------------------------------------------------------------- #
_CONTEXTUAL_PRONOUN_RE = re.compile(
    r"\b(?:nó|đó|ấy|này|đây|kia|chúng|chung)\b", re.I,
)
_CONTEXTUAL_ASCII_RE = re.compile(r"\b(?:no|do|ay|nay|day|kia|chung)\b", re.I)
_CONTEXTUAL_DEMONSTRATIVE = re.compile(
    r"(?:bảng|bang|dataset|table|trường|truong|field|cột|cot|cái|cai|thằng|thang|"
    r"entity|term|document|tài liệu|tai lieu|đối tượng|doi tuong|schemas?)[\s\-]+"
    r"(?:này|nay|đó|do|kia|đấy|day|ấy|ay|trên|tren|trước|truoc|đang xét|dang xet|"
    r"hiện tại|hien tai|vừa rồi|vua roi|vừa nãy|vua nay)\b",
    re.I,
)
# Capability-ellipsis: no identifier of its own, but clearly a follow-up that
# asks about an attribute of the previously discussed entity.
_CONTEXTUAL_ELLIPSIS = re.compile(
    r"(?:có các trường|có những trường|co cac truong|co nhung truong|"
    r"có những field|co nhung field|có các field|co cac field|có field|co field|"
    r"có những cột|có các cột|co nhung cot|co cac cot|"
    r"schema là gì|schema la gi|schema của nó|schema cua no|"
    r"có schema|co schema|có glossary|có glossary term|có thuật ngữ|co thuat ngu|"
    r"thuộc về ai|thuoc ve ai|thuộc ai|thuoc ai|thuộc về|có owner|có domain|có url|"
    r"thuộc domain nào|thuoc domain nao|thuộc lĩnh vực nào|thuoc linh vuc nao|"
    r"lấy dữ liệu từ đâu|lay du lieu tu dau|upstream là gì|downstream là gì|"
    r"ai sở hữu|ai so huu|owner là ai|owner la ai|owner của|có link|có document|"
    r"có tài liệu|có bao nhiêu trường|co bao nhieu truong|bị ảnh hưởng gì|"
    r"bi anh huong gi|ảnh hưởng gì|anh huong gi|thuộc lĩnh vực|thuoc linh vuc)",
    re.I,
)
_contextual_identifier_re = re.compile(
    r"[A-Za-z0-9_]{2,}(?:\.[A-Za-z0-9_]+)+|[a-z0-9]{2,}_[a-z0-9_]+", re.I,
)

# A question that refers back to an uploaded image (ảnh/hình/bảng này/nó/đây...).
# IMAGE IS CONTEXT, NOT INTENT: only questions carrying an explicit image
# reference may be answered directly from the Image Context; every other question
# routes through the normal pipeline with the image-derived entity as a hint.
_IMAGE_REF_RE = re.compile(
    r"ảnh|hình|bang nay|nó|no[.? ]|đó|do[.? ]|đây|day|này|nay[.? ]|kia|trên|"
    r"anh nay|hinh|bang",
    re.I,
)


def _has_own_identifier(question: str) -> bool:
    """True when the message itself names a concrete catalog identifier."""
    if bool(_contextual_identifier_re.search(question or "")):
        return True
    from retrieval.query_parser import _extract_entity
    ent = _extract_entity(question or "")
    return ent is not None


# --------------------------------------------------------------------------- #
# Evidence-kind helpers: map an intent / payload to a structured evidence kind
# --------------------------------------------------------------------------- #
def _normalize_field(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "_")


def _evidence_kind_for_intent(intent: "QueryIntent", payload: dict) -> str | None:
    if intent in (QueryIntent.SCHEMA_LOOKUP,):
        return "schema"
    if intent in (QueryIntent.LINEAGE, QueryIntent.IMPACT):
        return "lineage"
    if intent == QueryIntent.OWNER_LOOKUP:
        return "owner"
    if intent == QueryIntent.ENTITY_DOMAIN:
        return "domain"
    if intent == QueryIntent.TERM_DEFINITION:
        return "glossary"
    if intent == QueryIntent.SQL_GENERATION:
        return "sql"
    if intent == QueryIntent.TERM_TO_DATASETS:
        return "glossary"
    if intent == QueryIntent.DATASET_LOOKUP or intent == QueryIntent.FIND_ENTITY:
        if payload.get("schema_fields"):
            return "schema"
        if payload.get("upstreams") or payload.get("downstreams"):
            return "lineage"
        return "dataset"
    if payload.get("schema_fields"):
        return "schema"
    if payload.get("upstreams") or payload.get("downstreams"):
        return "lineage"
    if payload.get("owners"):
        return "owner"
    return "dataset"


def _evidence_tool_name(intent: "QueryIntent") -> str:
    return {
        QueryIntent.SCHEMA_LOOKUP: "schema_lookup",
        QueryIntent.LINEAGE: "lineage",
        QueryIntent.IMPACT: "impact",
        QueryIntent.OWNER_LOOKUP: "owner_lookup",
        QueryIntent.ENTITY_DOMAIN: "domain_lookup",
        QueryIntent.TERM_DEFINITION: "term_definition",
        QueryIntent.SQL_GENERATION: "sql_generator",
    }.get(intent, "retrieval")


def _extract_join_field(question: str) -> str | None:
    """A snake_case *_id/_key/_code field named by the user."""
    m = re.search(r"\b([a-z0-9]+(?:_[a-z0-9]+){1,}?(?:_id|_key|_code))\b",
                  (question or "").lower())
    return _normalize_field(m.group(1)) if m else None


def _extract_lineage_keyword(question: str) -> str | None:
    """The subject a lineage filter targets ("liên quan đến tồn kho")."""
    m = re.search(
        r"(?:liên quan|lien quan|liên tới|lien toi|relate|related|involve)[^a-z0-9]+"
        r"([a-zà-ỹ0-9_ ]+?)(?:\?|$|\.|\s+(?:không|ko|nao|nào))",
        (question or "").lower(),
    )
    if not m:
        return None
    kw = m.group(1).strip()
    if not kw or len(kw) > 40:
        return None
    return kw


def _find_target_entity(res, entity: str) -> str | None:
    """The other entity named in a join/lineage follow-up, if any.

    Ref tokens that are (substrings of) the entity itself are excluded so
    "fact_inventory ... với dim_warehouse" targets ``dim_warehouse``, not the
    subject "fact_inventory"; the last non-self ref wins (the target of the
    phrase).
    """
    en = _normalize_field(entity)
    candidates: list[str] = []
    for r in (getattr(res, "field_refs", None) or []):
        if r.lower() == entity.lower():
            continue
        rn = _normalize_field(r)
        if not rn or rn == en or rn in en or en in rn:
            continue
        candidates.append(r)
    return candidates[-1] if candidates else None


def _name_from_urn(r: str) -> str:
    """Extract the table name out of a DataHub dataset URN."""
    if not isinstance(r, str):
        return str(r)
    if "PROD" in r:
        inner = r.split("PROD")[0].rsplit("(", 1)[-1].strip().strip(",")
    else:
        inner = r
    return inner


def _is_contextual_followup(question: str) -> bool:
    """True when ``question`` refers back to a previously discussed entity.

    Recognises pronoun anaphora (nó/đó/this), demonstrative noun phrases
    ("bảng này", "dataset đó") and pure capability ellipsis ("có các trường
    nào?", "thuộc về ai?") — as long as the message carries no identifier of
    its own. Self-contained questions ("dim_warehouse có các trường nào?")
    are NOT follow-ups.
    """
    q = question or ""
    # Self-contained questions that name a concrete catalog identifier are
    # never follow-ups, even when they happen to contain a pronoun-like token
    # (e.g. "dây chuyền"/"đầy đủ" normalise to "day"). Check this FIRST so a
    # question like "Xóa dim_material thì ... ảnh hưởng gì?" keeps its own
    # explicit entity instead of being re-routed against the conversation.
    if _has_own_identifier(q):
        return False
    if _CONTEXTUAL_PRONOUN_RE.search(q) or _CONTEXTUAL_ASCII_RE.search(_norm_vn(q)):
        return True
    if _CONTEXTUAL_DEMONSTRATIVE.search(q):
        return True
    return bool(_CONTEXTUAL_ELLIPSIS.search(q))

_GREETING_RESPONSES = [
    "Xin chào! Tôi là trợ lý DataHub. Tôi có thể giúp bạn tra cứu datasets, "
    "glossary terms, owners, lineage và các thông tin metadata khác.",
    "Chào bạn! Tôi có thể hỗ trợ bạn tra cứu thông tin dữ liệu trong hệ thống. "
    "Bạn muốn tìm hiểu về điều gì?",
    "Xin chào! Hãy hỏi tôi về bất kỳ thông tin metadata nào như datasets, "
    "dashboards, glossary terms, hoặc lineage.",
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
    "bạn là ai": "Tôi là DataHub AI Chatbot, xây dựng để giúp bạn tra cứu "
                  "thông tin về dữ liệu doanh nghiệp.",
    "who are you": "I'm DataHub AI Chatbot, your metadata assistant.",
    "cảm ơn": "Không có gì! Nếu bạn cần thêm thông tin gì, cứ hỏi tôi nhé.",
    "cám ơn": "Không có gì! Nếu bạn cần thêm thông tin gì, cứ hỏi tôi nhé.",
    "thank": "You're welcome! Feel free to ask if you need anything else.",
}

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

def _count_identifiers(question: str) -> int:
    return len(_JOIN_TOKEN_RE.findall(question or ""))

def _detect_entity_type(question: str) -> str | None:
    for pattern, entity_type in _ENTITY_TYPE_PATTERNS:
        if pattern.search(question):
            return entity_type
    return None

def _detect_listing(question: str) -> str | None:
    cleaned = question.lower().strip().rstrip("?!.")
    # A trailing system scope ("... nào trong hệ thống") is very common on
    # listing questions ("có những document nào trong hệ thống?"); strip it
    # so the noun-phrase patterns above still match, without ever stripping
    # a catalog entity name.
    cleaned = re.sub(
        r'\s+(?:trong|in)\s+(?:hệ thống|he thong|system)\s*$', '', cleaned,
    ).strip()
    for pattern in _LISTING_PATTERNS:
        m = pattern.match(cleaned)
        if m:
            type_word = m.group(1).lower().strip()
            for key, entity_type in _LISTING_TYPE_MAP.items():
                if type_word.startswith(key) or key.startswith(type_word):
                    return entity_type
    return None

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
            base = f"  - {f.get('name', '')} ({f.get('type', '')})"
            field_lines.append(f"{base}: {desc}" if desc else base)
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

def _extract_entity_like(question: str) -> str | None:
    """Return the first entity-like token (contains '_' or '.') in ``question``."""
    import re
    for m in re.finditer(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", question):
        return m.group(0)
    for m in re.finditer(r"[a-z0-9]+_[a-z0-9_]+", question, re.I):
        return m.group(0)
    return None

def _extract_field_identifier(question: str) -> str | None:
    """Return a snake_case / dotted column identifier explicitly named by the user.

    Example: "warehouse_id" in "warehouse_id là gì?" Without this, the name
    is normalized to "warehouse id" and the glossary resolver can blur it
    into an unrelated match ("Bonded Warehouse"), so the field is never
    considered. A preserved identifier is the strongest signal that the user
    is asking about a *column* even when they omit the words "field/trường".

    The identifier right after a field signal ("trường X", "field X", "cột X")
    wins: in a compound "trong dataset Y có trường X" the dataset name is ALSO
    snake_case and appears first, so a naive first-match picks the dataset
    instead of the column ("dim_businessunit ... trường bu_short_name").
    """
    # Vietnamese question words that should NOT be treated as field names.
    # "gì" (what), "nào" (which), "chi" (dialect gì), "sao" (how), etc.
    _VN_QUESTION_WORDS = frozenset({
        "gi", "nao", "chi", "sao", "the", "vay", "dau", "bao", "may", "nhung",
        "cac", "khi", "tai", "tu", "voi", "trong", "ngoai", "tren", "duoi",
        "sau", "truoc", "giua", "hay", "hoac", "hoc", "roi", "da", "se",
        "dang", "con", "duoc", "bi", "phai", "can", "co", "khong", "la",
        "de", "vi", "nen", "nhu", "nay", "do", "o", "theo", "bang", "ve", "cho",
        "va", "and", "with",
    })
    # Explicit snake_case identifier right after field indicator
    m_snake = re.search(
        r"(?:trường|truong|cột|cot|field|column|col)\s+[\"“”'`]?([A-Za-z0-9]+(?:_[A-Za-z0-9]+)+)[\"“”'`]?",
        question, re.I,
    )
    if m_snake:
        return m_snake.group(1).strip()

    m = re.search(
        r"(?:trường|truong|cột|cot|field|column|col)\s+[\"“”'`]?"
        r"([\w\u00C0-\u024F]+(?:\s+[\w\u00C0-\u024F]+)*(?:\.[\w\u00C0-\u024F]+)*)",
        question, re.I | re.UNICODE,
    )
    if m:
        candidate_raw = m.group(1).strip()
        cand_tokens = candidate_raw.split()
        clean_tokens = []
        for tok in cand_tokens:
            if _norm_vn(tok) in _VN_QUESTION_WORDS and clean_tokens:
                break
            clean_tokens.append(tok)
        while clean_tokens and _norm_vn(clean_tokens[-1]) in _VN_QUESTION_WORDS:
            clean_tokens.pop()
        candidate = " ".join(clean_tokens).strip(" \"'“”`")
        if not candidate or _norm_vn(candidate) in _VN_QUESTION_WORDS:
            return None
        if len(candidate) < 3:
            return None
        return candidate
    m = re.search(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", question)
    if m:
        return m.group(0)
    for m in re.finditer(r"\b[A-Za-z0-9]+(_[A-Za-z0-9]+)+\b", question):
        return m.group(0)
    return None



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


def _is_field_location_question(question: str) -> bool:
    """True when the question asks WHERE a column lives ("dataset nào chứa
    trường X?", "trường X nằm trong dataset nào?", "warehouse_id nằm trong
    những dataset nào?", "X liên kết với bảng nào qua trường Y?").

    Such questions are a LISTING of every dataset carrying the field - several
    results are the answer, never an ambiguity clarification. Also excludes the
    formula-of-column phrasing ("công thức của X") which resolves the column as
    a glossary metric instead, and column-MEANING phrasing ("trường X nghĩa là
    gì?") which answers the field's meaning inside its dataset.
    """
    q = _norm_vn(question)
    if re.search(r"công thức|cong thuc|formula|cách tính|cach tinh", q):
        return False
    # Column-definition asks ("trường X nghĩa là gì?", "...có trường Y nghĩa
    # là gì?") ask the field's MEANING inside its dataset, not WHERE it lives.
    if re.search(r"nghĩa|nghia|meaning|ý nghĩa|y nghia|có nghĩa|co nghia", q, re.I):
        return False
    # Schema-listing asks ("có trường gì?", "có những trường nào?", "có bao
    # nhiêu trường?") ask WHAT fields the dataset has — NOT where a named
    # column lives.  These end with a question word after "trường/truong":
    # gì, nào, bao nhiêu, ...
    if re.search(
        r"(?:có\s+)?(?:trường|truong|cột|cot|field|column)\s+"
        r"(?:gì|gi|nào|nao|chi|bao\s+nhiêu|bao\s+nhieu|gì\b)",
        q, re.I,
    ):
        return False
    has_field_signal = bool(re.search(
        r"trường|truong|cột|cot|field|column|schema",
        q, re.I,
    ))
    has_bare_id = bool(re.search(r"[a-z0-9]{2,}(?:\.[a-z0-9_]+)+|[a-z0-9]{2,}_[a-z0-9_]+", q, re.I))
    if not (has_field_signal or has_bare_id):
        return False
    # Explicit "trường X nằm/ở/trong dataset nào" / "trường X thuộc bảng nào".
    if re.search(
        r"(?:trường|truong|cột|cot|field|column)\s+[\"“”'`]?[a-z0-9_\.\-]{2,}"
        r"\s+(?:thuộc|thuoc|nằm|nam|ở)\s+(?:trong)?\s*(?:những|nhung)?"
        r"\s*(?:dataset|bảng|bang|table|asset)",
        q, re.I,
    ):
        return True
    # Bare-identifier location: "warehouse_id nằm trong những dataset nào",
    # "promotion_id thuộc bảng nào".
    if re.search(
        r"[a-z0-9_]{2,}(?:\.[a-z0-9_]+)*\s+(?:nằm|nam|ở|thuộc|thuoc)"
        r"\s+(?:trong|ở\s+trong)?\s*(?:những|nhung)?\s*(?:dataset|bảng|bang|table)",
        q, re.I,
    ):
        return True
    # Join-sharing phrasing: "X liên kết với bảng nào qua trường Y", "nối với
    # dataset nào bằng field Z". The shared column names the listing datasets.
    if re.search(
        r"(?:liên kết|lien ket|join|nối|noi|kết nối|ket noi|được sync|duoc sync)"
        r"[^\n]{0,40}?(?:qua|theo|bằng|bang)\s*(?:trường|truong|field|cột|cot)?\s*"
        r"[a-z0-9_\.\-]{2,}",
        q, re.I,
    ):
        return True
    return bool(
        has_field_signal
        and re.search(
            r"(dataset|bảng|bang|table|asset)[^?]{0,50}?"
            r"(chứa|chua|contains?|has|có trường|co truong|chứa trường|chua truong)"
            r"|trường.*(thuộc|nằm|nam|trong dataset|trong bảng)"
            r"|(nằm|nam|ở|trong dataset nào|trong bảng nào)"
            r"|chứa trường|chua truong",
            q, re.I,
        )
    )

def _is_column_meaning_question(question: str) -> bool:
    """True for column-definition asks ("trường X nghĩa là gì?", "trường X
    có nghĩa là gì?", "ý nghĩa của trường X", "what does field X mean?").

    These ask the MEANING of a column - the answer is the field description /
    name-derived meaning inside its dataset, NOT a glossary-term formula. The
    formula-of-column guard must not hijack them.
    """
    q = _norm_vn(question)
    if re.search(r"công thức|cong thuc|formula|cách tính|cach tinh", q):
        return False
    has_field_signal = bool(re.search(
        r"trường|truong|cột|cot|field|column|col\b",
        q, re.I,
    ))
    meaning_signal = bool(re.search(
        r"nghĩa gì|nghia gi|nghĩa là gì|nghia la gi|có nghĩa|co nghia|"
        r"ý nghĩa|y nghia|meaning|nghĩa|nghia",
        q, re.I,
    ))
    return bool(has_field_signal and meaning_signal)


def _is_term_in_dataset_question(question: str) -> bool:
    """True for the "term/formula X trong dataset Y" compound pattern.

    "công thức Coverage Date trong Fact_Inventory_Coverage là gì?" names BOTH
    the term and the dataset; every resolved candidate (the dataset + the
    same-named terms) is the answer, never an ambiguity clarification.

    The dataset may be referenced with the word "dataset/bảng" or by its bare
    identifier ("trong Fact_Inventory_Coverage"); a bare "domain" reference
    ("trong domain SẢN XUẤT") is NOT a dataset anchor.
    """
    q = _norm_vn(question)
    return bool(re.search(
        r"(?:công thức|cong thuc|formula|cách tính|cach tinh|định nghĩa|"
        r"dinh nghia|nghĩa|nghia)"
        r"[^.!?]{0,60}?"
        r"trong\s+(?:(?:dataset|bảng|bang)\s+)?"
        r"(?!domain\b)[\"“”'`]?[a-z0-9_]+",
        q, re.I,
    ))


def _extract_identifiers(question: str) -> list[str]:
    out: list[str] = []
    for m in _JOIN_TOKEN_RE.finditer(question or ""):
        tok = m.group(0).strip()
        if tok and tok not in out:
            out.append(tok)
    return out

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
        "giai", "thich", "khai", "niem", "thuat", "ngu", "term",
        "cong", "thuc", "cach", "tinh", "can", "biet", "muon",
        "huong", "dan", "nhu", "the", "nao", "trong", "domain",
        "o", "nay", "do", "tu", "den",
    }
    clean_tokens = [t for t in tokens if t not in stop_words]
    # Drop leading noise tokens (verbs/prepositions) that often precede the
    # entity name but are not reduced by the global stop-word set above,
    # e.g. "trinh bay ve" / "mo ta ve" / "hay cho biet ve".
    _leading_noise = {
        "trinh", "bay", "mo", "ta", "neu", "cho", "giup", "hay", "ban",
        "tim", "hieu", "noi", "giui", "the", "nay", "do", "biet", "xin",
        "describe", "about", "explain", "what", "tell", "me", "please",
        "information", "info", "show", "display", "detail", "can",
        "muon", "giai", "thich", "khai", "niem", "thuat", "ngu",
        "cong", "thuc", "tinh", "huong", "dan", "bao", "cao",
        "report", "dashboard", "column", "cot", "truong",
    }
    while clean_tokens and clean_tokens[0] in _leading_noise:
        clean_tokens.pop(0)
    while clean_tokens and clean_tokens[-1] in _leading_noise:
        clean_tokens.pop()
    result = " ".join(clean_tokens) if clean_tokens else name
    result = result.strip().strip(" ?.!,:;-'\"").strip()
    return result


def _infer_entity_from_history(history: list[tuple[str, str]]) -> str | None:
    from retrieval.coreference import resolve_entity_reference

    return resolve_entity_reference(history)

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
        # bare capitalised "Term X" questions are glossary lookups ("Term
        # 3-Way Matching là gì?", "Term Aging Inventory có ý nghĩa gì?").
        # Word-bounded so "term" inside normal English ("long-term",
        # "patterns") does not over-match.
        "thuat ngu", "thuật ngữ", "y nghia", "ý nghĩa", "co nghia", "có nghĩa",
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
        # Impact / consequence vocabulary: deleting, changing or dropping an
        # asset and asking what happens is inherently a DataHub question even
        # when it carries no entity keyword of its own.
        "xoa", "xoá", "delete", "drop", "remove", "anh huong", "ảnh hưởng",
        "impact", "thay doi", "thay đổi", "what happens",
        # Anaphora used in follow-ups whose entity lives in conversation history
        "nó", "no ", "này", "nay ", "kéo",
        # Record / filter vocabulary for natural-language SQL queries
        "ban ghi", "bản ghi", "ban tin", "bản tin", "record",
    }
    if any(k in q or k in n for k in keywords):
        return True
    # Catalog / column identifiers speak DataHub even without vocabulary:
    # snake_case or dotted names ("dim_warehouse", "sales.orders",
    # "warehouse_id") are unambiguous metadata references.
    return bool(
        re.search(r"\b[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+(?:\.[A-Za-z0-9_]+)?\b", q)
        or re.search(r"\b[A-Za-z0-9_]+\.[A-Za-z0-9_]+\b", q)
        # Leading "Term X", "Glossary term X", "Thuật ngữ X" questions are
        # glossary lookups even when the term name alone carries no keyword.
        or re.search(r"\b(?:terms?|thuật ngữ|thuat ngu|khái niệm|khai niem)\b\s+\w+", n)
    )

def _is_glossary_followup(question: str) -> bool:
    low = question.lower()
    return any(k in low for k in (
        "glossary", "thuật ngữ", "thuat ngu", "giải thích", "giai thich",
        "định nghĩa", "dinh nghia",
    ))

def _is_noisy_entity(name: str) -> bool:
    """True when ``name`` is a long phrase, not a clean entity name."""
    if not name:
        return False
    if "_" in name or "." in name:
        return False
    return len(name.split()) > 2

def _looks_like_join(question: str) -> bool:
    if not question or not _JOIN_SIGNAL_RE.search(question):
        return False
    # "giữa/between" alone is too loose: require two real identifiers.
    matched = _JOIN_SIGNAL_RE.search(question).group(0).lower()
    if matched in ("giữa", "between"):
        return _count_identifiers(question) >= 2
    return _count_identifiers(question) >= 2 or (
        "liên kết" in question.lower() or "lien ket" in question.lower()
        or "join" in question.lower()
    )

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

def _short_negative_answer(intent: QueryIntent, results: Sequence[SearchResult], question: str = "") -> str | None:
    # If the user asks a composite question (e.g. schema + owner), do not short-circuit with a negative answer!
    if question and re.search(r"schema|cấu trúc|cau truc|cột|cot|trường|truong|field|lineage|formula|công thức|cong thuc|domain", question, re.I):
        return None

    if intent == QueryIntent.OWNER_LOOKUP and len(results) == 1:
        payload = results[0].payload or {}
        owners = payload.get("owners")
        if not owners:
            return f"Dataset {results[0].name} hiện không có người sở hữu (owner)."
    if intent == QueryIntent.LINEAGE and len(results) == 1:
        payload = results[0].payload or {}
        if payload.get("lineage_api_error"):
            return f"Không thể lấy lineage cho Dataset {results[0].name} do lỗi kết nối với hệ thống DataHub."
        if not payload.get("upstreams") and not payload.get("downstreams"):
            return (
                f"Dataset {results[0].name} hiện không có lineage "
                "(upstream/downstream) được ghi nhận."
            )
    if intent == QueryIntent.TERM_TO_DATASETS and len(results) == 1:
        payload = results[0].payload or {}
        if results[0].entity_type == "glossary_term":
            return (
                f"Term '{results[0].name}' hiện chưa được gắn cho dataset nào "
                "trong metadata DataHub."
            )
    # Guardrail #1/#2: an absence query with no metadata match is a grounded
    # negative answer ("does not exist in the catalog") rather than a guess.
    if intent == QueryIntent.ENTITY_EXISTS and len(results) == 0:
        return "Entity này không tồn tại trong metadata DataHub hiện có."
    return None

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


class QuestionAnalysisService:
    """Service providing unified question analysis, semantic normalization, and anaphora resolution."""

    @staticmethod
    def semantic_normalize(question: str) -> str:
        """Strip polite fillers, punctuation, and normalize whitespace."""
        q = re.sub(r"^(?:cho tôi hỏi|cho toi hoi|làm ơn cho tôi biết|lam on cho toi biet|vui lòng cho biết|vui long cho biet|hãy cho biết|hay cho biet)\s+", "", question, flags=re.I)
        q = re.sub(r"[?!.,;:\"']+", " ", q)
        return re.sub(r"\s+", " ", q).strip()

    @staticmethod
    def resolve_anaphora_with_context(question: str, history: list[tuple[str, str]]) -> str:
        """Replace pronouns (nó/đó/bảng này) with the active entity from conversation history."""
        if not _is_contextual_followup(question):
            return question

        entity = _infer_entity_from_history(history)
        if not entity:
            return question

        # Replace pronouns with entity
        q = re.sub(r"\b(?:nó|đó|ấy|này|kia|no|do|ay|nay|kia)\b", entity, question, flags=re.I)
        q = re.sub(r"\b(?:bảng này|bang nay|dataset này|dataset nay|bảng đó|bang do)\b", f"bảng {entity}", q, flags=re.I)
        return q

    @staticmethod
    def extract_target_entity(question: str) -> str | None:
        """Extract primary target entity name or snake/dotted identifier."""
        return _extract_field_identifier(question) or _extract_entity_like(question)

    @staticmethod
    def is_contextual_followup(question: str) -> bool:
        return _is_contextual_followup(question)

    @staticmethod
    def is_datahub_relevant(question: str) -> bool:
        return _is_datahub_relevant(question)

