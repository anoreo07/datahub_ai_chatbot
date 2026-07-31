"""Document ingestion service."""
import datetime
import hashlib

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import EntityChunk
from database.repositories.chunk_repository import ChunkRepository
from database.repositories.entity_repository import EntityRepository
from indexing.chunker import chunk_text
from indexing.embedder import Embedder, create_embedder
from indexing.vector_store import OpenSearchVectorStore
from infrastructure.storage import LocalStorage
from ingestion.document_parsers import get_parser
from ingestion.document_parsers.ssrf_guard import SSRFGuard
from ingestion.models import CanonicalEntity

log = structlog.get_logger()


class DocumentIngestionError(Exception):
    pass


class DocumentIngestionResult:
    def __init__(
        self,
        success: bool = False,
        entity_urn: str = "",
        chunks_count: int = 0,
        error: str = "",
        source_url: str = "",
        title: str = "",
    ) -> None:
        self.success = success
        self.entity_urn = entity_urn
        self.chunks_count = chunks_count
        self.error = error
        self.source_url = source_url
        self.title = title


class DocumentIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)
        self._chunk_repo = ChunkRepository(session)
        self._vector_store = OpenSearchVectorStore()
        self._embedder: Embedder = create_embedder()
        self._storage = LocalStorage()
        self._ssrf = SSRFGuard()
        self._http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def ingest_from_url(self, url: str, title: str = "") -> DocumentIngestionResult:
        if not self._ssrf.validate(url):
            return DocumentIngestionResult(
                success=False,
                source_url=url,
                error=f"URL rejected by SSRF guard: {url[:100]}",
                title=title,
            )

        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            content = response.content
            filename = url.split("/")[-1] or "document.html"
        except Exception as e:
            log.warning("document_download_failed", url=url[:100], error=str(e))
            return DocumentIngestionResult(
                success=False,
                source_url=url,
                error=f"Download failed: {str(e)[:200]}",
                title=title,
            )

        return await self._ingest_bytes(content, filename, url, title)

    async def ingest_from_file(self, file_content: bytes, filename: str, title: str = "") -> DocumentIngestionResult:
        return await self._ingest_bytes(file_content, filename, "", title)

    async def _ingest_bytes(self, content: bytes, filename: str, source_url: str, title: str) -> DocumentIngestionResult:
        parser = get_parser(filename, use_mock=settings.APP_ENV == "development")
        if not parser:
            return DocumentIngestionResult(
                success=False,
                source_url=source_url,
                error=f"No parser available for: {filename}",
                title=title,
            )

        text = await parser.parse(content, filename)
        if not text.strip():
            return DocumentIngestionResult(
                success=False,
                source_url=source_url,
                error=f"Empty content extracted from: {filename}",
                title=title,
            )

        entity_urn = f"urn:li:document:{hashlib.sha256(content).hexdigest()[:16]}"
        doc_title = title or filename.rsplit(".", 1)[0]

        canonical = CanonicalEntity(
            urn=entity_urn,
            entity_type="document",
            name=doc_title,
            display_name=doc_title,
            description=f"Imported document: {filename}",
            source_url=source_url or None,
            raw_properties={"source": "document_ingestion", "filename": filename, "char_count": len(text)},
            raw_payload={"_doc_content": [{"heading": "Full Content", "content": text}]},
            deleted=False,
        )

        sub_texts = chunk_text(text)
        texts = sub_texts
        embeddings = await self._embedder.embed(texts)

        pg_chunks: list[EntityChunk] = []
        os_docs: list[dict] = []
        for i, (sub_text, emb) in enumerate(zip(sub_texts, embeddings)):
            content_hash = hashlib.sha256(sub_text.encode()).hexdigest()[:16]
            chunk_id = f"{entity_urn}_document_chunk_{i}"

            pg_chunks.append(EntityChunk(
                entity_urn=entity_urn,
                chunk_type="document_chunk",
                chunk_index=i,
                content=sub_text,
                chunk_metadata={
                    "source_url": source_url,
                    "filename": filename,
                    "source_title": doc_title,
                    "page": None,
                    "section": None,
                },
                content_hash=content_hash,
                embedding_model=self._embedder.model_name,
                indexed_at=datetime.datetime.now(datetime.UTC),
            ))

            os_docs.append({
                "_id": chunk_id,
                "chunk_id": chunk_id,
                "entity_urn": entity_urn,
                "entity_type": "document",
                "entity_name": doc_title,
                "chunk_type": "document_chunk",
                "content": sub_text,
                "embedding": emb,
                "owner_names": "",
                "term_urns": [],
                "domain": "",
                "platform": "",
                "environment": "",
                "datahub_url": source_url,
                "source_title": doc_title,
                "page": None,
                "section": None,
                "content_hash": content_hash,
                "updated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            })

        try:
            from database.models import Entity as DBEntity
            db_entity = DBEntity(
                urn=canonical.urn,
                entity_type=canonical.entity_type,
                name=canonical.name,
                display_name=canonical.display_name,
                description=canonical.description,
                platform=canonical.platform,
                environment=canonical.environment,
                domain=canonical.domain,
                datahub_url=canonical.source_url,
                payload=canonical.model_dump(mode="json", exclude={"raw_payload"}),
                content_hash=hashlib.sha256(text.encode()).hexdigest()[:16],
            )
            await self._entity_repo.upsert(db_entity)
            if os_docs:
                await self._vector_store.ensure_index()
                await self._vector_store.bulk_upsert(os_docs)
            await self._chunk_repo.replace_for_entity(entity_urn, pg_chunks)
            log.info("document_ingested", urn=entity_urn, chunks=len(pg_chunks), filename=filename)
            return DocumentIngestionResult(
                success=True,
                entity_urn=entity_urn,
                chunks_count=len(pg_chunks),
                source_url=source_url,
                title=doc_title,
            )
        except Exception as e:
            log.exception("document_ingestion_failed", urn=entity_urn, filename=filename)
            return DocumentIngestionResult(
                success=False,
                source_url=source_url,
                error=f"Ingestion failed: {str(e)[:300]}",
                title=doc_title,
            )

    async def close(self) -> None:
        await self._http_client.aclose()
