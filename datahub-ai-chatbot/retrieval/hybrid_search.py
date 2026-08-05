from collections.abc import Sequence
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.repositories.entity_repository import EntityRepository
from indexing.embedder import Embedder, create_embedder
from indexing.vector_store import OpenSearchVectorStore
from indexing.vector_store import VectorSearchResult as OSResult
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from retrieval.entity_resolver import EntityResolver

log = structlog.get_logger()


class SearchResult:
    def __init__(self, urn: str, entity_type: str, name: str, score: float, snippet: str = "",
                 datahub_url: str | None = None, payload: dict | None = None) -> None:
        self.urn = urn
        self.entity_type = entity_type
        self.name = name
        self.score = score
        self.snippet = snippet
        self.datahub_url = datahub_url
        self.payload = payload or {}


class HybridSearch:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)
        self._entity_resolver = EntityResolver(session)
        self._vector_store = OpenSearchVectorStore()
        self._embedder: Embedder = create_embedder()
        self._source: DataHubSource = create_datahub_source()

    async def _search_mock_fallback(self, query: str) -> list[SearchResult]:
        from ingestion import create_datahub_source
        source = create_datahub_source()
        tokens = [t for t in query.lower().split() if len(t) > 2]
        seen: set[str] = set()
        results: list[SearchResult] = []
        for etype in ("dataset", "dashboard", "glossary_term", "document"):
            for token in tokens:
                matches = await source.search_entities(etype, token)
                for ent in matches:
                    if ent.deleted or ent.urn in seen:
                        continue
                    seen.add(ent.urn)
                    results.append(SearchResult(
                        urn=ent.urn, entity_type=ent.entity_type,
                        name=ent.display_name or ent.name, score=0.6,
                        datahub_url=ent.datahub_url,
                        payload=ent.model_dump(exclude={"raw_payload"}),
                    ))
        return results[:10]

    async def search(self, query: str, top_k: int = 10, **filters: Any) -> list[SearchResult]:
        trace_id = filters.pop("trace_id", None)
        resolution = await self._entity_resolver.resolve(query, trace_id=trace_id)
        if resolution.exact_match and resolution.resolved:
            log.info("hybrid_path", trace_id=trace_id,
                     query=query, path="exact_match",
                     resolved=resolution.resolved.name, count=1)
            return [await self._entity_to_result(resolution.resolved.urn)]

        if resolution.candidates:
            urns = [c.urn for c in resolution.candidates[:5]]
            results = await self._urns_to_results(urns)
            log.info("hybrid_path", trace_id=trace_id, query=query,
                     path="candidates", count=len(results))
            return results

        vector = await self._embedder.embed_query(query)
        os_results = await self._vector_store.hybrid_search(query, vector, size=top_k, **filters)
        results = await self._os_results_to_search_results(os_results)
        log.info("hybrid_path", trace_id=trace_id, query=query,
                 path="vector", count=len(results))
        if results:
            return results
        if settings.USE_FAKE_OPENSEARCH or settings.USE_MOCK_DATAHUB:
            results = await self._search_mock_fallback(query)
            log.info("hybrid_path", trace_id=trace_id, query=query,
                     path="mock_fallback", count=len(results))
            return results
        return results

    async def keyword_search(self, query: str, top_k: int = 10, **filters: Any) -> list[SearchResult]:
        os_results = await self._vector_store.keyword_search(query, size=top_k, **filters)
        return await self._os_results_to_search_results(os_results)

    async def _entity_to_result(self, urn: str) -> SearchResult:
        entity = await self._entity_repo.get_by_urn(urn)
        if not entity:
            return SearchResult(urn=urn, entity_type="", name="", score=0)
        return SearchResult(
            urn=entity.urn,
            entity_type=entity.entity_type,
            name=entity.display_name or entity.name,
            score=1.0,
            datahub_url=entity.datahub_url,
            payload=entity.payload,
        )

    async def _urns_to_results(self, urns: list[str]) -> list[SearchResult]:
        entities = await self._entity_repo.list_by_urns(urns)
        return [
            SearchResult(
                urn=e.urn, entity_type=e.entity_type, name=e.display_name or e.name,
                score=0.9, datahub_url=e.datahub_url, payload=e.payload,
            )
            for e in entities
        ]

    async def _os_results_to_search_results(self, results: Sequence[OSResult]) -> list[SearchResult]:
        out: list[SearchResult] = []
        seen: set[str] = set()
        for r in results:
            urn = r.payload.get("entity_urn", "")
            if urn in seen:
                continue
            seen.add(urn)
            out.append(SearchResult(
                urn=urn,
                entity_type=r.payload.get("entity_type", ""),
                name=r.payload.get("entity_name", ""),
                score=r.score,
                snippet=r.payload.get("content", "")[:300],
                datahub_url=r.payload.get("datahub_url"),
                payload=r.payload,
            ))
        return out

    async def search_by_entity_type(self, query: str, entity_type: str, top_k: int = 10) -> list[SearchResult]:
        return await self.search(query, top_k=top_k, entity_type=entity_type)
