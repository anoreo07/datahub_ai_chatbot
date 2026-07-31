"""In-memory fake search backend for mock mode. No OpenSearch required."""

import re


class SearchChunk:
    def __init__(
        self,
        chunk_id: str,
        entity_urn: str,
        entity_type: str,
        chunk_type: str,
        text: str,
        domain: str = "",
        domain_urn: str = "",
        platform: str = "",
        environment: str = "",
        field_path: str = "",
        source_url: str = "",
        content_hash: str = "",
        embedding: list[float] | None = None,
        metadata: dict | None = None,
    ):
        self.chunk_id = chunk_id
        self.entity_urn = entity_urn
        self.entity_type = entity_type
        self.chunk_type = chunk_type
        self.text = text
        self.domain = domain
        self.domain_urn = domain_urn
        self.platform = platform
        self.environment = environment
        self.field_path = field_path
        self.source_url = source_url
        self.content_hash = content_hash
        self.embedding = embedding
        self.metadata = metadata or {}


class FakeSearchBackend:
    def __init__(self) -> None:
        self._chunks: dict[str, SearchChunk] = {}
        self._by_entity: dict[str, list[str]] = {}

    async def ensure_index(self) -> None:
        pass  # no-op in memory

    async def index_chunk(self, chunk: SearchChunk) -> None:
        self._chunks[chunk.chunk_id] = chunk
        self._by_entity.setdefault(chunk.entity_urn, []).append(chunk.chunk_id)

    async def bulk_index(self, chunks: list[SearchChunk]) -> None:
        for chunk in chunks:
            await self.index_chunk(chunk)

    async def delete_chunk(self, chunk_id: str) -> None:
        chunk = self._chunks.pop(chunk_id, None)
        if chunk and chunk.entity_urn in self._by_entity:
            try:
                self._by_entity[chunk.entity_urn].remove(chunk_id)
            except ValueError:
                pass

    async def delete_by_entity(self, entity_urn: str) -> None:
        for cid in self._by_entity.pop(entity_urn, []):
            self._chunks.pop(cid, None)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        entity_type: str | None = None,
        domain: str | None = None,
        environment: str | None = None,
    ) -> list[dict]:
        results = []
        normalized_query = self._normalize(query)
        for chunk in self._chunks.values():
            if entity_type and chunk.entity_type != entity_type:
                continue
            if domain and chunk.domain != domain:
                continue
            if environment and chunk.environment != environment:
                continue
            score = self._compute_score(chunk.text, normalized_query)
            if score > 0:
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "entity_urn": chunk.entity_urn,
                    "entity_type": chunk.entity_type,
                    "chunk_type": chunk.chunk_type,
                    "text": chunk.text,
                    "domain": chunk.domain,
                    "domain_urn": chunk.domain_urn,
                    "platform": chunk.platform,
                    "environment": chunk.environment,
                    "field_path": chunk.field_path,
                    "source_url": chunk.source_url,
                    "score": score,
                })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    async def get_by_entity(self, entity_urn: str) -> list[dict]:
        return [
            {
                "chunk_id": c.chunk_id,
                "entity_urn": c.entity_urn,
                "entity_type": c.entity_type,
                "chunk_type": c.chunk_type,
                "text": c.text,
            }
            for c in self._chunks.values()
            if c.entity_urn == entity_urn
        ]

    async def get_by_chunk_type(self, entity_urn: str, chunk_type: str) -> list[dict]:
        return [
            r for r in await self.get_by_entity(entity_urn) if r["chunk_type"] == chunk_type
        ]

    async def count(self) -> int:
        return len(self._chunks)

    async def healthcheck(self) -> bool:
        return True

    @staticmethod
    def _normalize(text: str) -> str:
        result = text.lower().strip()
        result = result.replace("_", " ").replace("-", " ").replace(".", " ")
        result = re.sub(r"\s+", " ", result)
        return result.strip()

    def _compute_score(self, text: str, normalized_query: str) -> float:
        normalized_text = self._normalize(text)
        if normalized_query == normalized_text:
            return 1.0
        if normalized_query in normalized_text:
            return 0.8
        q_tokens = set(normalized_query.split())
        t_tokens = set(normalized_text.split())
        if not q_tokens:
            return 0.0
        overlap = len(q_tokens & t_tokens)
        if overlap == len(q_tokens):
            return 0.7
        return overlap / len(q_tokens) * 0.5
