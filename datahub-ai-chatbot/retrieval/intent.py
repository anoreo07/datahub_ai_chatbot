import re
from enum import StrEnum


class QueryIntent(StrEnum):
    TERM_DEFINITION = "TERM_DEFINITION"
    FIND_ENTITY = "FIND_ENTITY"
    OWNER_LOOKUP = "OWNER_LOOKUP"
    TERM_TO_DATASETS = "TERM_TO_DATASETS"
    LINEAGE = "LINEAGE"
    SCHEMA_LOOKUP = "SCHEMA_LOOKUP"
    DOMAIN_QUERY = "DOMAIN_QUERY"
    TAG_QUERY = "TAG_QUERY"
    PLATFORM_QUERY = "PLATFORM_QUERY"
    ENTITIES_BY_OWNER = "ENTITIES_BY_OWNER"
    CERTIFIED_LIST = "CERTIFIED_LIST"
    DOCUMENT_QA = "DOCUMENT_QA"
    GREETING = "GREETING"
    CHITCHAT = "CHITCHAT"
    GENERAL = "GENERAL"
    DATAHUB_URL = "DATAHUB_URL"
    ENTITY_EXISTS = "ENTITY_EXISTS"


_GREETINGS = {
    "xin chào", "xin chao", "chào", "chao", "hello", "hi", "hey",
    "chào bạn", "chao ban", "chào bot", "chao bot",
    "hello bot", "hi there",
}

_CHITCHAT = {
    "bạn khỏe không", "bạn khoẻ không", "ban khoe khong",
    "bạn có khỏe không", "bạn có khoẻ không", "ban co khoe khong",
    "how are you",
    "bạn tên gì", "ban ten gi",
    "bạn là ai", "ban la ai", "who are you",
    "bạn làm gì", "ban lam gi",
    "cảm ơn", "cám ơn", "cam on",
    "thank", "thanks",
    "ok", "okay", "good", "tốt", "tot", "tuyệt", "tuyet", "great",
}


def _norm_vn(s: str) -> str:
    import unicodedata
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return s


_RULE_STRINGS: list[tuple[str, QueryIntent]] = [
    (r"(nghĩa|là gì|la gi|định nghĩa|dinh nghia|definition|meaning|define)", QueryIntent.TERM_DEFINITION),
    (r"(ai sở hữu|owner|của ai|who (owns|is the owner))", QueryIntent.OWNER_LOOKUP),
    (r"(lấy dữ liệu từ đâu|lấy từ đâu|upstream|downstream|lineage|nguồn|source.*data|phụ thuộc)", QueryIntent.LINEAGE),
    (r"(field|column|cột|schema|trường|có những field)", QueryIntent.SCHEMA_LOOKUP),
    # Domain queries — "domain vgreen bao gồm những asset nào", "những asset thuộc domain X"
    (r"(domain|miền)\s+[\w\.\- ]{1,60}?\s+(bao gồm|gồm|có (những|các|asset|entity|dataset)|chứa|include|includes?|has|have|contain)", QueryIntent.DOMAIN_QUERY),
    (r"(assets?|entities?|datasets?|dashboards?)\s+(?:(that\s+are|are|which\s+are|which)\s+)?(trong|thuộc|in|belonging to|belong to)\s+(the\s+)?(domain|miền)\s+[\w\.\- ]{1,60}", QueryIntent.DOMAIN_QUERY),
    (r"(domain|miền)\s*[:=]\s*[\w\.\- ]{1,60}", QueryIntent.DOMAIN_QUERY),
    # Platform queries — "những dataset trên sap", "platform mysql có những asset gì"
    (r"(dataset|asset|entity|dashboard)s?\s+(trên|trong|in|on)\s+(platform|nền tảng)\s+[\w\.\- ]{1,60}", QueryIntent.PLATFORM_QUERY),
    (r"(platform|nền tảng)\s+[\w\.\- ]{1,60}?\s+(bao gồm|gồm|có (những|các|dataset|asset|entity)|chứa|include|has|contain)", QueryIntent.PLATFORM_QUERY),
    (r"(những|which|what|all)\s+(dataset|asset|entity|dashboard)s?\s+(trên|on|in)\s+[\w\.\- ]{1,60}", QueryIntent.PLATFORM_QUERY),
    (r"(dataset|asset|entity)s?\s+on\s+(sap|powerbi|snowflake|mysql|hive|kafka|s3|looker|mode|bigquery|redshift|postgres)", QueryIntent.PLATFORM_QUERY),
    # Tag queries — "dataset nào có tag PII", "assets tagged Gold"
    (r"(dataset|asset|entity|dashboard)s?\s+(nào|which)?\s*(có tag|được gắn tag|với tag|tagged|with tag)\s+[\w\.\- ]{1,60}", QueryIntent.TAG_QUERY),
    (r"tag\s+[\w\.\- ]{1,40}?\s+(bao gồm|gồm|có (những|các|dataset|asset|entity)|liên quan|chứa)", QueryIntent.TAG_QUERY),
    (r"(list|liệt kê|danh sách)\s+(datasets?|assets?|entities?)\s+(with|by|có)\s+tag\s+[\w\.\- ]{1,60}", QueryIntent.TAG_QUERY),
    (r"(assets?|entities?|datasets?)\s+tagged\s+[\w\.\- ]{1,60}", QueryIntent.TAG_QUERY),
    # Entities owned by someone — "dataset nào do Sales Analytics sở hữu", "what does X own"
    (r"(dataset|asset|entity|dashboard)s?\s+(nào|which|mà)\s+(do|bởi|owned by)\s+[\w\.\- ]{1,60}\s+(sở hữu|own)", QueryIntent.ENTITIES_BY_OWNER),
    (r"(dataset|asset|entity|dashboard)s?\s+(của|owned by)\s+[\w\.\- ]{1,60}", QueryIntent.ENTITIES_BY_OWNER),
    (r"(do|bởi|owned by)\s+[\w\.\- ]{1,60}\s+(sở hữu|own)", QueryIntent.ENTITIES_BY_OWNER),
    (r"what does\s+[\w\.\- ]{1,60}\s+own", QueryIntent.ENTITIES_BY_OWNER),
    (r"(những|which)\s+(dataset|asset|entity)s?\s+(của|do)\s+[\w\.\- ]{1,60}", QueryIntent.ENTITIES_BY_OWNER),
    # Certified entities — "những dataset certified", "list certified assets"
    (r"(dataset|asset|entity)s?\s+(đã\s+)?(được\s+)?(xác nhận|certified)", QueryIntent.CERTIFIED_LIST),
    (r"certified\s+(dataset|asset|entity)s?", QueryIntent.CERTIFIED_LIST),
    (r"danh sách\s+(đã\s+)?certified", QueryIntent.CERTIFIED_LIST),
    (r"(dataset nào|dataset.*gắn|entity.*associated|find dataset|entity nào)", QueryIntent.TERM_TO_DATASETS),
    (r"(theo tài liệu|document|report nói gì|theo document)", QueryIntent.DOCUMENT_QA),
    (r"(link|url|đường dẫn|datahub.*link)", QueryIntent.DATAHUB_URL),
    (r"(có tồn tại|tồn tại không|exist|có\s+không|co khong|có\s+\S+(?:\s+\S+)?\s+không)", QueryIntent.ENTITY_EXISTS),
]

_RULES: list[tuple[re.Pattern[str], QueryIntent]] = [
    (re.compile(p, re.I), intent) for p, intent in _RULE_STRINGS
]

_RULES_ASCII: list[tuple[re.Pattern[str], QueryIntent]] = [
    (re.compile(_norm_vn(p), re.I), intent) for p, intent in _RULE_STRINGS
]


def classify_intent(query: str) -> QueryIntent:
    cleaned = query.lower().strip().rstrip("?!.")
    if cleaned in _GREETINGS:
        return QueryIntent.GREETING
    if cleaned in _CHITCHAT or any(c in cleaned for c in _CHITCHAT if len(c) > 4):
        return QueryIntent.CHITCHAT

    for pattern, intent in _RULES:
        if pattern.search(query):
            return intent

    ascii_query = _norm_vn(query)
    for pattern, intent in _RULES_ASCII:
        if pattern.search(ascii_query):
            return intent

    return QueryIntent.GENERAL
