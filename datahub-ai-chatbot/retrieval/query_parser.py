"""Query Parser — converts natural language to QuerySpec.

Replaces the scattered pattern of:
  classify_intent() → flat string intent
  _extract_entity() → string or None
  parse_metadata_query() → GenericMetadataQuery (only for listing)

With a single unified parser that produces a QuerySpec with:
  scope, operation, property, operator, entity, filters.

Root causes addressed:
  RC1: Scope detection (ENTITY vs GLOBAL) is explicit
  RC2: Property extraction is decoupled from intent
  RC3: Operator extraction (EXISTS/MISSING/EQUALS) is structured
  RC5: Missing queries produce operator=MISSING, not separate intents
  RC6: Property comes from registry, not regex conflicts
  RC7: Multi-filter supported via filters list
"""

from __future__ import annotations

import re
import unicodedata

import structlog

from retrieval.metadata_query import ATTRIBUTE_REGISTRY, normalize_attribute
from retrieval.query_spec import (
    Operation,
    Operator,
    QueryFilter,
    QuerySpec,
    ResolutionStatus,
    Scope,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Vietnamese/English pattern building blocks
# ---------------------------------------------------------------------------

_ENTITY_TYPES = {
    "dataset": "dataset", "datasets": "dataset", "bảng": "dataset", "bang": "dataset",
    "dashboard": "dashboard", "dashboards": "dashboard",
    "glossary": "glossary_term", "glossary term": "glossary_term",
    "thuật ngữ": "glossary_term", "thuat ngu": "glossary_term",
    "document": "document", "documents": "document",
    "tài liệu": "document", "tai lieu": "document",
}

# Entity name patterns (snake_case, dotted, multi-word after markers)
_RE_SNAKE = re.compile(r"[A-Za-z0-9]{2,}_[A-Za-z0-9_]+")
_RE_DOTTED = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+")
_RE_MULTIWORD_MARKER = re.compile(
    r"(?:của|cho|cua|of|for|dataset|bang|bảng)\s+(?:dataset\s+)?"
    r"([A-Za-z0-9][A-Za-z0-9_\-.'&]{1,80})",
    re.I,
)

# Operation patterns
_RE_COUNT = re.compile(
    r"(?:có bao nhiêu|co bao nhieu|bao nhiêu|bao nhieu|how many|"
    r"số lượng|so luong|tổng số|tong so|tổng cộng|tong cong|count)",
    re.I,
)
_RE_DEFINE = re.compile(
    r"(?:là gì|la gi|định nghĩa|dinh nghia|giải thích|giai thich|"
    r"meaning|definition|define|thuật ngữ|thuat ngu|term)",
    re.I,
)
_RE_EXISTS_Q = re.compile(
    r"(?:có tồn tại|co ton tai|tồn tại|ton tai|exists?|được không|duoc khong)",
    re.I,
)
_RE_LIST = re.compile(
    r"(?:liệt kê|liet ke|danh sách|danh sach|show|list|display|xem|cho tôi)",
    re.I,
)

# Operator patterns
_RE_MISSING = re.compile(
    r"(?:không có|khong co|chưa có|chua co|thiếu|thieu|"
    r"bị thiếu|bi thieu|chưa được gán|chua duoc gan|missing|without|no )",
    re.I,
)
_RE_EXISTS = re.compile(
    r"(?:có |dang có|dang co|duoc gan|có thông tin|co thong tin|"
    r"có metadata|co metadata|đang được|dang duoc)",
    re.I,
)
_RE_EQUALS = re.compile(
    r"(?:thuộc|thuoc|là|of|on|in|trên|tren|belong)",
    re.I,
)

# Count-with-filter: "có bao nhiêu dataset có owner?"
_RE_COUNT_FILTER = re.compile(
    r"(?:bao nhieu|co bao nhieu|how many|count).+?(?:co |có )",
    re.I,
)

# Entity type keywords
_RE_ENTITY_TYPE = re.compile(
    r"(?:dataset|dashboard|glossary(?:\s+term)?|document|"
    r"bảng|bang|tài liệu|tai lieu)",
    re.I,
)


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip()


def _detect_entity_type(message: str) -> str:
    n = _norm(message)
    for pattern, etype in _ENTITY_TYPES.items():
        if pattern in n:
            return etype
    return "dataset"


_ACTION_PREFIX_RE = re.compile(
    r"^(?:(?:cho tôi xem|cho toi xem|cho xem|xem|vẽ|ve|hiển thị|hien thi|tạo|tao|kiểm tra|kiem tra|đánh giá|danh gia|phân tích|phan tich)\s+)?"
    r"(?:visualize\s+)?(?:data\s+)?(?:lineage|linage|impact(?:\s+analysis)?|quality(?:\s+check)?|metadata\s+report|report|generate\s+sql|sql|search(?:\s+dataset)?|tìm\s+kiếm|tim\s+kiem|tìm|tim|tra\s+cứu|tra\s+cuu)\s*"
    r"(?:(?:của|cho|cua|of|for)\s+)?"
    r"(?:(?:dataset|dashboard|glossary(?:\s+term)?|document|bảng|bang|tài liệu|tai lieu)\s+)?"
    r"([A-Za-z0-9][A-Za-z0-9 _\-.'&]{1,80})$",
    re.I,
)


def _extract_entity(message: str) -> str | None:
    """Extract entity name from the question.

    Returns None for global queries (no specific entity mentioned).
    """
    clean_msg = message.strip().rstrip("?.!,;:")
    message_norm = _norm(message)

    # Priority -1: How-To / Meta-questions without explicit identifiers
    if re.search(
        r"^(?:làm thế nào|lam the nao|làm sao|lam sao|hướng dẫn|huong dan|cách nào|cach nao|như thế nào|nhu the nao|bằng cách nào|bang cach nao)\b",
        message_norm,
        re.I,
    ) and not (_RE_DOTTED.search(clean_msg) or _RE_SNAKE.search(clean_msg) or re.search(r"[\"“”'`][A-Za-z0-9_]+[\"“”'`]", clean_msg)):
        return None

    # Priority 0: Action prefix stripping (e.g. "Lineage của dataset PVB QDAT", "Impact PVB QDAT")
    m_act = _ACTION_PREFIX_RE.match(clean_msg)
    if m_act:
        c = m_act.group(1).strip()
        if len(c) >= 2 and not re.match(
            r"^(?:cho|cua|của|of|for|the|a|an|này|đó|nay|do|không|khong|tồn|ton|tại|tai)$", c, re.I
        ):
            return c

    # Priority 1: Dotted path
    m = _RE_DOTTED.search(message_norm)
    if m:
        return m.group(0)

    # Priority 2: Snake_case identifier
    m = _RE_SNAKE.search(message_norm)
    if m:
        return m.group(0)

    _META_VERBS_STOP = (
        r"(?:\s+(?:co|khong co|chua co|thieu|bi thieu|thuoc|tren|lay du lieu|"
        r"luu|dung de|la gi|duoc|nhu the nao|thi|gap su co|co bao nhieu|bao nhieu|"
        r"nhung|co nhung|chua|co the|duoc khong|ton tai|nao|gi|khong)\b|[?.!,;:]|$)"
    )

    _LOOKAHEAD_IGNORE = (
        r"co|khong|chua|thieu|thuoc|tren|nao|gi|lay|luu|dung|la|duoc|bao nhieu|tat ca|nhung|cac|moi|gii|lieu|"
        r"mot|1|mot so|bat ky|bat cu|va|va kiem|kiem|kiem tra|he thong|datahub|chung|tong the"
    )

    # Priority 3: Direct entity type keyword with optional platform
    m_direct = re.search(
        rf"(?:dataset|dashboard|glossary(?:\s+term)?|document|tai lieu|bang|bảng|thuat ngu|thuật ngữ|chi so|chỉ số|bao cao|báo cáo|column|cột|cot|field|trường|truong)\s+"
        rf"(?!(?:{_LOOKAHEAD_IGNORE})\b)"
        rf"(?:(?:glue|redshift|powerbi|sap|mes)\s+)?"
        rf"([A-Za-z0-9][A-Za-z0-9_\-. \(\)'&/]{{0,70}}?)"
        rf"{_META_VERBS_STOP}",
        message_norm, re.I,
    )
    if m_direct:
        c = m_direct.group(1).strip()
        # Strip all trailing noise words iteratively
        c = re.sub(r"(?:\s+(?:nay|do|la|la gi|nhu the nao|tinh nhu the nao))+$", "", c, flags=re.I).strip()
        if len(c) >= 2 and not re.match(r"^(?:mot\s+|1\s+|cac\s+|nhung\s+|va\s+|kiem\s+|datahub|he thong)", c, re.I):
            return c

    # Priority 4: In / About / Of / Specific markers
    m_marker = re.search(
        rf"(?:cua|ve|trong|of|about|for|cho\s+(?:dataset|bang|dashboard))\s+"
        rf"(?!(?:{_LOOKAHEAD_IGNORE})\b)"
        rf"([A-Za-z0-9][A-Za-z0-9_\-. \(\)'&/]{{0,70}}?)"
        rf"{_META_VERBS_STOP}",
        message_norm, re.I,
    )
    if m_marker:
        c = m_marker.group(1).strip()
        # Strip leading column/field prefixes if present
        c = re.sub(r"^(?:column|cot|field|truong)\s+", "", c, flags=re.I).strip()
        # Strip all trailing noise words iteratively
        c = re.sub(r"(?:\s+(?:nay|do|la|la gi|nhu the nao|tinh nhu the nao))+$", "", c, flags=re.I).strip()
        if len(c) >= 2 and len(c.split()) <= 4 and not re.match(r"^(?:mot\s+|1\s+|cac\s+|nhung\s+|va\s+|kiem\s+|datahub|he thong)", c, re.I):
            return c

    return None




def _has_entity_signal(message: str) -> bool:
    """Check if the message mentions a specific entity name."""
    return _extract_entity(message) is not None


def _extract_all_entities(message: str) -> list[str]:
    """Extract ALL entity mentions from the question (not just the first).

    Handles multi-entity questions like:
      "so sánh dataset A và B về schema"
      "A, B, và C có lineage không?"
      "dataset A với dashboard B"

    Returns a deduplicated list preserving mention order.
    """
    message_norm = _norm(message)
    entities: list[str] = []

    # Find all dotted paths
    for m in _RE_DOTTED.finditer(message_norm):
        name = m.group(0)
        if name not in entities:
            entities.append(name)

    # Find all snake_case identifiers (only if they look like entity names,
    # not common Vietnamese/English words)
    _STOP_TOKENS = {
        "co", "khong", "chua", "thieu", "thuoc", "tren", "lay", "luu",
        "dung", "la", "duoc", "bao", "nhieu", "tat", "ca", "nhung", "cac",
        "moi", "gii", "lieu", "va", "hay", "hoac", "neu", "thi", "se",
        "bi", "dang", "da", "sẽ", "đã", "đang", "cung", " nhu", "theo",
        "ve", "trong", "cho", "doi", "voi", "tu", "den", "tai", "khi",
        "nao", "gi", "gì", "nào", "so", "san", "sanh", "compare",
        "field", "column", "schema", "table", "dataset", "dashboard",
        "lineage", "quality", "owner", "domain", "term", "glossary",
        "phu hop", "tot hon", "xay dung", "ton kho",
    }
    for m in _RE_SNAKE.finditer(message_norm):
        name = m.group(0)
        # Skip if it's a substring of an already-found dotted name
        if any(name in e for e in entities):
            continue
        if name not in entities and name.lower() not in _STOP_TOKENS:
            entities.append(name)

    # Find entity names after type markers: "dataset X", "dashboard Y", etc.
    # Use a broader capture to get multi-word names separated by "và"/"and"
    for m in re.finditer(
        r"(?:dataset|dashboard|glossary(?:\s+term)?|document|bảng|bang|"
        r"tài liệu|tai lieu|report|báo cáo|bao cao|thuật ngữ|thuat ngu)"
        r"\s+"
        r"(?:[A-Za-z0-9][A-Za-z0-9_\-. \(\)'&/]{1,80})",
        message_norm, re.I,
    ):
        raw = m.group(0)
        # Strip the type prefix to get just the name
        name = re.sub(
            r"^(?:dataset|dashboard|glossary(?:\s+term)?|document|bảng|bang|"
            r"tài liệu|tai lieu|report|báo cáo|bao cao|thuật ngữ|thuat ngu)\s+",
            "", raw, flags=re.I,
        ).strip()
        # Truncate at metadata verbs and common Vietnamese connectors
        name_parts = re.split(
            r"\s+(?:co|khong co|chua co|thieu|thuoc|tren|lay du lieu|"
            r"luu|dung de|la gi|duoc|nhu the nao|thi|gap su co|co bao nhieu|"
            r"nhung|co nhung|chua|co the|duoc khong|ton tai|nao|gi|khong|"
            r"ve|trong|va|hay|hoac|neu|so sanh|compare|quality|schema|lineage|"
            r"phu hop|tot hon|khac|difference|versus|vs|"
            r"xay dung|dashboard|ton kho|cross.?domain|"
            r"chat luong|du lieu|metadata)\b",
            name, flags=re.I,
        )
        name = name_parts[0].strip() if name_parts else name.strip()
        # Reject pure Vietnamese noise words that slipped through
        _NOISE_WORDS = {"nao", "gi", "gì", "nào", "do", "day", "nay", "kia", "ay"}
        if name.lower() in _NOISE_WORDS:
            continue
        if name and len(name) >= 2 and name not in entities:
            entities.append(name)

    return entities


def _detect_operation(message: str) -> Operation:
    n = _norm(message)

    if _RE_COUNT.search(n):
        return Operation.COUNT
    if _RE_DEFINE.search(n):
        return Operation.DEFINE
    if _RE_EXISTS_Q.search(n):
        return Operation.EXISTS
    if _RE_LIST.search(n):
        return Operation.LIST

    return Operation.GET


def _detect_operator(message: str) -> Operator:
    n = _norm(message)

    # MISSING must be checked before EXISTS (since "không có" contains "có")
    if _RE_MISSING.search(n):
        return Operator.MISSING
    if _RE_EXISTS.search(n):
        return Operator.EXISTS
    if _RE_EQUALS.search(n):
        return Operator.EQUALS

    return Operator.GET


def _detect_property(message: str) -> str | None:
    """Extract the metadata property being queried.

    Uses the AttributeRegistry for synonym matching.
    """
    n = _norm(message)

    # Entity type words should NOT be treated as properties
    entity_type_words = {"dataset", "dashboard", "glossary", "document", "bảng", "bang"}

    best_match: str | None = None
    best_len = 0

    for spec in ATTRIBUTE_REGISTRY.values():
        for syn in spec.synonyms:
            syn_n = _norm(syn)
            if syn_n in n and len(syn_n) > best_len:
                # Skip entity type overlaps
                if syn_n in entity_type_words:
                    continue
                if any(et in syn_n for et in entity_type_words):
                    continue
                best_match = spec.name
                best_len = len(syn_n)

    if best_match:
        return best_match

    # Individual word matching
    for word in re.split(r"[\s,;:]+", n):
        if word in entity_type_words or len(word) < 2:
            continue
        result = normalize_attribute(word)
        if result:
            return result

    return None


def _detect_equals_value(message: str) -> str | None:
    """Extract the value after equals/belongs-to markers.

    'dataset thuộc domain SALES' → 'SALES'
    'dataset trên platform powerbi' → 'powerbi'
    """
    n = _norm(message)
    m = re.search(
        r"(?:thuoc|thuoc|la|of|on|in|tren)"
        r"\s+"
        r"([A-Za-z0-9][A-Za-z0-9 _\-.'&]{0,60})",
        n, re.I,
    )
    if m:
        val = m.group(1).strip()
        val = re.split(r"\s+(?:va|and|nhung|but|hoac|or|de|va co|va khong)", val)[0]
        val = val.strip().rstrip("?.!,;:")
        if val and len(val) >= 1:
            return val
    return None


def _detect_limit(message: str) -> int:
    m = re.search(r"(\d+)", message)
    if m:
        return min(int(m.group(1)), 100)
    return 10


def _is_global_query(message: str, entity_name: str | None) -> bool:
    """Determine if this is a global/collection query vs entity-specific.

    Global: "dataset nào có lineage?" (no entity name, uses "nào")
    Entity: "dim_warehouse có lineage không?" (has entity name)
    """
    n = _norm(message)

    # If an entity name was extracted, it's entity-scoped
    if entity_name:
        return False

    # "nào" / "nao" signals a collection query
    if re.search(r"\b(?:nao|nào|gi|gì)\b", n):
        return True

    # "có những" / "danh sách" signals listing
    if re.search(r"(?:co nhung|có những|danh sach|danh sách|liet ke|liệt kê)", n):
        return True

    # "bao nhiêu" with entity type keyword = global count
    if _RE_COUNT.search(n) and _RE_ENTITY_TYPE.search(n):
        return True

    return False


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_query(message: str, selected_action: str | None = None) -> QuerySpec:
    """Parse a natural language question into a QuerySpec.

    This is the unified entry point that replaces:
      classify_intent() + _extract_entity() + parse_metadata_query()
    """
    entity_type = _detect_entity_type(message)
    entity_name = _extract_entity(message)
    operation = _detect_operation(message)
    operator = _detect_operator(message)
    prop = _detect_property(message)
    eq_value = _detect_equals_value(message)
    limit = _detect_limit(message)

    if selected_action:
        if selected_action == "lineage":
            prop = prop or "lineage"
            operator = Operator.EQUALS
            operation = Operation.GET
        elif selected_action == "impact":
            prop = prop or "impact"
            operator = Operator.EQUALS
            operation = Operation.GET
        elif selected_action == "quality":
            prop = prop or "quality"
            operator = Operator.EQUALS
            operation = Operation.GET
        elif selected_action in ("sql", "report"):
            operation = Operation.GET
            prop = prop or "schema"
        elif selected_action == "search":
            operation = Operation.GET

    # Determine scope
    if _is_global_query(message, entity_name) and not selected_action:
        scope = Scope.GLOBAL
    elif entity_name:
        scope = Scope.ENTITY
    else:
        scope = Scope.GLOBAL

    # Build filters
    filters: list[QueryFilter] = []
    if prop:
        filters.append(QueryFilter(attr=prop, operator=operator, value=eq_value))

    # Multi-filter: detect "và"/"and" conjunctions
    if re.search(r"\s+(?:va|and)\s+", _norm(message)):
        parts = re.split(r"\s+(?:va|and)\s+", _norm(message))
        if len(parts) >= 2:
            for part in parts[1:]:
                second_prop = _detect_property(part)
                if second_prop and second_prop != prop:
                    second_op = _detect_operator(part)
                    second_val = _detect_equals_value(part)
                    filters.append(QueryFilter(
                        attr=second_prop, operator=second_op, value=second_val,
                    ))

    # Determine resolution status
    resolution_status = ResolutionStatus.READY
    if scope == Scope.ENTITY and not entity_name:
        resolution_status = ResolutionStatus.NEEDS_ENTITY
    elif not prop and operation in (Operation.GET, Operation.LIST) and not selected_action:
        resolution_status = ResolutionStatus.NEEDS_PROPERTY

    # Build QuerySpec
    spec = QuerySpec(
        operation=operation,
        scope=scope,
        entity_type=entity_type,
        entity_name=entity_name,
        attr=prop,
        operator=operator,
        value=eq_value,
        filters=filters,
        aggregation="count" if operation == Operation.COUNT else None,
        limit=limit,
        resolution_status=resolution_status,
        raw_question=message,
    )

    log.info(
        "query_spec_parsed",
        operation=spec.operation.value,
        scope=spec.scope.value,
        entity_type=spec.entity_type,
        entity_name=spec.entity_name,
        property=spec.attr,
        operator=spec.operator.value,
        filters=[(f.attr, f.operator.value) for f in spec.filters],
        resolution_status=spec.resolution_status.value,
        message=message[:100],
    )

    return spec


# ---------------------------------------------------------------------------
# H7: Follow-up classification and query merging
# ---------------------------------------------------------------------------

# Patterns that signal the user is selecting from a clarification menu
# NOTE: patterns use ASCII (normalized) forms since _norm() strips diacritics.
_RE_SELECTION = re.compile(
    r"^\s*(?:A|B|C|D|1|2|3|4|a|b|c|d)\s*$"
    r"|^(?:cai?\s+)?(?:dau tien|thu hai|thu ba|thu tu|dung roi|ok|u|duoc|chinh xac)"
    r"|^(?:option|choice|chon)\s*\d",
    re.I,
)

# Patterns that signal refinement — same entity, narrower scope
_RE_REFINEMENT = re.compile(
    r"(?:chi|only|just)\s+"
    r"|(?:dung|roi|ok|vay|thi|nhe)\s*$"
    r"|^(?:vay\s+)?(?:chi|only|just)\s+",
    re.I,
)

# Patterns that signal a follow-up — anaphora or implicit entity
_RE_FOLLOWUP_ANAPHORA = re.compile(
    r"\b(?:no|do|nay|day|kia|"
    r"minh|toi|chung ta|ta)\b",
    re.I,
)

# "cua no" / "thuoc no" / "thong tin" — implicit entity from previous turn
# Uses word boundaries to avoid false matches (e.g. "domain" matching "do")
_RE_FOLLOWUP_IMPLICIT = re.compile(
    r"(?:cua|thuoc|thong tin|info|detail|chi tiet)\s+"
    r"(?:\bno\b|\bdo\b|\bnay\b|\bcai?\s*(?:\bdo\b|\bnay\b))",
    re.I,
)


def classify_followup_type(
    message: str,
    prev_query_spec: dict | None,
    prev_entity_name: str | None = None,
) -> str:
    """Classify how a new question relates to the previous turn's QuerySpec.

    Returns one of:
      NEW_QUERY                — completely independent question
      FOLLOW_UP                — same entity, new property ("domain của nó?")
      REFINEMENT               — same entity + property, narrower ("Chỉ SAP thôi")
      CLARIFICATION_RESPONSE   — answer to clarification ("B", "đúng rồi")
      AMBIGUOUS                — cannot determine — treat as NEW_QUERY

    This replaces the regex-based _is_contextual_followup() in question_analysis.py.
    """
    n = _norm(message)

    # If no previous QuerySpec, it's a new query (no prior context)
    if not prev_query_spec:
        # Check for anaphora — could be a follow-up with no context (treat as NEW_QUERY)
        if _RE_FOLLOWUP_ANAPHORA.search(n):
            return "AMBIGUOUS"  # user says "nó" but we have no context
        return "NEW_QUERY"

    # --- Check for clarification response first (A/B/C/D or "đúng rồi") ---
    if _RE_SELECTION.search(n):
        return "CLARIFICATION_RESPONSE"

    # --- Check for refinement signals ---
    if _RE_REFINEMENT.search(n):
        # "Chỉ SAP thôi" with prev entity + property → REFINEMENT
        if prev_query_spec.get("entity_name") and prev_query_spec.get("property"):
            return "REFINEMENT"
        # If only entity was set, treat as FOLLOW_UP with filter
        if prev_query_spec.get("entity_name"):
            return "REFINEMENT"

    # --- Check for follow-up with anaphora ---
    has_anaphora = bool(_RE_FOLLOWUP_ANAPHORA.search(n))
    has_implicit = bool(_RE_FOLLOWUP_IMPLICIT.search(n))

    if has_anaphora or has_implicit:
        # User is referring to the previous entity
        if prev_query_spec.get("entity_name"):
            return "FOLLOW_UP"
        return "AMBIGUOUS"  # anaphora but no entity in previous spec

    # --- No explicit signal — check if it's a new question or continuation ---
    # If new query has an entity name that matches the previous one → FOLLOW_UP
    new_spec = parse_query(message)
    if (new_spec.entity_name and prev_query_spec.get("entity_name")
            and _norm(new_spec.entity_name) == _norm(prev_query_spec["entity_name"])):
        # Same entity — check if property changed
        if new_spec.attr and new_spec.attr != prev_query_spec.get("property"):
            return "FOLLOW_UP"
        # Same entity + same property (or no new property) → REFINEMENT
        if new_spec.value:
            return "REFINEMENT"
        return "FOLLOW_UP"

    # If new query has NO entity name but prev had one → possible FOLLOW_UP
    if not new_spec.entity_name and prev_query_spec.get("entity_name"):
        # Check if the new question is asking about a property of the prev entity
        if new_spec.attr:
            return "FOLLOW_UP"

    # Completely different entity or global query → NEW_QUERY
    return "NEW_QUERY"


def merge_query_specs(prev: dict | None, new: QuerySpec) -> QuerySpec:
    """Merge a new QuerySpec with the previous turn's context.

    Rules:
      FOLLOW_UP: inherit entity from prev, add new property/filter from new
      REFINEMENT: inherit entity + property from prev, add value/filter from new
      NEW_QUERY: use new as-is
      CLARIFICATION_RESPONSE: use prev (the pending spec from clarification)
      AMBIGUOUS: use new as-is
    """
    if prev is None:
        return new

    followup_type = classify_followup_type(
        new.raw_question,
        prev,
        prev.get("entity_name"),
    )

    if followup_type == "NEW_QUERY" or followup_type == "AMBIGUOUS":
        return new

    # Reconstruct a QuerySpec from the previous turn's dict
    prev_spec = QuerySpec(
        operation=Operation(prev.get("operation", "GET")),
        scope=Scope(prev.get("scope", "GLOBAL")),
        entity_type=prev.get("entity_type", "dataset"),
        entity_name=prev.get("entity_name"),
        entity_urn=prev.get("entity_urn"),
        attr=prev.get("property"),
        operator=Operator(prev.get("operator", "GET")),
        value=prev.get("value"),
        filters=[
            QueryFilter(
                attr=f.get("property", f.get("attr", "")),
                operator=Operator(f.get("operator", "GET")),
                value=f.get("value"),
                negated=f.get("negated", False),
            )
            for f in prev.get("filters", [])
        ],
        aggregation=prev.get("aggregation"),
        limit=prev.get("limit", 10),
    )

    if followup_type == "CLARIFICATION_RESPONSE":
        # Return the pending spec as-is — the user's selection resolves it
        return prev_spec

    if followup_type == "FOLLOW_UP":
        # Inherit entity from prev, use new property/operator/value
        merged = QuerySpec(
            operation=new.operation,
            scope=Scope.ENTITY if prev_spec.entity_name else new.scope,
            entity_type=prev_spec.entity_type,
            entity_name=prev_spec.entity_name or new.entity_name,
            entity_urn=prev_spec.entity_urn or new.entity_urn,
            attr=new.attr or prev_spec.attr,
            operator=new.operator,
            value=new.value,
            filters=new.filters or prev_spec.filters,
            aggregation=new.aggregation or prev_spec.aggregation,
            limit=new.limit,
            resolution_status=new.resolution_status,
            raw_question=new.raw_question,
            context_dependency={"carried_from_previous_turn": True, "carried_fields": []},
        )
        # Track which fields were carried over
        carried = []
        if not new.entity_name and prev_spec.entity_name:
            carried.append("entity_name")
        if not new.attr and prev_spec.attr:
            carried.append("property")
        merged.context_dependency["carried_fields"] = carried
        return merged

    if followup_type == "REFINEMENT":
        # Inherit entity + property from prev, add new value/filter from new
        merged = QuerySpec(
            operation=new.operation if new.operation != Operation.GET else prev_spec.operation,
            scope=Scope.ENTITY if prev_spec.entity_name else new.scope,
            entity_type=prev_spec.entity_type,
            entity_name=prev_spec.entity_name or new.entity_name,
            entity_urn=prev_spec.entity_urn or new.entity_urn,
            attr=new.attr or prev_spec.attr,
            operator=new.operator if new.operator != Operator.GET else prev_spec.operator,
            value=new.value or prev_spec.value,
            filters=new.filters if new.filters else prev_spec.filters,
            aggregation=new.aggregation or prev_spec.aggregation,
            limit=new.limit,
            resolution_status=new.resolution_status,
            raw_question=new.raw_question,
            context_dependency={"carried_from_previous_turn": True, "carried_fields": []},
        )
        carried = []
        if not new.entity_name and prev_spec.entity_name:
            carried.append("entity_name")
        if not new.attr and prev_spec.attr:
            carried.append("property")
        if not new.value and prev_spec.value:
            carried.append("value")
        merged.context_dependency["carried_fields"] = carried
        return merged

    return new
