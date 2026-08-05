import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import EntityChunk
from database.repositories.chunk_repository import ChunkRepository
from database.repositories.entity_repository import EntityRepository
from database.repositories.index_job_repository import IndexJobRepository
from indexing.chunker import chunk_text
from indexing.embedder import Embedder, create_embedder
from indexing.entity_document import ChunkItem, build_chunks_for_entity
from indexing.vector_store import OpenSearchVectorStore
from ingestion.models import CanonicalEntity

log = structlog.get_logger()


class IndexingPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)
        self._chunk_repo = ChunkRepository(session)
        self._index_repo = IndexJobRepository(session)
        self._vector_store = OpenSearchVectorStore()
        self._embedder: Embedder = create_embedder()

    async def process_entity(self, canonical: CanonicalEntity) -> None:
        urn = canonical.urn
        chunk_items = build_chunks_for_entity(canonical)
        full_chunks: list[ChunkItem] = []
        for item in chunk_items:
            sub_texts = chunk_text(item.content)
            for i, sub in enumerate(sub_texts):
                sub_item = item.model_copy(update={"chunk_index": item.chunk_index + i, "content": sub})
                full_chunks.append(sub_item)

        texts = [c.content for c in full_chunks]
        if not texts:
            await self._chunk_repo.replace_for_entity(urn, [])
            return
        embeddings = await self._embedder.embed(texts)

        pg_chunks: list[EntityChunk] = []
        os_docs: list[dict] = []
        for ci, emb in zip(full_chunks, embeddings):
            pg_chunks.append(EntityChunk(
                entity_urn=ci.entity_urn,
                chunk_type=ci.chunk_type,
                chunk_index=ci.chunk_index,
                content=ci.content,
                chunk_metadata=ci.metadata,
                content_hash=ci.content_hash,
                embedding_model=self._embedder.model_name,
                indexed_at=datetime.datetime.now(datetime.UTC),
            ))
            os_docs.append({
                "_id": f"{urn}_{ci.chunk_type}_{ci.chunk_index}",
                "chunk_id": f"{urn}_{ci.chunk_type}_{ci.chunk_index}",
                "entity_urn": ci.entity_urn,
                "entity_type": ci.entity_type,
                "entity_name": ci.entity_name,
                "chunk_type": ci.chunk_type,
                "content": ci.content,
                "embedding": emb,
                "owner_names": ci.metadata.get("owner_names", ""),
                "term_urns": ci.metadata.get("term_urns", []),
                "domain": ci.metadata.get("domain", ""),
                "platform": ci.metadata.get("platform", ""),
                "environment": ci.metadata.get("environment", ""),
                "datahub_url": ci.metadata.get("datahub_url", ""),
                "source_title": ci.metadata.get("source_title", ""),
                "page": ci.metadata.get("page"),
                "section": ci.metadata.get("section", ""),
                "content_hash": ci.content_hash,
                "updated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            })

        if os_docs:
            await self._vector_store.delete_by_entity_urn(urn)
            await self._vector_store.ensure_index()
            await self._vector_store.bulk_upsert(os_docs)

        await self._chunk_repo.replace_for_entity(urn, pg_chunks)

    async def process_pending_jobs(self, max_jobs: int = 20) -> int:
        jobs = await self._index_repo.get_pending(limit=max_jobs)
        processed = 0
        for job in jobs:
            try:
                await self._index_repo.mark_running(job.id)
                entity_db = await self._entity_repo.get_by_urn(job.entity_urn)
                if not entity_db:
                    await self._index_repo.mark_failed(job.id, "entity_not_found")
                    continue
                payload = entity_db.payload or {}
                canonical = CanonicalEntity(**payload)
                await self.process_entity(canonical)
                await self._index_repo.mark_completed(job.id)
                processed += 1
            except Exception as e:
                log.exception("index_job_failed", job_id=job.id, urn=job.entity_urn)
                await self._index_repo.mark_failed(job.id, str(e)[:500])
        return processed
