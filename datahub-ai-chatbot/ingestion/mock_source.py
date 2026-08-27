import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from config.settings import settings
from ingestion.models import CanonicalEntity, Domain, EntityPage, Owner, SchemaField
from ingestion.source import DataHubSource

_NON_ASCII = re.compile(r"[^a-zA-Z0-9\s]")


class MockDataHubSource(DataHubSource):
    def __init__(self, fixtures_dir: str | None = None) -> None:
        dir_path = fixtures_dir or settings.MOCK_DATAHUB_FIXTURES_PATH
        fixtures_path = Path(dir_path)
        self._entities: dict[str, CanonicalEntity] = {}
        self._by_type: dict[str, list[CanonicalEntity]] = {}
        self._by_domain: dict[str, list[CanonicalEntity]] = {}
        self._by_platform: dict[str, list[CanonicalEntity]] = {}
        self._by_env: dict[str, list[CanonicalEntity]] = {}
        self._domains: dict[str, Domain] = {}
        self._lineage: list[dict] = []
        self._doc_content: dict[str, list[dict]] = {}
        self._by_normalized_name: dict[str, list[CanonicalEntity]] = {}
        self._load_fixtures(fixtures_path)
        self._build_indexes()

    def _load_fixtures(self, fixtures_path: Path) -> None:
        from ingestion.loader import MockMetadataLoader
        loader = MockMetadataLoader(fixtures_path)
        self._domains = loader.load_domains_by_urn()
        for entity in loader.load_entities():
            self._entities[entity.urn] = entity
        self._lineage = loader.load_lineage_edges()

        # Populate upstreams/downstreams arrays on entity objects from lineage edges
        for edge in self._lineage:
            src = edge.get("source")
            tgt = edge.get("target")
            if src and tgt:
                if src in self._entities:
                    if tgt not in self._entities[src].downstreams:
                        self._entities[src].downstreams.append(tgt)
                if tgt in self._entities:
                    if src not in self._entities[tgt].upstreams:
                        self._entities[tgt].upstreams.append(src)
        content_path = fixtures_path / "documents_content.json"
        if content_path.exists():
            import json
            for entry in json.loads(content_path.read_text("utf-8")):
                self._doc_content[entry["urn"]] = entry.get("sections", [])
        for entity in self._entities.values():
            raw = entity.raw_payload or {}
            raw["_doc_content"] = self._doc_content.get(entity.urn, [])

    def _build_indexes(self) -> None:
        for entity in self._entities.values():
            self._by_type.setdefault(entity.entity_type, []).append(entity)
            if entity.domain:
                self._by_domain.setdefault(entity.domain, []).append(entity)
            if entity.platform:
                self._by_platform.setdefault(entity.platform, []).append(entity)
            if entity.environment:
                self._by_env.setdefault(entity.environment, []).append(entity)
            nname = self._normalize(entity.name)
            self._by_normalized_name.setdefault(nname, []).append(entity)

    @staticmethod
    def _normalize(text: str) -> str:
        result = text.lower().strip()
        result = result.replace("_", " ").replace("-", " ").replace(".", " ")
        result = re.sub(r"\s+", " ", result).strip()
        return result

    def _match(self, text: str, query: str) -> bool:
        nq = self._normalize(query)
        nt = self._normalize(text)
        if nq in nt or nt in nq:
            return True
        nq_no_accent = _NON_ASCII.sub("", nq)
        nt_no_accent = _NON_ASCII.sub("", nt)
        if nq_no_accent and nq_no_accent in nt_no_accent:
            return True
        return False

    def list_domains(self) -> list[Domain]:
        return list(self._domains.values())

    async def list_entities(
        self,
        entity_type: str,
        cursor: str | None = None,
        page_size: int = 100,
        domain: str | None = None,
        platform: str | None = None,
        environment: str | None = None,
    ) -> EntityPage:
        entities = self._by_type.get(entity_type, [])
        if domain:
            entities = [e for e in entities if e.domain == domain]
        if platform:
            entities = [e for e in entities if e.platform == platform]
        if environment:
            entities = [e for e in entities if e.environment == environment]
        start = int(cursor) if cursor and cursor.isdigit() else 0
        page = entities[start:start + page_size]
        next_start = start + page_size
        has_more = next_start < len(entities)
        items = [e.raw_payload or {"urn": e.urn, "name": e.name} for e in page]
        return EntityPage(
            items=items,
            next_cursor=str(next_start) if has_more else None,
            has_more=has_more,
            total=len(entities),
        )

    async def search_entities(
        self,
        entity_type: str,
        query: str = "*",
        domain: str | None = None,
    ) -> Sequence[CanonicalEntity]:
        entities = self._by_type.get(entity_type, [])
        if query == "*":
            if domain:
                entities = [e for e in entities if e.domain == domain]
            return entities
        results: list[CanonicalEntity] = []
        for e in entities:
            if domain and e.domain != domain:
                continue
            if self._match(e.name, query) or self._match(e.urn, query) or self._match(e.description or "", query):
                results.append(e)
        return results

    async def get_entity(self, urn: str) -> CanonicalEntity | None:
        return self._entities.get(urn)

    async def get_entity_by_urn(self, urn: str) -> CanonicalEntity | None:
        return self._entities.get(urn)

    async def list_entity_type(self, entity_type: str) -> Sequence[CanonicalEntity]:
        return self._by_type.get(entity_type, [])

    async def list_datasets(self) -> Sequence[CanonicalEntity]:
        return self._by_type.get("dataset", [])

    async def list_dashboards(self) -> Sequence[CanonicalEntity]:
        return self._by_type.get("dashboard", [])

    async def list_glossary_terms(self) -> Sequence[CanonicalEntity]:
        return self._by_type.get("glossary_term", [])

    async def list_documents(self) -> Sequence[CanonicalEntity]:
        return self._by_type.get("document", [])

    async def get_schema(self, urn: str) -> list[SchemaField]:
        entity = self._entities.get(urn)
        if entity:
            return entity.schema_fields
        return []

    async def get_owners(self, urn: str) -> list[Owner]:
        entity = self._entities.get(urn)
        if entity:
            return entity.owners
        return []

    async def get_lineage(self, urn: str, direction: str = "both", depth: int = 1) -> dict[str, Any]:
        result: dict[str, Any] = {"relationships": []}
        if direction in ("upstream", "both"):
            for edge in self._lineage:
                if edge["target"] == urn:
                    result["relationships"].append({
                        "type": "UPSTREAM",
                        "entity": {"urn": edge["source"], "type": self._infer_type(edge["source"])},
                    })
        if direction in ("downstream", "both"):
            for edge in self._lineage:
                if edge["source"] == urn:
                    result["relationships"].append({
                        "type": "DOWNSTREAM",
                        "entity": {"urn": edge["target"], "type": self._infer_type(edge["target"])},
                    })
        return result

    @staticmethod
    def _infer_type(urn: str) -> str:
        if ":dataset:" in urn or ":dataset(" in urn:
            return "dataset"
        if ":dashboard:" in urn or ":dashboard(" in urn:
            return "dashboard"
        if ":glossaryTerm:" in urn:
            return "glossaryTerm"
        if ":document:" in urn:
            return "document"
        return "unknown"

    async def get_by_domain(self, domain_name: str) -> list[CanonicalEntity]:
        return self._by_domain.get(domain_name, [])

    async def get_by_platform(self, platform: str) -> list[CanonicalEntity]:
        return self._by_platform.get(platform, [])

    async def get_by_environment(self, env: str) -> list[CanonicalEntity]:
        return self._by_env.get(env, [])

    async def resolve_by_name(self, name: str) -> list[CanonicalEntity]:
        normalized = self._normalize(name)
        exact_results = self._by_normalized_name.get(normalized, [])
        if exact_results:
            return exact_results
        results = []
        for entity in self._entities.values():
            if self._match(entity.name, name) or self._match(entity.display_name or "", name):
                results.append(entity)
        return results

    async def healthcheck(self) -> bool:
        return True

    async def close(self) -> None:
        pass

    def list_all(self) -> Sequence[CanonicalEntity]:
        return list(self._entities.values())
