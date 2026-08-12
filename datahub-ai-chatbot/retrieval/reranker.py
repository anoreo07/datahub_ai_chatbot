"""Four-signal reranker.

Ranks retrieved ``SearchResult``s by a weighted blend of four independent
signals (the Metadata Intelligence Assistant spec):

- semantic: how close the entity name/content is to the question text.
- graph: lineage/impact proximity (impact depth, being a source/consumer of the
  primary entity, graph traversal metadata).
- metadata: richness of the entity payload (description, owners, domain,
  schema fields, lineage edges).
- citation: whether the entity already carries citation / evidence metadata.

Each signal is normalized to [0, 1]; the final score keeps the upstream
retrieval ``score`` as the dominant anchor so base relevance is never drowned
out. Per-signal breakdowns are recorded in each result's payload under
``rerank_scores`` for observability.
"""

from __future__ import annotations

from collections.abc import Sequence

import structlog

from retrieval.fuzzy import fuzzy_score
from retrieval.hybrid_search import SearchResult

log = structlog.get_logger()

_WEIGHTS = {
    "base": 0.5,
    "semantic": 0.2,
    "graph": 0.15,
    "metadata": 0.1,
    "citation": 0.05,
}


class Reranker:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or _WEIGHTS

    async def rerank(self, query: str, results: Sequence[SearchResult]) -> list[SearchResult]:
        if not results:
            return []

        scored: list[tuple[SearchResult, dict[str, float]]] = []
        for r in results:
            signals = {
                "semantic": self._semantic_score(query, r),
                "graph": self._graph_score(r),
                "metadata": self._metadata_score(r),
                "citation": self._citation_score(r),
            }
            base = max(0.0, min(1.0, r.score))
            final = (
                self._weights["base"] * base
                + self._weights["semantic"] * signals["semantic"]
                + self._weights["graph"] * signals["graph"]
                + self._weights["metadata"] * signals["metadata"]
                + self._weights["citation"] * signals["citation"]
            )
            r.score = round(final, 4)
            payload = dict(r.payload or {})
            payload["rerank_scores"] = signals
            r.payload = payload
            scored.append((r, signals))

        scored.sort(key=lambda t: t[1]["semantic"], reverse=True)
        scored.sort(key=lambda t: t[0].score, reverse=True)

        log.info("reranker_done", input=len(results), output=len(scored))
        return [r for r, _ in scored]

    # ---- signals -----------------------------------------------------------

    @staticmethod
    def _semantic_score(query: str, result: SearchResult) -> float:
        """Similarity between the question and the entity name/content."""
        name_score = fuzzy_score(query, result.name) if result.name else 0.0
        content = (result.payload or {}).get("content", "") or result.snippet or ""
        content_score = fuzzy_score(query, content[:400]) if content else 0.0
        return max(name_score, content_score * 0.7)

    @staticmethod
    def _graph_score(result: SearchResult) -> float:
        """Lineage/impact proximity signals embedded by the tools layer."""
        payload = result.payload or {}
        depth = payload.get("impact_depth")
        if isinstance(depth, int):
            # Closer to the root is more relevant.
            return max(0.0, 1.0 - depth * 0.2)
        if payload.get("impact_leaf"):
            return 0.4
        if payload.get("live_lineage") or payload.get("upstreams") or payload.get("downstreams"):
            return 0.5
        return 0.0

    @staticmethod
    def _metadata_score(result: SearchResult) -> float:
        """Richness of the metadata payload (higher is more complete)."""
        payload = result.payload or {}
        parts = 0
        if payload.get("description"):
            parts += 1
        if payload.get("owners"):
            parts += 1
        if payload.get("domain"):
            parts += 1
        if payload.get("platform"):
            parts += 1
        if payload.get("schema_fields"):
            parts += 1
        if payload.get("upstreams") or payload.get("downstreams"):
            parts += 1
        return min(1.0, parts / 5)

    @staticmethod
    def _citation_score(result: SearchResult) -> float:
        """Whether the entity already carries citation/evidence metadata."""
        payload = result.payload or {}
        if payload.get("citation_ids") or payload.get("citations"):
            return 1.0
        if payload.get("impact_depth") is not None:
            return 0.6
        return 0.0
