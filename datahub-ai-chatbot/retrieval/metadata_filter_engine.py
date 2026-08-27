"""Metadata Filter Engine.

Executes GenericMetadataQuery against PostgreSQL + payload JSON.
Uses SQL-level filtering where possible (entity_type, domain, platform)
and JSON-level filtering for payload fields (owners, tags, lineage, etc.).

Performance: O(N) over filtered entity_type, NOT full catalog scan.
For 8,500+ datasets: SQL WHERE entity_type='dataset' + JSON checks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Entity
from retrieval.metadata_query import (
    ATTRIBUTE_REGISTRY,
    FilterOperation,
    GenericMetadataQuery,
    MetadataFilter,
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# JSON check builders (PostgreSQL jsonb)
# ---------------------------------------------------------------------------

def _json_exists_check(column: str, json_path: str, check_type: str) -> str:
    """Build a SQL fragment for checking JSON field existence.

    column: table column name (e.g. 'payload')
    json_path: JSON key (e.g. 'owners')
    check_type: 'not_null', 'array_not_empty', 'not_empty_string', 'lineage_edges', 'boolean_true'
    """
    jp = f"(payload->'{json_path}')::jsonb"
    jp_raw = f"payload->'{json_path}'"
    if check_type == "not_null":
        return f"{jp_raw} IS NOT NULL"
    elif check_type == "array_not_empty":
        return f"{jp_raw} IS NOT NULL AND jsonb_array_length({jp}) > 0"
    elif check_type == "not_empty_string":
        return f"{jp_raw} IS NOT NULL AND {jp_raw} != '\"\"' AND {jp_raw} != 'null'"
    elif check_type == "lineage_edges":
        return (
            "((payload->'upstreams') IS NOT NULL AND jsonb_array_length((payload->'upstreams')::jsonb) > 0)"
            " OR "
            "((payload->'downstreams') IS NOT NULL AND jsonb_array_length((payload->'downstreams')::jsonb) > 0)"
        )
    elif check_type == "boolean_true":
        return f"{jp_raw} = true"
    return f"{jp_raw} IS NOT NULL"


def _json_missing_check(column: str, json_path: str, check_type: str) -> str:
    """Build a SQL fragment for checking JSON field absence/emptiness."""
    jp_raw = f"payload->'{json_path}'"
    jp = f"({jp_raw})::jsonb"
    if check_type == "not_null":
        return f"({jp_raw} IS NULL OR {jp_raw} = 'null')"
    elif check_type == "array_not_empty":
        return f"({jp_raw} IS NULL OR jsonb_array_length({jp}) = 0)"
    elif check_type == "not_empty_string":
        return f"({jp_raw} IS NULL OR {jp_raw} = '\"\"' OR {jp_raw} = 'null')"
    elif check_type == "lineage_edges":
        return (
            "((payload->'upstreams') IS NULL OR jsonb_array_length((payload->'upstreams')::jsonb) = 0)"
            " AND "
            "((payload->'downstreams') IS NULL OR jsonb_array_length((payload->'downstreams')::jsonb) = 0)"
        )
    elif check_type == "boolean_true":
        return f"({jp} IS NULL OR {jp} != true)"
    return f"({jp} IS NULL)"


def _build_filter_clause(f: MetadataFilter) -> str | None:
    """Build a SQL WHERE clause fragment for a single MetadataFilter."""
    spec = ATTRIBUTE_REGISTRY.get(f.attribute)
    if spec is None:
        return None

    check_type = spec.exists_check

    # --- SQL-column-based checks (indexed, fast) ---
    if spec.sql_column in ("domain", "platform", "environment"):
        col = spec.sql_column
        if f.operation == FilterOperation.EXISTS:
            return f"{col} IS NOT NULL AND {col} != ''"
        elif f.operation == FilterOperation.MISSING:
            return f"({col} IS NULL OR {col} = '')"
        elif f.operation == FilterOperation.EQUALS and f.value:
            # Case-insensitive match
            return f"LOWER({col}) = LOWER(:val_{f.attribute})"
        elif f.operation == FilterOperation.NOT_EQUALS and f.value:
            return f"LOWER({col}) != LOWER(:val_{f.attribute})"

    if spec.sql_column == "description":
        if f.operation == FilterOperation.EXISTS:
            return "description IS NOT NULL AND description != ''"
        elif f.operation == FilterOperation.MISSING:
            return "(description IS NULL OR description = '')"

    # --- JSON-based checks (payload column) ---
    jp = f"payload->'{spec.json_path}'"

    if f.operation == FilterOperation.EXISTS:
        return _json_exists_check("payload", spec.json_path, check_type)
    elif f.operation == FilterOperation.MISSING:
        return _json_missing_check("payload", spec.json_path, check_type)
    elif f.operation == FilterOperation.EQUALS and f.value:
        if check_type == "not_empty_string":
            # String field: case-insensitive contains
            return f"LOWER({jp}::text) LIKE LOWER(:val_{f.attribute})"
        elif check_type == "array_not_empty":
            # Array field: check if value is in array
            return f"{jp} @> :val_{f.attribute}"
        return None
    elif f.operation == FilterOperation.NOT_EQUALS and f.value:
        if check_type == "not_empty_string":
            return f"(LOWER({jp}::text) NOT LIKE LOWER(:val_{f.attribute}) OR {jp} IS NULL)"
        return None

    return None


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class MetadataFilterEngine:
    """Executes GenericMetadataQuery against the database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, query: GenericMetadataQuery) -> MetadataQueryResult:
        """Execute the query and return results."""
        entity_type = query.entity_type

        # Build base query
        stmt = select(Entity).where(Entity.entity_type == entity_type)

        # Apply filters
        bind_params: dict[str, Any] = {}
        for f in query.filters:
            clause = _build_filter_clause(f)
            if clause:
                stmt = stmt.where(text(clause))
                # Add bind parameters for value-based filters
                if f.value and f.attribute in ("domain", "platform", "environment",
                                                 "description"):
                    bind_params[f"val_{f.attribute}"] = f"%{f.value}%" if f.operation == FilterOperation.EQUALS else f.value
                elif f.value and f.operation == FilterOperation.EQUALS:
                    bind_params[f"val_{f.attribute}"] = json.dumps([f.value])

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        if bind_params:
            count_result = await self._session.execute(count_stmt, bind_params)
        else:
            count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Fetch results
        stmt = stmt.order_by(Entity.name)
        stmt = stmt.offset(query.offset).limit(query.limit)
        if bind_params:
            result = await self._session.execute(stmt, bind_params)
        else:
            result = await self._session.execute(stmt)
        entities = list(result.scalars().all())

        return MetadataQueryResult(
            query=query,
            entities=entities,
            total_count=total_count,
            returned_count=len(entities),
        )


@dataclass
class MetadataQueryResult:
    query: GenericMetadataQuery
    entities: list  # list[Entity]
    total_count: int
    returned_count: int

    def to_answer_text(self) -> str:
        """Build a human-readable answer from the results."""
        q = self.query
        entity_label = q.entity_type.replace("_", " ")

        # Count sentence
        if self.total_count == 0:
            count_text = f"Không tìm thấy {entity_label} nào"
            if q.filters:
                conditions = " và ".join(
                    self._filter_description(f) for f in q.filters
                )
                count_text += f" {conditions}"
            count_text += "."
        else:
            count_text = f"Có **{self.total_count}** {entity_label}"
            if q.filters:
                conditions = " và ".join(
                    self._filter_description(f) for f in q.filters
                )
                count_text += f" {conditions}"
            count_text += "."

        # Listing
        if self.entities and (q.include_count or self.total_count > 0):
            lines = [count_text, ""]
            if self.returned_count < self.total_count:
                lines.append(
                    f"Dưới đây là {self.returned_count} {entity_label} đầu tiên "
                    f"(trong tổng số {self.total_count}):"
                )
                lines.append("")
            for i, e in enumerate(self.entities, 1):
                name = e.display_name or e.name or e.urn
                parts = [f"**{i}. {name}**"]
                if e.platform:
                    parts.append(f"Platform: {e.platform}")
                if e.environment:
                    parts.append(f"Env: {e.environment}")
                if e.domain:
                    parts.append(f"Domain: {e.domain}")
                lines.append("  ".join(parts))
            return "\n".join(lines)

        return count_text

    def _filter_description(self, f: MetadataFilter) -> str:
        spec = ATTRIBUTE_REGISTRY.get(f.attribute)
        label = spec.display_name if spec else f.attribute
        if f.operation == FilterOperation.EXISTS:
            return f"có {label.lower()}"
        elif f.operation == FilterOperation.MISSING:
            return f"thiếu {label.lower()}"
        elif f.operation == FilterOperation.EQUALS:
            return f"{label.lower()} = {f.value}"
        elif f.operation == FilterOperation.NOT_EQUALS:
            return f"{label.lower()} ≠ {f.value}"
        return f"{label.lower()} {f.operation.value}"

    def to_citations(self) -> list[dict]:
        """Build citation objects for each entity in results."""
        citations = []
        for e in self.entities:
            citations.append({
                "id": e.urn,
                "entity_urn": e.urn,
                "entity_name": e.display_name or e.name,
                "entity_type": e.entity_type,
                "source_type": "datahub_entity",
                "url": e.datahub_url,
            })
        return citations
