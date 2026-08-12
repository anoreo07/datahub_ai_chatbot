"""Graph expansion over the metadata lineage graph.

``GraphExpander`` exposes a lightweight, session-optional API so it can be used
as a plain helper (e.g. in tests or standalone expanders) without a running
database. When a session is supplied it delegates to ``MetadataGraph`` for real
BFS traversal; otherwise it returns an empty expansion.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class GraphExpander:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._graph = None
        if session is not None:
            from retrieval.graph import MetadataGraph
            self._graph = MetadataGraph(session)

    async def expand(self, urn: str, depth: int = 1) -> list[dict[str, Any]]:
        """Expand ``urn`` to its lineage neighbors (downstream), to ``depth``."""
        if self._graph is None:
            return []
        nodes = await self._graph.connected_components(urn, direction="downstream", depth=depth)
        return [node.to_dict() for node in nodes]
