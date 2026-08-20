from typing import Any

import structlog
from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk

from config.constants import OPENSEARCH_INDEX_NAME
from config.settings import settings

log = structlog.get_logger()


class VectorSearchResult:
    def __init__(self, id: str, score: float, payload: dict) -> None:
        self.id = id
        self.score = score
        self.payload = payload


INDEX_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "knn": True,
        },
        "analysis": {
            "analyzer": {
                "default": {
                    "type": "standard",
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "entity_urn": {"type": "keyword"},
            "entity_type": {"type": "keyword"},
            "entity_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "chunk_type": {"type": "keyword"},
            "content": {"type": "text"},
            "embedding": {"type": "knn_vector", "dimension": settings.EMBEDDING_DIMENSION},
            "owner_names": {"type": "keyword"},
            "term_urns": {"type": "keyword"},
            "domain": {"type": "keyword"},
            "platform": {"type": "keyword"},
            "environment": {"type": "keyword"},
            "datahub_url": {"type": "keyword"},
            "source_title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "page": {"type": "integer"},
            "section": {"type": "text"},
            "content_hash": {"type": "keyword"},
            "updated_at": {"type": "date"},
        }
    },
}


class OpenSearchVectorStore:
    def __init__(self) -> None:
        self._client = AsyncOpenSearch(
            hosts=[settings.OPENSEARCH_URL],
            http_auth=(settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD) if settings.OPENSEARCH_USERNAME else None,
            use_ssl=False,
            verify_certs=False,
        )
        self._index = settings.OPENSEARCH_INDEX or OPENSEARCH_INDEX_NAME
        self._fake_search: Any = None

    def _get_fake(self) -> Any:
        if self._fake_search is None:
            from indexing.fake_search import FakeSearchBackend
            self._fake_search = FakeSearchBackend()
        return self._fake_search

    async def ensure_index(self) -> None:
        if settings.USE_FAKE_OPENSEARCH:
            await self._get_fake().ensure_index()
            return
        try:
            exists = await self._client.indices.exists(index=self._index)
            if not exists:
                await self._client.indices.create(index=self._index, body=INDEX_MAPPING)
        except Exception:
            log.warning("opensearch_ensure_index_failed", index=self._index)

    async def upsert(self, chunk_id: str, body: dict) -> None:
        if settings.USE_FAKE_OPENSEARCH:
            from indexing.fake_search import SearchChunk
            chunk = SearchChunk(
                chunk_id=chunk_id,
                entity_urn=body.get("entity_urn", ""),
                entity_type=body.get("entity_type", ""),
                chunk_type=body.get("chunk_type", ""),
                text=body.get("content", ""),
                domain=body.get("domain", ""),
                platform=body.get("platform", ""),
                source_url=body.get("datahub_url", ""),
                embedding=body.get("embedding"),
            )
            await self._get_fake().index_chunk(chunk)
            return
        await self._client.index(index=self._index, id=chunk_id, body=body, refresh="wait_for")

    async def bulk_upsert(self, docs: list[dict]) -> int:
        if settings.USE_FAKE_OPENSEARCH:
            for doc in docs:
                await self.upsert(doc.pop("_id", None) or doc.get("chunk_id"), doc)
            return len(docs)
        actions = [
            {"_index": self._index, "_id": doc.pop("_id", None) or doc.get("chunk_id"), "_source": doc}
            for doc in docs
        ]
        success, _ = await async_bulk(self._client, actions, refresh=True)
        return success

    async def keyword_search(self, query: str, size: int = 10, **filters: Any) -> list[VectorSearchResult]:
        if settings.USE_FAKE_OPENSEARCH:
            results = await self._get_fake().search(query, top_k=size, **filters)
            return [
                VectorSearchResult(
                    id=r["chunk_id"],
                    score=r["score"],
                    payload=r,
                ) for r in results
            ]
        must: list[dict] = [{"match": {"content": query}}]
        if filters:
            for key, value in filters.items():
                if value:
                    must.append({"term": {key: value}})
        body = {
            "query": {"bool": {"must": must}},
            "size": size,
        }
        return await self._search(body)

    async def vector_search(self, vector: list[float], size: int = 10, **filters: Any) -> list[VectorSearchResult]:
        if settings.USE_FAKE_OPENSEARCH:
            return await self.keyword_search("", size=size, **filters)
        must: list[dict] = [{"knn": {"embedding": {"vector": vector, "k": size}}}]
        if filters:
            for key, value in filters.items():
                if value:
                    must.append({"term": {key: value}})
        body = {
            "query": {"bool": {"must": must}},
            "size": size,
        }
        try:
            return await self._search(body)
        except Exception:
            log.warning("knn_fallback_to_keyword", index=self._index)
            return await self.keyword_search("", size=size, **filters)

    async def hybrid_search(self, query: str, vector: list[float], size: int = 10, **filters: Any) -> list[VectorSearchResult]:
        keyword_results = await self.keyword_search(query, size=size * 2, **filters)
        vector_results = await self.vector_search(vector, size=size * 2, **filters)
        merged: dict[str, VectorSearchResult] = {}
        for r in keyword_results:
            r.score *= 0.5
            merged[r.id] = r
        for r in vector_results:
            if r.id in merged:
                merged[r.id].score += r.score * 0.5
            else:
                r.score *= 0.5
                merged[r.id] = r
        sorted_results = sorted(merged.values(), key=lambda x: x.score, reverse=True)
        return sorted_results[:size]

    async def delete_by_entity_urn(self, entity_urn: str) -> None:
        if settings.USE_FAKE_OPENSEARCH:
            await self._get_fake().delete_by_entity(entity_urn)
            return
        try:
            body = {"query": {"term": {"entity_urn": entity_urn}}}
            await self._client.delete_by_query(index=self._index, body=body)
        except Exception:
            log.warning("opensearch_delete_failed", entity_urn=entity_urn)

    async def close(self) -> None:
        if settings.USE_FAKE_OPENSEARCH:
            return
        try:
            await self._client.close()
        except Exception:
            log.warning("opensearch_close_failed")

    async def healthcheck(self) -> bool:
        if settings.USE_FAKE_OPENSEARCH:
            return True
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def _search(self, body: dict) -> list[VectorSearchResult]:
        try:
            response = await self._client.search(index=self._index, body=body)
            results: list[VectorSearchResult] = []
            for hit in response["hits"]["hits"]:
                results.append(VectorSearchResult(
                    id=hit["_id"],
                    score=hit["_score"],
                    payload=hit["_source"],
                ))
            return results
        except Exception:
            log.warning("opensearch_search_failed", index=self._index)
            return []
