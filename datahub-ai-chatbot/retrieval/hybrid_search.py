from collections.abc import Sequence
from typing import Any

import re

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


def _entity_payload_to_text(entity_type: str, payload: dict) -> str:
    parts = []
    name = payload.get("display_name") or payload.get("name", "")
    if name:
        parts.append(f"Name: {name}")
    desc = payload.get("description", "")
    if desc:
        parts.append(f"Description: {desc}")
    domain = payload.get("domain", "")
    if domain:
        parts.append(f"Domain: {domain}")
    platform = payload.get("platform", "")
    if platform:
        parts.append(f"Platform: {platform}")
    owners = payload.get("owners", [])
    if owners:
        owner_names = [o.get("name", "") for o in owners]
        parts.append(f"Owners: {', '.join(owner_names)}")
    fields = payload.get("schema_fields", [])
    if fields:
        field_lines = []
        for f in fields:
            fdesc = f.get("description", "")
            base = f"  - {f.get('name', '')} ({f.get('type', '')})"
            field_lines.append(f"{base}: {fdesc}" if fdesc else base)
        parts.append("Schema fields:\n" + "\n".join(field_lines))
    terms = payload.get("glossary_terms", [])
    if terms:
        parts.append(f"Glossary terms: {', '.join(terms)}")
    upstreams = payload.get("upstreams", [])
    if upstreams:
        parts.append(f"Upstream: {', '.join(upstreams)}")
    downstreams = payload.get("downstreams", [])
    if downstreams:
        parts.append(f"Downstream: {', '.join(downstreams)}")
    return " | ".join(parts)

log = structlog.get_logger()

# Question words that mark a query as a *discovery* sentence rather than a
# concrete entity-name lookup. When a question carries these words, fuzzy
# entity resolution produces spurious matches ("dataset staging vật tư ..."
# -> a random report), so the resolver candidates are only trusted when they
# are strong or the query explicitly quotes an entity name.
_DISCOVERY_MARKERS = (
    "nào", "nao", "gì", "gi ", "ở đâu", "o dau", "nằm ở đâu", "nam o dau",
    "không?", "khong?", "là gì", "la gi", "có báo cáo", "co bao cao",
    "có dashboard", "co dashboard", "có report", "co report", "có dataset",
    "co dataset", "tìm", "tim ", "liệt kê", "liet ke", "có bao nhiêu",
    "co bao nhieu", "chứa", "chua", "which", "what ", "how ", "where",
)


def _names_entity(query: str) -> bool:
    """True when ``query`` contains an explicit entity-name signal.

    A signal is a quoted name (``"..."`` or ``'...'``), a snake_case or dotted
    catalog identifier, or the phrasing "tên chính xác"/"có tên"/"tên là".
    Discovery sentences without any such signal must NOT be resolved to a
    single entity by fuzzy matching.
    """
    if re.search(r"""["'“”‘’][^"'“”‘’]{2,80}["'“”‘’]""", query):
        return True
    if re.search(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+|[a-z0-9]{2,}_[a-z0-9_]+", query):
        return True
    q = query.lower()
    if re.search(r"tên chính xác|ten chinh xac|có tên|co ten|tên là|ten la|named", q):
        return True
    return False


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

        # A resolver that settled on ONE entity (not ambiguous) is authoritative
        # even when it did not cross the exact-match bar: the question named a
        # concrete entity and the resolver picked it. Returning just that entity
        # prevents the downstream ambiguity gate from asking a clarification
        # against fuzzy runner-ups the user never asked about. Discovery
        # sentences without an entity-name signal (and weak fuzzy scores) must
        # not trigger this — the "resolution" there is keyword spillover.
        if (resolution.resolved and not resolution.ambiguous
                and (_names_entity(query)
                     or resolution.resolved.score >= settings.ENTITY_RESOLVER_TRUST_THRESHOLD)):
            log.info("hybrid_path", trace_id=trace_id, query=query,
                     path="resolved_single",
                     resolved=resolution.resolved.name, count=1)
            return [await self._entity_to_result(resolution.resolved.urn)]

        if resolution.candidates:
            # Discovery sentences ("dataset staging vật tư ... nào?", "có báo
            # cáo nào về ...") have no concrete entity name; fuzzy candidates
            # are just keyword spillover and routinely point at unrelated
            # reports. Only surface them for explicit name queries or when the
            # top candidate is strong enough to be meaningful.
            if _names_entity(query) or resolution.candidates[0].score >= settings.ENTITY_RESOLVER_TRUST_THRESHOLD:
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

        # R2 — domain-scoped semantic discovery. Discovery sentences in natural
        # language ("dataset staging vật tư (material) trong DMS ở đâu?", "có
        # báo cáo nào về WIP giữa MES và SAP?") name a business concept that
        # maps onto the English/technical tokens of the target entity name
        # (dms.stg.stg_material, "Báo cáo check WIP MES_SAP"). The full-sentence
        # vector search routinely ranks unrelated entities above those targets
        # (Vietnamese query words do not literally appear in the entity content).
        # Merge the deterministic token-discovery candidates into the results so
        # the target entity is surfaced alongside the semantic hits.
        from retrieval.discovery import TokenDiscovery, expand_query_tokens, score_entity
        discovery = TokenDiscovery(self._entity_repo)
        disc_entities = await discovery.discover(query, top_k=top_k, trace_id=trace_id)
        if disc_entities:
            disc_urns = {e.urn for e in disc_entities}
            existing = {r.urn for r in results}
            merged = list(results)
            tokens = expand_query_tokens(query)
            for e in disc_entities:
                if e.urn in existing:
                    continue
                payload = dict(e.payload or {})
                payload.setdefault("content", _entity_payload_to_text(e.entity_type, payload))
                # Score discovery hits by token-match strength so a candidate that
                # matches EVERY expanded query token ("Báo cáo check WIP MES_SAP"
                # for "WIP giữa MES và SAP") can compete with vector hits, while
                # partial matches stay below them. Flat 0.9 made a full-token-match
                # dashboard lose to weak vector datasets whose raw scores clamp to
                # base 1.0 in the reranker (type-aware retrieval regression).
                hits = score_entity(tokens, e)
                max_hits = max(1.0, len(tokens) * 2.0)
                score = round(min(1.0, 0.9 + 0.1 * hits / max_hits), 4)
                merged.append(SearchResult(
                    urn=e.urn, entity_type=e.entity_type,
                    name=e.display_name or e.name, score=score,
                    datahub_url=e.datahub_url, payload=payload,
                ))
                existing.add(e.urn)
            results = merged
            log.info("hybrid_discovery_merge", trace_id=trace_id, query=query[:100],
                     discovery_urns=len(disc_urns), merged=len(results))

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
        payload = dict(entity.payload or {})
        payload.setdefault("content", _entity_payload_to_text(entity.entity_type, payload))
        return SearchResult(
            urn=entity.urn,
            entity_type=entity.entity_type,
            name=entity.display_name or entity.name,
            score=1.0,
            datahub_url=entity.datahub_url,
            payload=payload,
        )

    async def _urns_to_results(self, urns: list[str]) -> list[SearchResult]:
        entities = await self._entity_repo.list_by_urns(urns)
        return [
            SearchResult(
                urn=e.urn, entity_type=e.entity_type, name=e.display_name or e.name,
                score=0.9, datahub_url=e.datahub_url,
                payload={
                    **dict(e.payload or {}),
                    "content": _entity_payload_to_text(
                        e.entity_type, e.payload or {}),
                },
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
