from collections.abc import Sequence
from typing import Any

import structlog

from ingestion.errors import DataHubConnectionError
from ingestion.graphql.client import GraphQLClient
from ingestion.graphql.queries import (
    GET_DASHBOARD_QUERY,
    GET_DATASET_LINEAGE_QUERY,
    GET_DATASET_QUERY,
    GET_DOCUMENT_QUERY,
    GET_GLOSSARY_TERM_QUERY,
    LIST_GLOSSARY_TERMS_QUERY,
    SCROLL_ACROSS_ENTITIES_QUERY,
)
from ingestion.mappers.dashboard import DashboardMapper
from ingestion.mappers.dataset import DatasetMapper
from ingestion.mappers.document import DocumentMapper
from ingestion.mappers.glossary import GlossaryNodeMapper, GlossaryTermMapper
from ingestion.models import CanonicalEntity, EntityPage
from ingestion.source import DataHubSource
from ingestion.url_builder import DataHubUrlBuilder

log = structlog.get_logger()


class GraphQLDataHubSource(DataHubSource):
    def __init__(
        self,
        gms_url: str | None = None,
        token: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._client = GraphQLClient(
            gms_url=gms_url,
            token=token,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self._url_builder = DataHubUrlBuilder()
        self._dataset_mapper = DatasetMapper()
        self._dashboard_mapper = DashboardMapper()
        self._glossary_term_mapper = GlossaryTermMapper()
        self._glossary_node_mapper = GlossaryNodeMapper()
        self._document_mapper = DocumentMapper()

    async def list_entities(
        self,
        entity_type: str,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> EntityPage:
        type_map = {
            "dataset": "DATASET",
            "dashboard": "DASHBOARD",
            "glossary_term": "GLOSSARY_TERM",
            "chart": "CHART",
            "dataFlow": "DATA_FLOW",
            "dataJob": "DATA_JOB",
            "container": "CONTAINER",
            "tag": "TAG",
            "mlModel": "MLMODEL",
            "mlFeatureTable": "ML_FEATURE_TABLE",
        }
        graphql_type = type_map.get(entity_type, entity_type.upper())
        try:
            data = await self._client.execute(
                SCROLL_ACROSS_ENTITIES_QUERY,
                {
                    "input": {
                        "types": [graphql_type],
                        "query": "*",
                        "count": page_size,
                        "scrollId": cursor,
                        "orFilters": [],
                    }
                },
            )
        except DataHubConnectionError:
            log.exception("graphql_list_entities_failed", entity_type=entity_type)
            return EntityPage(items=[])

        scroll = data.get("scrollAcrossEntities") or {}
        items = []
        for hit in (scroll.get("searchResults") or []):
            entity = hit.get("entity") or {}
            items.append(entity)

        next_cursor = scroll.get("nextScrollId")
        has_more = bool(next_cursor)
        total = scroll.get("total")
        return EntityPage(items=items, next_cursor=next_cursor, has_more=has_more, total=total)

    async def search_entities(self, entity_type: str, query: str = "*") -> Sequence[CanonicalEntity]:
        try:
            data = await self._client.execute(
                SCROLL_ACROSS_ENTITIES_QUERY,
                {
                    "input": {
                        "types": [entity_type.upper()],
                        "query": query,
                        "count": 50,
                        "orFilters": [],
                    }
                },
            )
        except DataHubConnectionError:
            log.exception("graphql_search_failed", entity_type=entity_type)
            return []

        scroll = data.get("scrollAcrossEntities") or {}
        entities: list[CanonicalEntity] = []
        for hit in (scroll.get("searchResults") or []):
            entity = hit.get("entity") or {}
            canonical = self._search_hit_to_canonical(entity)
            if canonical:
                entities.append(canonical)
        return entities

    _URN_TYPE_ROUTING: list[tuple[str, str]] = [
        (":dataset:", "dataset"),
        (":dataset(", "dataset"),
        (":glossaryTerm:", "glossary_term"),
        (":dashboard:", "dashboard"),
        (":dashboard(", "dashboard"),
        (":chart:", "chart"),
        (":chart(", "chart"),
        (":dataFlow:", "dataFlow"),
        (":dataFlow(", "dataFlow"),
        (":dataJob:", "dataJob"),
        (":dataJob(", "dataJob"),
        (":container:", "container"),
        (":container(", "container"),
        (":tag:", "tag"),
        (":mlModel:", "mlModel"),
        (":mlModel(", "mlModel"),
    ]

    @staticmethod
    def _urn_to_type(urn: str) -> str:
        for pattern, etype in GraphQLDataHubSource._URN_TYPE_ROUTING:
            if pattern in urn:
                return etype
        return "dataset"

    async def get_entity(self, urn: str) -> CanonicalEntity | None:
        etype = self._urn_to_type(urn)
        if etype == "dataset":
            return await self._get_dataset(urn)
        if etype == "glossary_term":
            return await self._get_glossary_term(urn)
        if etype == "dashboard":
            return await self._get_dashboard(urn)
        if etype == "document":
            return await self._get_document(urn)
        return await self._search_fallback_entity(urn, etype)

    async def _search_fallback_entity(self, urn: str, etype: str) -> CanonicalEntity | None:
        try:
            data = await self._client.execute(
                SCROLL_ACROSS_ENTITIES_QUERY,
                {"input": {"types": [etype.upper()], "query": urn, "count": 1, "orFilters": []}},
            )
            scroll = data.get("scrollAcrossEntities") or {}
            for hit in (scroll.get("searchResults") or []):
                entity = hit.get("entity") or {}
                if entity.get("urn") == urn:
                    return self._search_hit_to_canonical(entity)
        except DataHubConnectionError:
            pass
        return None

    @staticmethod
    def _get_entity_name(entity: dict) -> str:
        name = entity.get("name") or ""
        if not name:
            props = entity.get("properties") or {}
            if isinstance(props, dict):
                name = props.get("name") or ""
        if not name:
            info = entity.get("info") or {}
            if isinstance(info, dict):
                name = info.get("title") or ""
        return name

    @staticmethod
    def _get_entity_description(entity: dict) -> str | None:
        desc = entity.get("description")
        if not desc:
            props = entity.get("properties") or {}
            if isinstance(props, dict):
                desc = props.get("description") or desc
        if not desc:
            info = entity.get("info") or {}
            if isinstance(info, dict):
                contents_obj = info.get("contents") or {}
                if isinstance(contents_obj, dict):
                    desc = contents_obj.get("text") or desc
                else:
                    desc = contents_obj or desc
        if not desc:
            doc = entity.get("documentation")
            if doc:
                desc = doc
        return desc

    @staticmethod
    def _extract_schema_fields(entity: dict) -> list[dict]:
        fields = []
        schema = entity.get("schemaMetadata") or {}
        for f in (schema.get("fields") or []):
            fields.append({
                "field_path": f.get("fieldPath", ""),
                "name": f.get("fieldPath", ""),
                "type": f.get("nativeDataType") or f.get("type", ""),
                "native_data_type": f.get("nativeDataType", ""),
                "description": f.get("description"),
                "nullable": f.get("nullable", True),
                "is_primary_key": f.get("isPartOfKey", False),
            })
        return fields

    @staticmethod
    def _extract_lineage_urns(entity: dict) -> tuple[list[str], list[str]]:
        upstreams: list[str] = []
        downstreams: list[str] = []

        for direction, alias in [("upstream", "upstreamLineage"), ("downstream", "downstreamLineage")]:
            side = entity.get(alias) or entity.get("lineage", {}).get(direction) or {}
            for rel in (side.get("relationships") or []):
                ent = rel.get("entity") or {}
                if ent.get("urn"):
                    if direction == "upstream":
                        upstreams.append(ent["urn"])
                    else:
                        downstreams.append(ent["urn"])
        return upstreams, downstreams

    def _search_hit_to_canonical(self, entity: dict) -> CanonicalEntity | None:
        urn = entity.get("urn", "")
        if not urn:
            return None
        raw = entity.get("raw") or entity

        owners = []
        ownership = entity.get("ownership") or {}
        for o in ((ownership.get("owners") or []) if isinstance(ownership, dict) else []):
            owner_data = o.get("owner") or {}
            owners.append({
                "name": (owner_data.get("properties") or {}).get("displayName")
                         or (owner_data.get("info") or {}).get("displayName")
                         or owner_data.get("username")
                         or owner_data.get("name", ""),
                "type": "BUSINESS_OWNER",
            })

        domain = None
        domain_obj = entity.get("domain") or {}
        if isinstance(domain_obj, dict):
            d_inner = domain_obj.get("domain") or {}
            if isinstance(d_inner, dict):
                domain = (d_inner.get("name")
                          or (d_inner.get("properties") or {}).get("name")
                          or domain)
        if not domain:
            properties = entity.get("properties")
            if isinstance(properties, dict):
                custom = properties.get("customProperties") or {}
                if isinstance(custom, list):
                    for entry in custom:
                        if isinstance(entry, dict) and entry.get("key") == "domain":
                            domain = entry.get("value") or domain
                elif isinstance(custom, dict):
                    domain = custom.get("domain") or domain

        glossary_terms = []
        gt_obj = entity.get("glossaryTerms") or {}
        terms_list = ((gt_obj.get("terms") or []) if isinstance(gt_obj, dict) else [])
        for t in terms_list:
            term = t.get("term") or {}
            if term.get("urn"):
                glossary_terms.append(term["urn"])

        tags = []
        tags_obj = entity.get("tags") or {}
        tag_list = ((tags_obj.get("tags") or []) if isinstance(tags_obj, dict) else [])
        for t in tag_list:
            tag = t.get("tag") or {}
            if tag.get("name"):
                tags.append(tag["name"])

        environment = None
        properties = entity.get("properties")
        if isinstance(properties, dict):
            custom = properties.get("customProperties") or {}
            if isinstance(custom, list):
                for entry in custom:
                    if isinstance(entry, dict) and entry.get("key") == "environment":
                        environment = entry.get("value") or environment
            elif isinstance(custom, dict):
                environment = custom.get("environment") or environment

        schema_fields = self._extract_schema_fields(entity)
        upstreams, downstreams = self._extract_lineage_urns(entity)

        name = self._get_entity_name(entity)
        result = CanonicalEntity(
            urn=urn,
            entity_type=self._urn_to_type(urn),
            name=name,
            display_name=entity.get("displayName") or name,
            description=self._get_entity_description(entity),
            platform=((entity.get("platform") or {}) or {}).get("name") if isinstance(entity.get("platform"), dict) else None,
            owners=owners,
            domain=domain,
            environment=environment,
            glossary_terms=glossary_terms,
            tags=tags,
            schema_fields=schema_fields,
            upstreams=upstreams,
            downstreams=downstreams,
            raw_payload=raw,
        )
        return result

    async def _get_dataset(self, urn: str) -> CanonicalEntity | None:
        try:
            data = await self._client.execute(GET_DATASET_QUERY, {"urn": urn})
        except DataHubConnectionError:
            log.exception("graphql_get_dataset_failed", urn=urn)
            return None

        ds = data.get("dataset") or data.get("datasetV2") or {}
        if not ds:
            return None

        try:
            return self._dataset_mapper.to_canonical(ds, self._url_builder)
        except Exception:
            log.exception("dataset_mapping_failed", urn=urn)
            return None

    async def _get_glossary_term(self, urn: str) -> CanonicalEntity | None:
        try:
            data = await self._client.execute(GET_GLOSSARY_TERM_QUERY, {"urn": urn})
        except DataHubConnectionError:
            log.exception("graphql_get_glossary_term_failed", urn=urn)
            return None

        term = data.get("glossaryTerm") or {}
        if not term:
            return None

        try:
            return self._glossary_term_mapper.to_canonical(term, self._url_builder)
        except Exception:
            log.exception("glossary_mapping_failed", urn=urn)
            return None

    async def _get_dashboard(self, urn: str) -> CanonicalEntity | None:
        try:
            data = await self._client.execute(GET_DASHBOARD_QUERY, {"urn": urn})
        except DataHubConnectionError:
            log.exception("graphql_get_dashboard_failed", urn=urn)
            return None

        dashboard = data.get("dashboard") or {}
        if not dashboard:
            return None

        try:
            return self._dashboard_mapper.to_canonical(dashboard, self._url_builder)
        except Exception:
            log.exception("dashboard_mapping_failed", urn=urn)
            return None

    async def _get_document(self, urn: str) -> CanonicalEntity | None:
        try:
            data = await self._client.execute(GET_DOCUMENT_QUERY, {"urn": urn})
        except DataHubConnectionError:
            log.exception("graphql_get_document_failed", urn=urn)
            return None

        doc = data.get("document") or {}
        if not doc:
            return None

        try:
            return self._document_mapper.to_canonical(doc, self._url_builder)
        except Exception:
            log.exception("document_mapping_failed", urn=urn)
            return None

    async def get_entity_by_urn(self, urn: str) -> CanonicalEntity | None:
        return await self.get_entity(urn)

    async def list_datasets(self) -> Sequence[CanonicalEntity]:
        return await self._list_type("dataset")

    async def list_dashboards(self) -> Sequence[CanonicalEntity]:
        return await self._list_type("dashboard")

    async def list_glossary_terms(self) -> Sequence[CanonicalEntity]:
        return await self._list_type("glossary_term")

    async def list_documents(self) -> Sequence[CanonicalEntity]:
        entities: list[CanonicalEntity] = []
        page = await self.list_entities("document", page_size=50)
        for raw in page.items:
            canonical = self._search_hit_to_canonical(raw)
            if canonical:
                entities.append(canonical)
        return entities

    async def get_lineage(self, urn: str, direction: str = "both", depth: int = 1) -> dict[str, Any]:
        try:
            data = await self._client.execute(
                GET_DATASET_LINEAGE_QUERY,
                {"urn": urn, "direction": direction.upper(), "depth": depth, "count": 100},
            )
        except DataHubConnectionError:
            log.exception("graphql_get_lineage_failed", urn=urn)
            return {}

        return data.get("lineage") or data.get("dataset", {}).get("lineage") or {}

    async def list_entity_type(self, entity_type: str) -> Sequence[CanonicalEntity]:
        if entity_type == "dataset":
            return await self.list_datasets()
        if entity_type == "dashboard":
            return await self.list_dashboards()
        if entity_type == "glossary_term":
            return await self.list_glossary_terms()
        if entity_type == "document":
            return await self.list_documents()
        return await self.search_entities(entity_type, query="*")

    async def healthcheck(self) -> bool:
        try:
            await self._client.execute("{ __typename }")
            return True
        except DataHubConnectionError:
            return False

    async def _list_type(
        self,
        entity_type: str,
    ) -> Sequence[CanonicalEntity]:
        entities: list[CanonicalEntity] = []
        cursor: str | None = None
        while True:
            page = await self.list_entities(entity_type, cursor=cursor)
            for raw in page.items:
                canonical = self._search_hit_to_canonical(raw)
                if canonical:
                    entities.append(canonical)
            if not page.has_more:
                break
            cursor = page.next_cursor
        return entities

    async def close(self) -> None:
        await self._client.close()
