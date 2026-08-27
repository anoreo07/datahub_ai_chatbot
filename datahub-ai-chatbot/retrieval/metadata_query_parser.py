"""Metadata Query Parser.

Converts natural language metadata queries to GenericMetadataQuery:
  "dataset nào có lineage?"     → entity_type=dataset, filter=lineage EXISTS
  "dataset nào không có owner?" → entity_type=dataset, filter=owner MISSING
  "dataset nào thuộc domain X?" → entity_type=dataset, filter=domain EQUALS "X"

No hard-coded per-question branches. Uses AttributeRegistry + pattern matching.
"""

from __future__ import annotations

import re
import unicodedata

import structlog

from retrieval.metadata_query import (
    ATTRIBUTE_REGISTRY,
    FilterOperation,
    GenericMetadataQuery,
    MetadataFilter,
    normalize_attribute,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Vietnamese/English pattern building blocks
# ---------------------------------------------------------------------------

_VI_EXISTS = r"(?:có|dang có|được gán|có thông tin|có metadata|chứa|đang được)"
_VI_MISSING = r"(?:không có|chưa có|thiếu|bị thiếu|chưa được gán|chưa được|missing)"
_VI_EQUALS = r"(?:thuộc|thuoc|là|of|on|in|trên)"
_VI_LIMIT = r"(?:liệt kê|liet ke|cho tôi|show|list|display|hiển thị|xem)"
_VI_COUNT = r"(?:có bao nhiêu|co bao nhieu|bao nhiêu|bao nhieu|how many|số lượng|so luong|tổng số|tong so|count)"
_VI_ENTITY = r"(?:dataset|dashboard|glossary(?:\s+term)?|document|tài liệu|bảng|bang)"
_VI_CONJUNCTION = r"(?:và|va|and|nhưng|nhung|but|hoặc|or)"
_VI_ANAPHORA = r"(?:nào|nao|gì|gi|nào đó|nào không|nào đang|nào chưa)"

# Entity type mapping
_ENTITY_TYPE_MAP = {
    "dataset": "dataset",
    "datasets": "dataset",
    "bảng": "dataset",
    "bang": "dataset",
    "dashboard": "dashboard",
    "dashboards": "dashboard",
    "glossary": "glossary_term",
    "glossary term": "glossary_term",
    "glossary terms": "glossary_term",
    "thuật ngữ": "glossary_term",
    "document": "document",
    "documents": "document",
    "tài liệu": "document",
    "tai lieu": "document",
}

# Common dataset name patterns (snake_case, dotted)
_RE_SNAKE = re.compile(r"[A-Za-z0-9]{2,}_[A-Za-z0-9_]+")
_RE_DOTTED = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+")


def _norm(s: str) -> str:
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip()


def _extract_value_after_equals(message: str) -> str | None:
    """Extract the value after equals/belongs-to markers.

    'dataset thuộc domain SALES' → 'SALES'
    'dataset trên platform powerbi' → 'powerbi'
    """
    n = _norm(message)
    # Pattern: "thuộc/above <value>" at end or before conjunction/stop
    m = re.search(
        r"(?:thuoc|thuoc|la|of|on|in|tren)"
        r"\s+"
        r"([A-Za-z0-9][A-Za-z0-9 _\-.'&]{0,60})",
        n, re.I,
    )
    if m:
        val = m.group(1).strip()
        # Trim trailing stop words
        val = re.split(r"\s+(?:va|and|nhung|but|hoac|or|de|va co|va khong)", val)[0]
        val = val.strip().rstrip("?.!,;:")
        if val and len(val) >= 1:
            return val
    return None


def _extract_limit(message: str) -> int:
    """Extract numeric limit from message: 'liệt kê 10 dataset' → 10."""
    m = re.search(r"(\d+)", message)
    if m:
        return min(int(m.group(1)), 100)
    return 10


def _detect_entity_type(message: str) -> str:
    """Detect entity type from message. Defaults to 'dataset'."""
    n = _norm(message)
    for pattern, etype in _ENTITY_TYPE_MAP.items():
        if pattern in n:
            return etype
    return "dataset"


def _detect_operations(message: str) -> tuple[FilterOperation, str | None]:
    """Detect the filter operation and optional value from the message.

    Returns (operation, value_or_None).
    """
    n = _norm(message)

    # MISSING patterns (check before EXISTS since "không có" contains "có")
    if re.search(r"(?:khong co|chua co|thieu|bi thieu|chua duoc gan|missing)", n):
        return FilterOperation.MISSING, None

    # EXISTS patterns
    if re.search(r"(?:co |dang co|duoc gan|co thong tin|co metadata|chua|dang duoc)", n):
        return FilterOperation.EXISTS, None

    # EQUALS patterns (with value extraction)
    if re.search(r"(?:thuoc|thuoc|la |of |on |in |tren )", n):
        value = _extract_value_after_equals(message)
        return FilterOperation.EQUALS, value

    # Default: EXISTS (most common "có X?" pattern)
    return FilterOperation.EXISTS, None


def _extract_attribute_from_message(message: str) -> str | None:
    """Extract the metadata attribute mentioned in the message.

    Handles: 'lineage', 'linage' (typo), 'owner', 'domain', etc.
    Also handles Vietnamese phrases: 'chủ sở hữu', 'dòng dữ liệu', etc.
    """
    n = _norm(message)

    entity_type_words = {"dataset", "dashboard", "glossary", "document", "bảng", "bang"}

    # Try each registered attribute's synonyms
    best_match: str | None = None
    best_len = 0
    for spec in ATTRIBUTE_REGISTRY.values():
        for syn in spec.synonyms:
            syn_n = _norm(syn)
            if syn_n in n and len(syn_n) > best_len:
                # Skip if synonym overlaps with entity type name:
                # - "glossary" (entity type) should not match "glossary" attribute
                # - "glossary term" should not match when entity is glossary_term
                if syn_n in entity_type_words:
                    continue
                if any(et in syn_n for et in entity_type_words):
                    # "glossary term" contains "glossary" entity type → skip
                    continue
                best_match = spec.name
                best_len = len(syn_n)

    if best_match:
        return best_match

    # Try normalize_attribute on individual words
    for word in re.split(r"[\s,;:]+", n):
        if word in entity_type_words:
            continue
        result = normalize_attribute(word)
        if result:
            return result

    return None


def _detect_conjunction(message: str) -> list[str]:
    """Split message on conjunctions to detect multi-filter queries.

    'dataset có lineage và owner' → ['lineage', 'owner']
    """
    n = _norm(message)
    parts = re.split(r"\s+(?:va|and|nhung|but|hoac|or)\s+", n)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_metadata_query(message: str) -> GenericMetadataQuery | None:
    """Parse a natural language message into a GenericMetadataQuery.

    Returns None if the message doesn't look like a metadata listing query.
    """
    n = _norm(message)

    # --- Step 0: Skip how-to / guidance queries ---
    if re.search(
        r"^(?:làm thế nào|lam the nao|làm sao|lam sao|hướng dẫn|huong dan|cách nào|cach nao|như thế nào|nhu the nao|bằng cách nào|bang cach nao)\b",
        n,
        re.I,
    ):
        return None

    # --- Step 0b: Skip concept discovery / semantic search queries ---
    # "Có dataset nào liên quan đến khái niệm X không?", "Dataset nào phục vụ X?"
    # are CONCEPT_DISCOVERY, NOT metadata attribute listing.
    if re.search(
        r"(?:lien quan|relat(?:e|ed)?|khai niem|concept|phuc vu|chua thong tin|"
        r"duoc su dung trong|dung de phan tich|phan tich chi phi|phuc vu nhu cau)",
        n, re.I,
    ) and not re.search(r"(?:lien ket document|lien ket tai lieu|gan term|gan glossary|co glossary|co term)", n, re.I):
        return None

    # --- Step 1: Detect if this is a metadata listing query ---

    # Must contain entity type keyword
    has_entity_type = bool(re.search(
        r"(?:dataset|dashboard|glossary|document|bảng|bang|tai lieu|tài liệu)",
        n, re.I,
    ))
    # Must contain a METADATA-SPECIFIC signal: có/không có/thiếu/thuộc + attribute,
    # or count+attribute, or limit+number. Generic "nào" alone is NOT enough
    # (it could be TERM_TO_DATASETS: "dataset nào gắn term X?").
    has_metadata_signal = bool(re.search(
        r"(?:"
        r"co\s+\w+"           # "có <attribute>"
        r"|khong\s+co\s+\w+"  # "không có <attribute>"
        r"|thieu\s+\w+"       # "thiếu <attribute>"
        r"|thuoc\s+"          # "thuộc <value>"
        r"|tren\s+"           # "trên <value>"
        r"|co bao nhieu.*co\s+" # "bao nhiêu ... có <attr>"
        r"|liet ke\s+\d+"     # "liệt kê 10"
        r"|list\s+\d+"        # "list 10"
        r")",
        n, re.I,
    ))

    if not has_entity_type or not has_metadata_signal:
        return None

    # --- Step 1b: Skip entity-specific queries ---
    from retrieval.query_parser import _extract_entity
    ent = _extract_entity(message)
    if ent:
        return None

    # --- Step 1c: Skip domain count queries ---
    # "Lĩnh vực tài chính có bao nhiêu datasets?" → domain count (COUNT_ENTITIES)
    # "bao nhiêu" + specific attribute value before it = dimension count, not metadata check
    if re.search(r"bao nhieu", n):
        # Check if there's a specific value before "bao nhiêu" (e.g., "tài chính")
        before_count = re.split(r"\s+co\s+bao\s+nhieu", n)[0] if "co bao nhieu" in n else ""
        if before_count:
            # If the attribute is domain-like and there's a value, it's a dimension count
            has_dim_value = bool(re.search(
                r"(?:linh vuc|domain|nen tang|platform|moi truong|environment)\s+\S+",
                before_count, re.I,
            ))
            if has_dim_value:
                return None

    # --- Step 2: Detect entity type ---
    entity_type = _detect_entity_type(message)

    # --- Step 3: Detect operation ---
    operation, eq_value = _detect_operations(message)

    # --- Step 4: Detect attribute ---
    attribute = _extract_attribute_from_message(message)

    # --- Step 4b: Require at least one metadata signal ---
    # If no attribute AND no equals value detected, this is NOT a metadata query
    # (e.g., "có những dataset nào?" is a pure listing, not metadata filtering)
    if not attribute and not (operation == FilterOperation.EQUALS and eq_value):
        return None

    # --- Step 5: Detect limit ---
    limit = _extract_limit(message)

    # --- Step 6: Build filters ---
    filters: list[MetadataFilter] = []

    if attribute:
        filters.append(MetadataFilter(
            attribute=attribute,
            operation=operation,
            value=eq_value,
        ))
    elif operation == FilterOperation.EQUALS and eq_value:
        # "dataset thuộc domain SALES" — attribute might be domain but not explicitly named
        # Try to infer from context
        if re.search(r"(?:domain|linh vuc|mien)", n):
            filters.append(MetadataFilter(
                attribute="domain", operation=operation, value=eq_value,
            ))
        elif re.search(r"(?:platform|nen tang|he thong)", n):
            filters.append(MetadataFilter(
                attribute="platform", operation=operation, value=eq_value,
            ))
        elif re.search(r"(?:environment|env|moi truong)", n):
            filters.append(MetadataFilter(
                attribute="environment", operation=operation, value=eq_value,
            ))
        else:
            # Unknown attribute with value — skip filter, will return all of entity_type
            pass
    elif operation in (FilterOperation.EXISTS, FilterOperation.MISSING):
        # Missing attribute but has EXISTS/MISSING — can't build filter without attribute
        pass

    # Multi-filter: detect conjunctions
    if len(filters) == 1 and re.search(r"\s+(?:va|and|nhung|but)\s+", n):
        parts = re.split(r"\s+(?:va|and|nhung|but)\s+", n)
        if len(parts) >= 2:
            second_attr = _extract_attribute_from_message(parts[1])
            if second_attr and second_attr != attribute:
                # Detect operation for second part
                second_op, second_val = _detect_operations(parts[1])
                filters.append(MetadataFilter(
                    attribute=second_attr,
                    operation=second_op,
                    value=second_val,
                ))

    # --- Step 7: Detect count intent ---
    include_count = bool(re.search(
        r"(?:co bao nhieu|bao nhieu|how many|so luong|tong so|count|tổng số)",
        n, re.I,
    ))

    # --- Step 8: Build query ---
    query = GenericMetadataQuery(
        entity_type=entity_type,
        filters=filters,
        limit=limit if not include_count else 5,
        include_count=include_count or True,
        raw_question=message,
    )

    log.info(
        "metadata_query_parsed",
        entity_type=entity_type,
        filters=[f.to_dict() for f in filters],
        limit=limit,
        include_count=include_count,
        message=message[:100],
    )

    return query
