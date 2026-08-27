"""Generic Metadata Listing Engine.

Provides a structured query contract for metadata queries like:
  "dataset nào có lineage?"
  "dataset nào không có owner?"
  "dataset nào thuộc domain X?"

Architecture:
  MetadataQueryParser (NLP → GenericMetadataQuery)
  MetadataFilterEngine (GenericMetadataQuery → DB results)
  AttributeRegistry (metadata attribute definitions)

Design: Adding a new attribute = add one entry to ATTRIBUTE_REGISTRY.
No if/else branches in ChatService.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data contract
# ---------------------------------------------------------------------------

class FilterOperation(StrEnum):
    EXISTS = "EXISTS"
    MISSING = "MISSING"
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    CONTAINS = "CONTAINS"


@dataclass
class MetadataFilter:
    attribute: str
    operation: FilterOperation
    value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"attribute": self.attribute, "operation": self.operation.value}
        if self.value is not None:
            d["value"] = self.value
        return d


@dataclass
class GenericMetadataQuery:
    entity_type: str
    filters: list[MetadataFilter] = field(default_factory=list)
    limit: int = 10
    offset: int = 0
    include_count: bool = True
    sort_by: str | None = None
    raw_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "filters": [f.to_dict() for f in self.filters],
            "limit": self.limit,
            "offset": self.offset,
            "include_count": self.include_count,
            "sort_by": self.sort_by,
        }


# ---------------------------------------------------------------------------
# Attribute Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AttributeSpec:
    name: str
    display_name: str
    entity_types: frozenset[str]
    sql_column: str | None = None
    json_path: str | None = None
    exists_check: str = "not_null"
    synonyms: tuple[str, ...] = ()
    description: str = ""


# Canonical attribute definitions.
# To add a new attribute: add one entry here. No other code changes needed.
ATTRIBUTE_REGISTRY: dict[str, AttributeSpec] = {
    "owner": AttributeSpec(
        name="owner",
        display_name="Owner",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term", "document"}),
        json_path="owners",
        exists_check="array_not_empty",
        synonyms=("owner", "chủ sở hữu", "người phụ trách", "người sở hữu",
                  "chủ", "sở hữu", "owns", "owned by"),
        description="Owner metadata (at least one valid owner)",
    ),
    "lineage": AttributeSpec(
        name="lineage",
        display_name="Lineage",
        entity_types=frozenset({"dataset", "dashboard"}),
        json_path="upstreams",
        exists_check="lineage_edges",
        synonyms=("lineage", "linage", "linege", "dòng dữ liệu", "luồng dữ liệu",
                  "nguồn dữ liệu", "data flow", "flow", "upstream", "downstream",
                  "nối", "kết nối"),
        description="Lineage edges (upstream or downstream)",
    ),
    "domain": AttributeSpec(
        name="domain",
        display_name="Domain",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term", "document"}),
        sql_column="domain",
        json_path="domain",
        exists_check="not_empty_string",
        synonyms=("domain", "lĩnh vực", "miền", "miền dữ liệu", "domain nghiệp vụ",
                  "business domain"),
        description="Domain assignment",
    ),
    "description": AttributeSpec(
        name="description",
        display_name="Description",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term", "document"}),
        sql_column="description",
        json_path="description",
        exists_check="not_empty_string",
        synonyms=("description", "mô tả", "business description", "giải thích",
                  "định nghĩa", "nội dung mô tả"),
        description="Description metadata",
    ),
    "tags": AttributeSpec(
        name="tags",
        display_name="Tags",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term", "document"}),
        json_path="tags",
        exists_check="array_not_empty",
        synonyms=("tag", "tags", "nhãn", "nhãn hiệu", "labels"),
        description="Tag associations",
    ),
    "glossary": AttributeSpec(
        name="glossary",
        display_name="Glossary",
        entity_types=frozenset({"dataset", "dashboard", "document"}),
        json_path="glossary_terms",
        exists_check="array_not_empty",
        synonyms=("glossary", "thuật ngữ", "business term", "business glossary",
                  "glossary term"),
        description="Glossary term associations",
    ),
    "schema": AttributeSpec(
        name="schema",
        display_name="Schema",
        entity_types=frozenset({"dataset"}),
        json_path="schema_fields",
        exists_check="array_not_empty",
        synonyms=("schema", "cấu trúc", "cột", "field", "column", "columns",
                  "schema fields", "cấu trúc bảng"),
        description="Schema fields",
    ),
    "platform": AttributeSpec(
        name="platform",
        display_name="Platform",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term", "document"}),
        sql_column="platform",
        json_path="platform",
        exists_check="not_empty_string",
        synonyms=("platform", "nền tảng", "source system"),
        description="Platform/source system",
    ),
    "environment": AttributeSpec(
        name="environment",
        display_name="Environment",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term", "document"}),
        sql_column="environment",
        json_path="environment",
        exists_check="not_empty_string",
        synonyms=("environment", "env", "môi trường", "khai thác", "production",
                  "PROD", "STG", "DEV"),
        description="Environment (PROD, STG, DEV, etc.)",
    ),
    "documentation": AttributeSpec(
        name="documentation",
        display_name="Documentation",
        entity_types=frozenset({"dataset", "dashboard", "document"}),
        json_path="linked_documents",
        exists_check="array_not_empty",
        synonyms=("documentation", "tài liệu", "document", "docs", "linked document"),
        description="Linked documentation",
    ),
    "deprecation": AttributeSpec(
        name="deprecation",
        display_name="Deprecation",
        entity_types=frozenset({"dataset", "dashboard", "glossary_term"}),
        json_path="deprecated",
        exists_check="boolean_true",
        synonyms=("deprecated", "deprecation", "ngừng sử dụng", "không dùng nữa",
                  "retired", "legacy"),
        description="Deprecation status",
    ),
}

ENTITY_TYPES = frozenset({"dataset", "dashboard", "glossary_term", "document", "container", "dataflow"})

# ---------------------------------------------------------------------------
# Typo normalization via attribute registry
# ---------------------------------------------------------------------------

_SYNONYM_TO_ATTR: dict[str, str] = {}
for _spec in ATTRIBUTE_REGISTRY.values():
    for _syn in _spec.synonyms:
        _key = _syn.lower()
        _SYNONYM_TO_ATTR[_key] = _spec.name
        # Also add ASCII-normalized version for diacritics-insensitive matching
        import unicodedata
        _key_norm = unicodedata.normalize("NFKD", _key).encode("ascii", "ignore").decode("ascii")
        if _key_norm != _key:
            _SYNONYM_TO_ATTR[_key_norm] = _spec.name


def normalize_attribute(token: str) -> str | None:
    """Resolve a token (possibly typo) to a canonical attribute name.

    Uses exact synonym match, then fuzzy prefix matching.
    Returns None if no attribute matches with sufficient confidence.
    """
    t = token.lower().strip()
    # Exact synonym match
    if t in _SYNONYM_TO_ATTR:
        return _SYNONYM_TO_ATTR[t]
    # Try without diacritics
    import unicodedata
    t_norm = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    if t_norm in _SYNONYM_TO_ATTR:
        return _SYNONYM_TO_ATTR[t_norm]
    # Prefix match: "linage" -> "lineage" via edit distance.
    # Only for tokens >= 4 chars to avoid false positives (e.g., "ton" → "tag").
    if len(t) >= 4:
        for syn, attr_name in _SYNONYM_TO_ATTR.items():
            if len(syn) >= 4 and _edit_distance(t, syn) <= len(syn) // 4:
                return attr_name
    return None


def _edit_distance(a: str, b: str) -> int:
    """Simple Levenshtein distance."""
    if len(a) > len(b):
        a, b = b, a
    costs = list(range(len(a) + 1))
    for i, bc in enumerate(b):
        new_costs = [i + 1]
        for j, ac in enumerate(a):
            new_costs.append(costs[j] if ac == bc else min(costs[j], costs[j + 1], new_costs[-1]) + 1)
        costs = new_costs
    return costs[-1]
