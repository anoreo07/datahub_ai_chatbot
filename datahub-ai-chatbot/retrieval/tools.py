"""Multi-tool orchestration layer.

Each public method is an executable "tool" that operates on DataHub metadata and
returns a list of ``SearchResult`` (or ``Entity`` rows). The ``ToolRegistry``
backs the query planner: a planned step becomes a tool call. Tools build on the
repository, the entity resolver, the metadata graph and (optionally) live
DataHub lineage.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.repositories.entity_repository import EntityRepository
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from retrieval.entity_resolver import EntityResolver
from retrieval.graph import ImpactResult, MetadataGraph
from retrieval.hybrid_search import SearchResult

log = structlog.get_logger()


def _payload_text(entity: Any) -> str:
    """Compact text representation of an entity payload for the generator."""
    payload = (entity.payload or {}) if entity is not None else {}
    parts: list[str] = []
    name = payload.get("display_name") or payload.get("name", "")
    if name:
        parts.append(f"Name: {name}")
    desc = payload.get("description")
    if desc:
        parts.append(f"Description: {desc}")
    domain = payload.get("domain")
    if domain:
        parts.append(f"Domain: {domain}")
    platform = payload.get("platform")
    if platform:
        parts.append(f"Platform: {platform}")
    owners = payload.get("owners") or []
    if owners:
        names = [o.get("name", "") for o in owners if isinstance(o, dict)]
        parts.append(f"Owners: {', '.join(names)}")
    fields = payload.get("schema_fields") or []
    if fields:
        lines = [
            f"  - {f.get('name','')} ({f.get('type','')}): {f.get('description','')}"
            if f.get("description") else f"  - {f.get('name','')} ({f.get('type','')})"
            for f in fields
        ]
        parts.append("Schema fields:\n" + "\n".join(lines))
    terms = payload.get("glossary_terms") or []
    if terms:
        parts.append(f"Glossary terms: {', '.join(terms)}")
    up = payload.get("upstreams") or []
    down = payload.get("downstreams") or []
    if up:
        parts.append(f"Upstream: {', '.join(up)}")
    if down:
        parts.append(f"Downstream: {', '.join(down)}")
    return " | ".join(parts)


class ToolRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EntityRepository(session)
        self._resolver = EntityResolver(session)
        self._graph = MetadataGraph(session)
        self._source: DataHubSource = create_datahub_source()

    # ---- entity helpers ----------------------------------------------------

    async def _entity_to_result(self, urn: str, score: float = 0.9,
                                enrich: bool = False) -> SearchResult | None:
        entity = await self._repo.get_by_urn(urn)
        if not entity:
            return None
        payload = {**(entity.payload or {})}
        # Lineage is stored in entity.payload (upstreams/downstreams)
        return SearchResult(
            urn=entity.urn, entity_type=entity.entity_type,
            name=entity.display_name or entity.name, score=score,
            datahub_url=entity.datahub_url,
            payload={**payload, "content": _payload_text(entity)},
        )

    def _urn_name(self, urn: str) -> str:
        """Extract a readable name from a DataHub-style URN, or the URN itself.

        ``urn:li:dataset:(urn:li:dataPlatform:redshift,fact_sales,PROD)``
        -> ``fact_sales``. Falls back to the raw URN for arbitrary test URNs.
        """
        if urn.startswith("urn:li:"):
            inner = urn.split("(", 1)[-1].rstrip(")")
            parts = inner.split(",")
            if len(parts) >= 3 and urn.startswith("urn:li:dataset:"):
                return parts[1]
            if parts:
                return parts[0].split(":", 1)[-1]
        return urn

    async def _impact_content(self, base: str, summary: dict[str, Any]) -> str:
        """Append an impact blast-radius summary to the root result content so
        the generator can answer chain/longest-path questions."""
        parts: list[str] = [base] if base else []
        summary_blocks: list[str] = []
        critical = summary.get("critical_path") or []
        longest = summary.get("longest_chain") or []
        chain = longest or critical
        if chain:
            names = [await self._impact_name(u) for u in chain]
            summary_blocks.append(
                "Critical (longest) dependency chain: " + " -> ".join(names))
        immediate = summary.get("immediate") or []
        if immediate:
            names = sorted({await self._impact_name(u) for u in immediate})
            summary_blocks.append(f"Immediate downstream ({len(names)}): "
                                  + ", ".join(names))
        indirect = summary.get("indirect") or []
        if indirect:
            names = sorted({await self._impact_name(u) for u in indirect})
            summary_blocks.append(f"Indirect downstream ({len(names)}): "
                                  + ", ".join(names))
        domains = summary.get("affected_domains") or []
        if domains:
            summary_blocks.append("Affected domains: " + ", ".join(sorted(domains)))
        cycles = summary.get("cycles") or []
        if cycles:
            summary_blocks.append("Lineage cycles detected: " + str(len(cycles)))
        if summary_blocks:
            parts.append("Impact analysis:\n" + "\n".join(summary_blocks))
        return "\n\n".join(parts)

    async def _impact_name(self, urn: str) -> str:
        """Display name for a URN from the catalog, falling back to URN parse."""
        entity = await self._repo.get_by_urn(urn)
        if entity:
            return entity.display_name or entity.name or self._urn_name(urn)
        return self._urn_name(urn)

    async def _resolve(self, name: str, entity_type: str | None = None) -> str | None:
        """Resolve ``name`` to a canonical URN, or None."""
        if not name:
            return None
        resolution = await self._resolver.resolve(name, entity_type=entity_type)
        if resolution.resolved:
            return resolution.resolved.urn
        return None

    async def _live_lineage_urns(self, urn: str) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {"upstreams": [], "downstreams": []}
        try:
            up = await self._source.get_lineage(urn, direction="upstream")
            down = await self._source.get_lineage(urn, direction="downstream")
            result["upstreams"] = [
                r["entity"]["urn"]
                for r in up.get("relationships", []) if (r.get("entity") or {}).get("urn")
            ]
            result["downstreams"] = [
                r["entity"]["urn"]
                for r in down.get("relationships", []) if (r.get("entity") or {}).get("urn")
            ]
        except Exception:  # noqa: BLE001
            log.exception("tool_lineage_live_failed", urn=urn)
        return result

    # ---- tools -------------------------------------------------------------

    async def resolve_entity(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or params.get("entity") or ""
        entity_type = params.get("entity_type")
        urn = await self._resolve(name, entity_type)
        if not urn:
            return []
        result = await self._entity_to_result(urn, score=1.0)
        log.info("tool_resolve_entity", name=name, found=bool(result))
        return [result] if result else []

    async def schema_lookup(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        urn = await self._resolve(name, "dataset")
        if not urn:
            return []
        result = await self._entity_to_result(urn, score=1.0)
        return [result] if result else []

    async def owner_lookup(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        urn = await self._resolve(name)
        if not urn:
            return []
        result = await self._entity_to_result(urn, score=1.0)
        return [result] if result else []

    async def glossary_lookup(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        urn = await self._resolve(name, "glossary_term")
        if not urn:
            # Also try dataset (definitions may be asked for a table).
            urn = await self._resolve(name) or ""
        if not urn:
            return []
        result = await self._entity_to_result(urn, score=1.0)
        return [result] if result else []

    async def existence(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        urn = await self._resolve(name)
        return (await self.resolve_entity({"name": name})) if urn else []

    async def lineage(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        direction = params.get("direction") or "both"
        urn = await self._resolve(name, "dataset") or await self._resolve(name)
        if not urn:
            return []
        result = await self._entity_to_result(urn, score=1.0, enrich=True)
        if not result:
            return []
        payload = result.payload or {}
        live = payload.get("live_lineage") or {}
        up = live.get("upstreams") or payload.get("upstreams") or []
        down = live.get("downstreams") or payload.get("downstreams") or []
        entities: list[SearchResult] = [result]
        if direction in ("upstream", "both"):
            for u in up:
                rel = await self._entity_to_result(u, score=0.8)
                if rel:
                    entities.append(rel)
        if direction in ("downstream", "both"):
            for d in down:
                rel = await self._entity_to_result(d, score=0.75)
                if rel:
                    entities.append(rel)
        return entities

    async def recursive_impact(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        depth = int(params.get("depth") or settings.IMPACT_DEFAULT_DEPTH)
        max_nodes = int(params.get("max_nodes") or settings.IMPACT_MAX_NODES)
        urn = await self._resolve(name, "dataset") or await self._resolve(name)
        if not urn:
            return []
        impact: ImpactResult = await self._graph.impact(urn, depth=depth, max_nodes=max_nodes)
        summary: dict[str, Any] = await self._graph.impact_summary(
            urn, depth=depth, max_nodes=max_nodes)
        root = await self._entity_to_result(urn, score=1.0, enrich=True)
        results: list[SearchResult] = [root] if root else []
        for node in impact.nodes:
            rel = await self._entity_to_result(node.urn, score=max(0.5, 1.0 - node.depth * 0.15))
            if rel:
                rel.payload["impact_depth"] = node.depth
                rel.payload["impact_leaf"] = node.urn in {n.urn for n in impact.leaf_nodes}
                results.append(rel)
        if results:
            # Blast-radius context for the generator: immediate vs indirect
            # impact, affected domains/owners/dashboards/pipelines and the
            # critical (longest) dependency chain.
            results[0].payload["impact_summary"] = summary
            results[0].payload["content"] = await self._impact_content(
                results[0].payload.get("content", ""), summary)
        log.info("tool_recursive_impact", root=name, urn=urn,
                 nodes=impact.count, depth=impact.depth_reached, truncated=impact.truncated,
                 immediate=summary.get("immediate_count"), indirect=summary.get("indirect_count"),
                 critical_length=summary.get("critical_length"))
        return results

    async def sources(self, params: dict[str, Any]) -> list[SearchResult]:
        name = params.get("name") or ""
        depth = int(params.get("depth") or settings.IMPACT_DEFAULT_DEPTH)
        max_nodes = int(params.get("max_nodes") or settings.IMPACT_MAX_NODES)
        urn = await self._resolve(name, "dataset") or await self._resolve(name)
        if not urn:
            return []
        src: ImpactResult = await self._graph.sources(urn, depth=depth, max_nodes=max_nodes)
        root = await self._entity_to_result(urn, score=1.0)
        results: list[SearchResult] = [root] if root else []
        for node in src.nodes:
            rel = await self._entity_to_result(node.urn, score=max(0.5, 1.0 - node.depth * 0.15))
            if rel:
                results.append(rel)
        return results

    async def term_to_datasets(self, params: dict[str, Any]) -> list[SearchResult]:
        term = params.get("term") or params.get("name") or ""
        urn = await self._resolve(term, "glossary_term")
        if not urn:
            return []
        datasets = await self._repo.list_by_type("dataset", limit=2000)
        matching: list[SearchResult] = []
        for e in datasets:
            terms = (e.payload or {}).get("glossary_terms") or []
            if urn in terms or any(urn in (t or "") for t in terms):
                rel = await self._entity_to_result(e.urn, score=0.9)
                if rel:
                    matching.append(rel)
        log.info("tool_term_to_datasets", term=term, matching=len(matching))
        return matching

    async def list_by_dimension(self, params: dict[str, Any]) -> list[SearchResult]:
        dimension = params.get("dimension") or ""
        value = params.get("value") or ""
        entity_type = params.get("entity_type")
        limit = int(params.get("limit") or 200)
        if dimension == "domain":
            entities = await self._repo.list_by_domain(value, entity_type, limit)
        elif dimension == "platform":
            entities = await self._repo.list_by_platform(value, entity_type, limit)
        elif dimension == "tag":
            entities = await self._repo.list_by_tag(value, entity_type, limit)
        elif dimension == "owner":
            entities = await self._repo.list_by_owner(value, entity_type, limit)
        elif dimension == "certified":
            entities = await self._repo.list_certified(entity_type, limit)
        else:
            return []
        results = [r for e in entities if (r := await self._entity_to_result(e.urn, score=0.9))]
        return results[:limit]

    async def list_by_type(self, params: dict[str, Any]) -> list[SearchResult]:
        entity_type = params.get("entity_type") or "dataset"
        limit = int(params.get("limit") or 200)
        entities = await self._repo.list_by_type(entity_type, limit=limit)
        results = [r for e in entities if (r := await self._entity_to_result(e.urn, score=0.9))]
        return results

    async def count_entities(self, params: dict[str, Any]) -> list[SearchResult]:
        entity_type = params.get("entity_type")
        domain = params.get("domain") or params.get("dimension_value")
        platform = params.get("platform")
        tag = params.get("tag")
        owner = params.get("owner")

        if domain:
            entities = list(await self._repo.list_by_domain(domain, entity_type=entity_type, limit=5000))
            total = len(entities)
        elif platform:
            entities = list(await self._repo.list_by_platform(platform, entity_type=entity_type, limit=5000))
            total = len(entities)
        elif tag:
            entities = list(await self._repo.list_by_tag(tag, entity_type=entity_type, limit=5000))
            total = len(entities)
        elif owner:
            entities = list(await self._repo.list_by_owner(owner, entity_type=entity_type, limit=5000))
            total = len(entities)
        else:
            total = await self._repo.count_by_type(entity_type)
            entities = list(await self._repo.list_by_type(entity_type or "dataset", limit=20))

        if total == 0:
            return []
        results = [r for e in entities[:20] if (r := await self._entity_to_result(e.urn, score=0.9))]
        if results:
            results[0].payload = {**results[0].payload, "count": total}
            if domain:
                results[0].payload["domain"] = domain
            if platform:
                results[0].payload["platform"] = platform
        return results

    async def document_qa(self, params: dict[str, Any]) -> list[SearchResult]:
        # Documents are indexed as entity chunks; return an empty result so the
        # RAG/vector path handles document content retrieval.
        return []

    async def execute(self, op: str, params: dict[str, Any]) -> list[SearchResult]:
        handler = getattr(self, op, None)
        if handler is None:
            log.warning("tool_unknown_op", op=op)
            return []
        try:
            results = await handler(params)
            return results or []
        except Exception:  # noqa: BLE001
            log.exception("tool_failed", op=op, params=params)
            return []
