import datetime
import json
from pathlib import Path

import structlog

from ingestion.models import CanonicalEntity, Domain, Owner, SchemaField

log = structlog.get_logger()

_VALID_OWNER_TYPES = {"BUSINESS_OWNER", "DATA_TECHNICAL_OWNER", "SYSTEM_OWNER", "USER"}


class MockValidationError(ValueError):
    pass


class MockMetadataLoader:
    def __init__(self, fixtures_dir: str | Path) -> None:
        self._fixtures_dir = Path(fixtures_dir)

    def load_domains(self) -> list[Domain]:
        try:
            data = self._load_json("domains.json", expect_list=True, optional=True)
        except MockValidationError:
            data = []
        domains = []
        for raw in data:
            domains.append(Domain(urn=raw["urn"], name=raw["name"], description=raw.get("description", "")))
        if domains:
            self._validate_unique_urns([d.urn for d in domains], "Domain")
        return domains

    def load_entities(self) -> list[CanonicalEntity]:
        all_entities: list[CanonicalEntity] = []
        for filename, entity_type in [
            ("datasets.json", "dataset"),
            ("dashboards.json", "dashboard"),
            ("glossary_terms.json", "glossary_term"),
            ("glossary_nodes.json", "glossary_node"),
            ("documents.json", "document"),
            ("deleted_entities.json", None),
        ]:
            path = self._fixtures_dir / filename
            if not path.exists():
                continue
            raw_list = json.loads(path.read_text("utf-8"))
            for raw in raw_list:
                etype = entity_type or raw.get("entity_type", "dataset")
                entity = self._parse_entity(raw, etype)
                all_entities.append(entity)

        self._validate_unique_urns([e.urn for e in all_entities], "Entity")
        domain_urns = {d.urn for d in self.load_domains()}
        self._validate_domain_refs(all_entities, domain_urns)
        self._validate_lineage_refs(all_entities)
        self._validate_owner_types(all_entities)
        return all_entities

    def load_lineage_edges(self) -> list[dict]:
        data = self._load_json("lineage.json", expect_list=True, optional=True)
        return data or []

    def load_domains_by_urn(self) -> dict[str, Domain]:
        return {d.urn: d for d in self.load_domains()}

    def _parse_entity(self, raw: dict, entity_type: str) -> CanonicalEntity:
        deleted_flag = raw.get("deleted", False)
        source_url = raw.get("datahub_url") or raw.get("source_url") or ""
        return CanonicalEntity(
            urn=raw["urn"],
            entity_type=entity_type,
            name=raw.get("name", ""),
            normalized_name=self._normalize_name(raw.get("name", "")),
            display_name=raw.get("display_name"),
            description=raw.get("description"),
            business_purpose=raw.get("business_purpose", ""),
            platform=raw.get("platform"),
            environment=raw.get("environment"),
            domain=raw.get("domain"),
            domain_urn=raw.get("domain_urn"),
            owners=self._parse_owners(raw.get("owners", [])),
            schema_fields=self._parse_schema_fields(raw.get("schema_fields", [])),
            glossary_terms=raw.get("glossary_terms", []),
            tags=raw.get("tags", []),
            upstreams=raw.get("upstreams", []),
            downstreams=raw.get("downstreams", []),
            linked_documents=raw.get("linked_documents", []),
            certified=raw.get("certified", False),
            source_url=source_url,
            raw_properties=raw.get("raw_properties", {}),
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC),
            deleted=deleted_flag,
            raw_payload=raw,
        )

    @staticmethod
    def _normalize_name(name: str) -> str:
        result = name.lower()
        result = result.replace("_", " ").replace("-", " ").replace(".", " ")
        import re
        result = re.sub(r"\s+", " ", result).strip()
        return result

    @staticmethod
    def _parse_owners(raw_owners: list[dict]) -> list[Owner]:
        return [Owner(**o) for o in raw_owners]

    @staticmethod
    def _parse_schema_fields(raw_fields: list[dict]) -> list[SchemaField]:
        fields = []
        for f in raw_fields:
            fields.append(SchemaField(
                field_path=f.get("field_path") or f.get("name", ""),
                name=f.get("name", ""),
                type=f.get("type", f.get("native_data_type", "")),
                native_data_type=f.get("native_data_type") or f.get("type", ""),
                description=f.get("description"),
                nullable=f.get("nullable", True),
                is_primary_key=f.get("is_primary_key", False),
                glossary_terms=f.get("glossary_terms", []),
                tags=f.get("tags", []),
            ))
        return fields

    def _load_json(self, filename: str, expect_list: bool = False, optional: bool = False) -> list | dict:
        path = self._fixtures_dir / filename
        if not path.exists():
            if optional:
                return [] if expect_list else {}
            raise MockValidationError(f"Fixture file not found: {path}")
        try:
            data = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError as e:
            raise MockValidationError(f"Invalid JSON in {filename}: {e}")
        if expect_list and not isinstance(data, list):
            raise MockValidationError(f"Expected list in {filename}, got {type(data).__name__}")
        return data

    @staticmethod
    def _validate_unique_urns(urns: list[str], label: str) -> None:
        seen = set()
        for urn in urns:
            if urn in seen:
                raise MockValidationError(f"Duplicate {label} URN: {urn}")
            seen.add(urn)

    @staticmethod
    def _validate_domain_refs(entities: list[CanonicalEntity], domain_urns: set[str]) -> None:
        if not domain_urns:
            return
        for e in entities:
            if e.domain_urn and e.domain_urn not in domain_urns:
                raise MockValidationError(
                    f"Entity {e.urn} references non-existent domain_urn: {e.domain_urn}"
                )

    @staticmethod
    def _validate_lineage_refs(entities: list[CanonicalEntity]) -> None:
        all_urns = {e.urn for e in entities}
        for e in entities:
            for u in e.upstreams + e.downstreams:
                if u not in all_urns:
                    log.warning("lineage_ref_not_found", entity_urn=e.urn, ref_urn=u)

    @staticmethod
    def _validate_owner_types(entities: list[CanonicalEntity]) -> None:
        for e in entities:
            for o in e.owners:
                if o.type not in _VALID_OWNER_TYPES:
                    raise MockValidationError(
                        f"Entity {e.urn} has invalid owner type '{o.type}'. Valid: {_VALID_OWNER_TYPES}"
                    )
