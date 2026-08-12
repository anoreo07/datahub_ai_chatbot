"""Metadata graph traversal and recursive impact analysis.

The graph is derived from the lineage edges stored in each entity's payload
(``upstreams`` / ``downstreams`` lists of URNs). ``MetadataGraph`` exposes a
BFS traversal with a depth limit plus helpers for impact/blast-radius queries:

- ``impact``: all downstream descendants within ``depth`` hops (consumers).
- ``sources``: all upstream ancestors within ``depth`` hops (producers).
- ``path``: the shortest upstream/downstream chain between two URNs.

Lineage edges are resolved lazily and cached per-instance to avoid re-querying
the repository for repeated lookups.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.repositories.entity_repository import EntityRepository

log = structlog.get_logger()


class GraphNode:
    """A single node in the metadata graph (an entity reached by lineage)."""

    __slots__ = ("urn", "name", "entity_type", "depth", "direction")

    def __init__(self, urn: str, name: str = "", entity_type: str = "",
                 depth: int = 0, direction: str = "downstream") -> None:
        self.urn = urn
        self.name = name
        self.entity_type = entity_type
        self.depth = depth
        self.direction = direction

    def to_dict(self) -> dict[str, Any]:
        return {
            "urn": self.urn,
            "name": self.name,
            "entity_type": self.entity_type,
            "depth": self.depth,
            "direction": self.direction,
        }


class ImpactResult:
    """Outcome of a recursive impact (or source) analysis."""

    def __init__(self, root_urn: str, root_name: str = "") -> None:
        self.root_urn = root_urn
        self.root_name = root_name
        self.nodes: list[GraphNode] = []
        self.leaf_nodes: list[GraphNode] = []
        self.depth_reached: int = 0
        self.truncated: bool = False

    @property
    def urns(self) -> list[str]:
        return [n.urn for n in self.nodes]

    @property
    def count(self) -> int:
        return len(self.nodes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_urn": self.root_urn,
            "root_name": self.root_name,
            "count": self.count,
            "depth_reached": self.depth_reached,
            "truncated": self.truncated,
            "nodes": [n.to_dict() for n in self.nodes],
            "leaf_nodes": [n.to_dict() for n in self.leaf_nodes],
        }


class MetadataGraph:
    """BFS traversal over lineage edges stored in entity payloads."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = EntityRepository(session)
        self._entities: dict[str, Any] = {}
        self._loaded_urns: set[str] = set()

    async def _load(self, urn: str) -> Any | None:
        if urn not in self._entities:
            entity = await self._repo.get_by_urn(urn)
            self._entities[urn] = entity
        return self._entities.get(urn)

    def _edges(self, entity: Any, direction: str) -> list[str]:
        payload = (entity.payload or {}) if entity is not None else {}
        key = "upstreams" if direction == "upstream" else "downstreams"
        return [u for u in (payload.get(key) or []) if isinstance(u, str)]

    async def neighbors(self, urn: str, direction: str) -> list[str]:
        """Direct lineage neighbors of ``urn`` in ``direction``."""
        entity = await self._load(urn)
        return self._edges(entity, direction)

    async def _bfs(self, root: str, direction: str, depth: int,
                   max_nodes: int, exclude: Sequence[str] = ()) -> ImpactResult:
        result = ImpactResult(root_urn=root)
        if depth <= 0:
            return result
        root_entity = await self._load(root)
        result.root_name = (root_entity.display_name or root_entity.name) if root_entity else root
        if not root_entity:
            return result

        seen: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root, 0)])
        excluded = set(exclude)

        while queue:
            urn, d = queue.popleft()
            if urn in seen:
                continue
            seen.add(urn)
            entity = await self._load(urn)
            if entity is None:
                continue
            if d > 0:
                node = GraphNode(
                    urn=urn,
                    name=entity.display_name or entity.name,
                    entity_type=entity.entity_type,
                    depth=d,
                    direction=direction,
                )
                result.nodes.append(node)
                if d > result.depth_reached:
                    result.depth_reached = d
            if d >= depth:
                continue
            for neighbor in self._edges(entity, direction):
                if neighbor == root or neighbor in excluded:
                    continue
                if neighbor not in seen and len(seen) < max_nodes:
                    queue.append((neighbor, d + 1))
                elif neighbor not in seen:
                    result.truncated = True

        # Leaf nodes = deepest nodes with no further children in this direction.
        reached = {n.urn for n in result.nodes}
        leaf_candidates = result.nodes
        has_child = set()
        for node in result.nodes:
            entity = await self._load(node.urn)
            for neighbor in self._edges(entity, direction):
                if neighbor in reached:
                    has_child.add(node.urn)
                    break
        result.leaf_nodes = [n for n in leaf_candidates if n.urn not in has_child]
        return result

    async def impact(self, urn: str, depth: int | None = None,
                     max_nodes: int | None = None) -> ImpactResult:
        """All downstream descendants (consumers) of ``urn``."""
        depth = depth or settings.IMPACT_DEFAULT_DEPTH
        depth = min(depth, settings.GRAPH_MAX_DEPTH)
        max_nodes = max_nodes or settings.IMPACT_MAX_NODES
        return await self._bfs(urn, "downstream", depth, max_nodes)

    async def sources(self, urn: str, depth: int | None = None,
                      max_nodes: int | None = None) -> ImpactResult:
        """All upstream ancestors (producers) of ``urn``."""
        depth = depth or settings.IMPACT_DEFAULT_DEPTH
        depth = min(depth, settings.GRAPH_MAX_DEPTH)
        max_nodes = max_nodes or settings.IMPACT_MAX_NODES
        return await self._bfs(urn, "upstream", depth, max_nodes)

    async def path(self, start: str, end: str, direction: str = "upstream",
                   depth: int | None = None) -> list[str]:
        """Shortest lineage path between two URNs (BFS), or [] if unreachable."""
        depth = depth or settings.GRAPH_MAX_DEPTH
        if start == end:
            return [start]
        frontier: deque[list[str]] = deque([[start]])
        seen: set[str] = set()
        while frontier:
            chain = frontier.popleft()
            last = chain[-1]
            if last in seen:
                continue
            seen.add(last)
            if len(chain) - 1 > depth:
                continue
            for neighbor in await self.neighbors(last, direction):
                nxt = chain + [neighbor]
                if neighbor == end:
                    return nxt
                if neighbor not in seen:
                    frontier.append(nxt)
        return []

    async def connected_components(self, urn: str, direction: str = "downstream",
                                   depth: int | None = None,
                                   max_nodes: int | None = None) -> list[GraphNode]:
        """Return the reachable subgraph as a flat, de-duplicated node list."""
        result = await self._bfs(
            urn, direction, depth or settings.GRAPH_MAX_DEPTH,
            max_nodes or settings.IMPACT_MAX_NODES,
        )
        return result.nodes

    def _load_nodes(self, urns: Iterable[str]) -> Sequence[Any]:
        return list(urns)

    # ---- advanced graph reasoning ------------------------------------------

    async def all_paths(self, start: str, direction: str = "downstream",
                        depth: int | None = None,
                        max_nodes: int | None = None) -> list[list[str]]:
        """All dependency chains (root -> leaf) by DFS within ``depth`` hops.

        Used to compute the longest/critical path of an impact analysis.
        """
        depth = depth or settings.GRAPH_MAX_DEPTH
        max_nodes = max_nodes or settings.IMPACT_MAX_NODES
        paths: list[list[str]] = []
        visited: set[str] = set()

        def _has_neighbors(entity: Any) -> bool:
            return bool(self._edges(entity, direction))

        async def _walk(chain: list[str]) -> None:
            last = chain[-1]
            if len(visited) >= max_nodes:
                return
            entity = await self._load(last)
            neighbors = self._edges(entity, direction) if entity else []
            if not neighbors:
                if len(chain) > 1:
                    paths.append(list(chain))
                return
            for n in neighbors:
                if n in visited:
                    continue
                if len(chain) >= depth + 1:
                    continue
                visited.add(n)
                await _walk(chain + [n])

        visited.add(start)
        await _walk([start])
        if not paths:
            entity = await self._load(start)
            if self._edges(entity, direction):
                paths.append([start])
        return paths

    async def longest_path(self, start: str, direction: str = "downstream",
                           depth: int | None = None) -> list[str]:
        """Longest (critical) dependency chain reachable from ``start``."""
        paths = await self.all_paths(start, direction=direction, depth=depth)
        if not paths:
            return [start]
        return max(paths, key=len)

    async def detect_cycles(self, urn: str, direction: str = "downstream",
                            depth: int | None = None) -> list[list[str]]:
        """Return any lineage cycles reachable from ``urn`` (DFS with back-edge)."""
        depth = depth or settings.GRAPH_MAX_DEPTH
        cycles: list[list[str]] = []
        colour: dict[str, int] = {}  # 1=grey(in stack), 2=black(done)
        stack: list[str] = []

        async def _dfs(node: str) -> None:
            colour[node] = 1
            stack.append(node)
            entity = await self._load(node)
            for nb in self._edges(entity, direction) if entity else []:
                if len(stack) > depth + 1:
                    continue
                if colour.get(nb) == 1:
                    idx = stack.index(nb) if nb in stack else 0
                    cycles.append(stack[idx:] + [nb])
                    continue
                if colour.get(nb, 0) == 0:
                    await _dfs(nb)
            stack.pop()
            colour[node] = 2

        await _dfs(urn)
        return cycles

    async def impact_summary(self, urn: str, depth: int | None = None,
                             max_nodes: int | None = None) -> dict[str, Any]:
        """Aggregate an impact analysis: immediate vs indirect nodes plus the
        affected domains / owner teams / dashboards / pipelines.

        Returns a dict suitable for the generator to explain blast radius:
        - ``immediate``: depth=1 consumers (direct dependents).
        - ``indirect``: depth>1 consumers (transitive dependents).
        - ``critical_path`` / ``longest_chain``: the deepest dependency chain.
        - ``affected_domains`` / ``affected_owners`` / ``affected_dashboards`` /
          ``affected_pipelines``: deduplicated metadata of impacted nodes.
        """
        result = await self.impact(urn, depth=depth, max_nodes=max_nodes)
        nodes = result.nodes
        immediate = [n.urn for n in nodes if n.depth == 1]
        indirect = [n.urn for n in nodes if n.depth > 1]
        critical = await self.longest_path(urn, direction="downstream", depth=depth)

        domains: set[str] = set()
        owners: set[str] = set()
        dashboards: set[str] = set()
        pipelines: set[str] = set()
        for n in nodes:
            entity = await self._load(n.urn)
            payload = (entity.payload or {}) if entity is not None else {}
            d = (entity.domain if entity is not None else None) \
                or payload.get("domain")
            if d:
                domains.add(str(d))
            for o in payload.get("owners") or []:
                if isinstance(o, dict) and o.get("name"):
                    owners.add(str(o["name"]))
            if n.entity_type == "dashboard":
                dashboards.add(n.name or n.urn)
            elif n.entity_type in ("dataFlow", "dataJob", "pipeline", "job"):
                pipelines.add(n.name or n.urn)

        cycle = await self.detect_cycles(urn, depth=depth)
        return {
            "root_urn": urn,
            "root_name": result.root_name,
            "total": result.count,
            "immediate": immediate,
            "indirect": indirect,
            "immediate_count": len(immediate),
            "indirect_count": len(indirect),
            "critical_path": critical,
            "critical_length": len(critical),
            "longest_chain": critical,
            "affected_domains": sorted(domains),
            "affected_owners": sorted(owners),
            "affected_dashboards": sorted(dashboards),
            "affected_pipelines": sorted(pipelines),
            "cycles": list(cycle),
            "truncated": result.truncated,
            "depth_reached": result.depth_reached,
        }
