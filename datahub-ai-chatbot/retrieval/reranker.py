from collections.abc import Sequence

from retrieval.hybrid_search import SearchResult


class Reranker:
    async def rerank(self, query: str, results: Sequence[SearchResult]) -> list[SearchResult]:
        if not results:
            return []
        scored = list(results)
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored
