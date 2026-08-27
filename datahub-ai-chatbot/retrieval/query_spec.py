"""QuerySpec — structured query representation for the entire pipeline.

Replaces the flat intent string + scattered entity_hint pattern with a
unified schema that carries scope, property, operator, and filters.

Root causes addressed:
  RC1: scope field distinguishes ENTITY vs GLOBAL queries
  RC2: property field decouples intent from entity
  RC3: operator field captures EXISTS/MISSING/EQUALS/GET
  RC5: missing/exists are operators, not separate intents
  RC6: property comes from registry, not from regex intent rules
  RC7: filters list supports multi-condition queries

Usage:
  question → QuerySpec → router decides path (entity lookup / global listing / etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Operation(StrEnum):
    """What the user wants to do — decoupled from entity type."""
    GET = "GET"              # Get a specific property value: "domain của X?"
    LIST = "LIST"            # List entities matching criteria: "dataset nào có lineage?"
    COUNT = "COUNT"          # Count entities: "có bao nhiêu dataset?"
    EXISTS = "EXISTS"        # Check if entity exists: "X có tồn tại không?"
    DEFINE = "DEFINE"        # Define a term: "term X là gì?"
    IMPACT = "IMPACT"        # Impact analysis: "nếu thay đổi X thì ảnh hưởng gì?"
    SQL = "SQL"              # Generate SQL
    SEMANTIC = "SEMANTIC"    # Free-form semantic search (fallback)


class Scope(StrEnum):
    """Whether the query targets a specific entity or a collection."""
    ENTITY = "ENTITY"        # Single entity: "dim_warehouse có domain gì?"
    GLOBAL = "GLOBAL"        # All entities of type: "dataset nào có lineage?"
    FILTERED = "FILTERED"    # Entities matching filter: "dataset thuộc domain SALES?"


class Operator(StrEnum):
    """How to evaluate the property — extracted from natural language."""
    GET = "GET"              # Get the value: "domain gì?"
    EXISTS = "EXISTS"        # Has the property: "có lineage?"
    MISSING = "MISSING"      # Doesn't have the property: "không có owner?", "thiếu description?"
    EQUALS = "EQUALS"        # Equals a value: "thuộc domain SALES"
    NOT_EQUALS = "NOT_EQUALS"
    CONTAINS = "CONTAINS"    # Contains a value (for array fields like tags)
    IN = "IN"                # Value is in a set
    NOT_IN = "NOT_IN"


class ResolutionStatus(StrEnum):
    """Whether the QuerySpec is complete or needs clarification."""
    READY = "READY"          # All required fields present
    NEEDS_ENTITY = "NEEDS_ENTITY"      # Entity reference missing
    NEEDS_PROPERTY = "NEEDS_PROPERTY"  # Property missing
    NEEDS_VALUE = "NEEDS_VALUE"        # Filter value missing
    AMBIGUOUS = "AMBIGUOUS"            # Multiple interpretations
    UNSUPPORTED = "UNSUPPORTED"        # Query type not supported


@dataclass
class QueryFilter:
    """A single filter condition."""
    attr: str                        # "domain", "platform", "owner", etc.
    operator: Operator = Operator.EXISTS
    value: str | None = None         # For EQUALS/CONTAINS/IN
    negated: bool = False            # True for NOT_EQUALS/NOT_IN/MISSING


@dataclass
class QuerySpec:
    """Structured representation of a user question.

    This is the contract between Query Understanding and everything downstream:
    - Query Planner (reads scope + operation to decide fast-path vs full-planning)
    - Execution Strategy Router (reads property + operator to route deterministic/semantic)
    - Evidence Assembly (reads property to know which fields to trace)
    - Evaluation (uses as golden format to compare actual vs expected)
    """
    # --- Core fields (always present) ---
    operation: Operation = Operation.GET
    scope: Scope = Scope.GLOBAL
    entity_type: str = "dataset"     # dataset, dashboard, glossary_term, document
    resolution_status: ResolutionStatus = ResolutionStatus.READY
    confidence: str = "medium"       # high | medium | low
    raw_question: str = ""

    # --- Entity reference (populated when scope=ENTITY) ---
    entity_name: str | None = None   # "dim_warehouse", "Bank Guarantee for tooling"
    entity_urn: str | None = None    # Full URN if resolved

    # --- Property/attribute (the metadata field being queried) ---
    # Named `attr` to avoid shadowing Python's `property` builtin.
    attr: str | None = None          # "domain", "owner", "lineage", "schema", etc.

    # --- Operator (how to evaluate the property) ---
    operator: Operator = Operator.GET
    value: str | None = None         # For EQUALS: "SALES", "powerbi"

    # --- Multi-filter support ---
    filters: list[QueryFilter] = field(default_factory=list)

    # --- Aggregation ---
    aggregation: str | None = None   # "count", "group_by", None

    # --- Pagination ---
    limit: int = 10
    offset: int = 0

    # --- Context from previous turn ---
    context_dependency: dict[str, Any] = field(default_factory=dict)
    # { carried_from_previous_turn: bool, carried_fields: [...] }

    # --- Derived from the above (computed, not set directly) ---
    _legacy_intent: str | None = None  # For backward compat during migration

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "scope": self.scope.value,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "entity_urn": self.entity_urn,
            "property": self.attr,
            "operator": self.operator.value,
            "value": self.value,
            "filters": [
                {"property": f.attr, "operator": f.operator.value,
                 "value": f.value, "negated": f.negated}
                for f in self.filters
            ],
            "aggregation": self.aggregation,
            "limit": self.limit,
            "resolution_status": self.resolution_status.value,
            "confidence": self.confidence,
        }

    @property
    def is_entity_scoped(self) -> bool:
        return self.scope == Scope.ENTITY

    @property
    def is_global(self) -> bool:
        return self.scope in (Scope.GLOBAL, Scope.FILTERED)

    @property
    def is_missing_query(self) -> bool:
        return self.operator == Operator.MISSING or any(
            f.operator == Operator.MISSING for f in self.filters
        )

    @property
    def is_count_query(self) -> bool:
        return self.operation == Operation.COUNT or self.aggregation == "count"

    def add_filter(self, prop: str, op: Operator, value: str | None = None) -> None:
        """Add a filter condition. Replaces existing filter on same property."""
        self.filters = [f for f in self.filters if f.attr != prop]
        self.filters.append(QueryFilter(attr=prop, operator=op, value=value))
        if len(self.filters) > 1:
            self.scope = Scope.FILTERED


# ---------------------------------------------------------------------------
# Legacy intent mapping — for backward compat during migration
# ---------------------------------------------------------------------------

def spec_to_legacy_intent(spec: QuerySpec) -> str:
    """Map QuerySpec to legacy QueryIntent string for routing.

    This is a TEMPORARY bridge — new code should use QuerySpec directly.
    """
    if spec.is_count_query:
        return "COUNT_ENTITIES"
    if spec.operation == Operation.DEFINE:
        return "TERM_DEFINITION"
    if spec.operation == Operation.IMPACT:
        return "IMPACT"
    if spec.operation == Operation.SQL:
        return "SQL_GENERATION"
    if spec.operation == Operation.SEMANTIC:
        return "GENERAL"

    # Property-based routing
    prop = spec.attr
    if prop == "lineage":
        return "LINEAGE"
    if prop == "schema":
        return "SCHEMA_LOOKUP"
    if prop == "owner":
        return "OWNER_LOOKUP" if spec.is_entity_scoped else "ENTITIES_BY_OWNER"
    if prop == "domain":
        return "ENTITY_DOMAIN" if spec.is_entity_scoped else "DOMAIN_QUERY"
    if prop == "platform":
        return "PLATFORM_QUERY"
    if prop == "tags":
        return "TAG_QUERY"
    if prop == "glossary":
        return "TERM_TO_DATASETS" if spec.is_entity_scoped else "TERM_DEFINITION"
    if prop == "description":
        return "SCHEMA_LOOKUP"  # closest legacy match

    # Missing queries
    if spec.is_missing_query:
        if prop == "owner":
            return "MISSING_OWNER"
        if prop == "description":
            return "MISSING_DESCRIPTION"
        if prop == "domain":
            return "MISSING_DOMAIN"

    if spec.operation == Operation.EXISTS:
        return "ENTITY_EXISTS"
    if spec.operation == Operation.LIST:
        return "LISTING"

    return "GENERAL"
