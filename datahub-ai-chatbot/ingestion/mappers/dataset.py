import datetime
import re

from ingestion.mappers import BaseMapper
from ingestion.models import CanonicalEntity, Owner, SchemaField
from ingestion.normalizer import clean_name

_URN_NAME_RE = re.compile(
    r"urn:li:dataset:\(urn:li:dataPlatform:[^,]+,(.+),(?:PROD|DEV|QA|UAT|ELM)\)$"
)


class DatasetMapper(BaseMapper):
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        properties = raw.get("properties") or {}
        schema = raw.get("schemaMetadata") or {}
        platform_info = raw.get("platform") or {}
        ownership = raw.get("ownership") or {}
        domain_info = raw.get("domain") or {}
        tags_info = raw.get("tags") or {}

        owners = self._map_owners(ownership)
        fields = self._map_schema_fields(schema)
        upstreams, downstreams = self._extract_lineage_urns(raw)
        domain = self._map_domain(domain_info)
        glossary_terms = self._map_glossary_terms(raw.get("glossaryTerms") or {})
        tags = self._map_tags(tags_info)

        urn = raw.get("urn", "")
        name = clean_name(
            raw.get("name") or properties.get("name") or self._name_from_urn(urn)
        ) or ""
        description = properties.get("description")

        return CanonicalEntity(
            urn=urn,
            entity_type="dataset",
            name=name,
            display_name=clean_name(raw.get("displayName") or name) or name,
            description=description,
            platform=clean_name(platform_info.get("name")),
            environment=properties.get("environment") or "PROD",
            domain=domain,
            owners=owners,
            glossary_terms=glossary_terms,
            tags=tags,
            schema_fields=fields,
            upstreams=upstreams,
            downstreams=downstreams,
            source_url=f"{url_builder.dataset_url(urn)}" if url_builder and hasattr(url_builder, "dataset_url") else None,
            raw_properties=self._normalize_custom_properties(properties.get("customProperties")),
            updated_at=self._parse_timestamp(raw.get("lastModified", {}).get("time")),
            deleted=False,
            raw_payload=raw,
        )

    def _map_owners(self, ownership: dict) -> list[Owner]:
        owners: list[Owner] = []
        for o in (ownership.get("owners") or []):
            owner_data = o.get("owner", {})
            name = (
                owner_data.get("username")
                or owner_data.get("info", {}).get("displayName", "")
                or owner_data.get("urn", "")
            )
            owner_type = o.get("type", "USER")
            if name:
                owners.append(Owner(name=name, type=owner_type))
        return owners


def _normalize_field_path(field_path: str) -> str:
    """Normalize a DataHub fieldPath to a clean column name.

    DataHub v2 schema format emits paths like:
        ``[version=2.0].[type=string].actual_field_name``
        ``[version=2.0].[type=struct].outer.[type=string].inner``

    Only the final dot-separated segment that does NOT start with ``[`` is
    the actual column/field name users care about.  All ``[key=value]``
    segments are metadata annotations; we strip them and return the real
    identifier.  If no such segment exists (unusual format), fall back to
    the raw path so no data is silently lost.
    """
    if not field_path:
        return field_path
    # Fast path: no bracketed annotations present → already a clean name.
    if "[" not in field_path:
        return field_path
    segments = field_path.split(".")
    # Collect segments that are NOT bracketed annotations.
    clean = [s for s in segments if s and not s.startswith("[")]
    if clean:
        # The deepest (last) non-annotation segment is the leaf column name.
        return clean[-1]
    return field_path


class DatasetMapper(BaseMapper):
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        properties = raw.get("properties") or {}
        schema = raw.get("schemaMetadata") or {}
        platform_info = raw.get("platform") or {}
        ownership = raw.get("ownership") or {}
        domain_info = raw.get("domain") or {}
        tags_info = raw.get("tags") or {}

        owners = self._map_owners(ownership)
        fields = self._map_schema_fields(schema)
        upstreams, downstreams = self._extract_lineage_urns(raw)
        domain = self._map_domain(domain_info)
        glossary_terms = self._map_glossary_terms(raw.get("glossaryTerms") or {})
        tags = self._map_tags(tags_info)

        urn = raw.get("urn", "")
        name = clean_name(
            raw.get("name") or properties.get("name") or self._name_from_urn(urn)
        ) or ""
        description = properties.get("description")

        return CanonicalEntity(
            urn=urn,
            entity_type="dataset",
            name=name,
            display_name=clean_name(raw.get("displayName") or name) or name,
            description=description,
            platform=clean_name(platform_info.get("name")),
            environment=properties.get("environment") or "PROD",
            domain=domain,
            owners=owners,
            glossary_terms=glossary_terms,
            tags=tags,
            schema_fields=fields,
            upstreams=upstreams,
            downstreams=downstreams,
            source_url=f"{url_builder.dataset_url(urn)}" if url_builder and hasattr(url_builder, "dataset_url") else None,
            raw_properties=self._normalize_custom_properties(properties.get("customProperties")),
            updated_at=self._parse_timestamp(raw.get("lastModified", {}).get("time")),
            deleted=False,
            raw_payload=raw,
        )

    def _map_owners(self, ownership: dict) -> list[Owner]:
        owners: list[Owner] = []
        for o in (ownership.get("owners") or []):
            owner_data = o.get("owner", {})
            name = (
                owner_data.get("username")
                or owner_data.get("info", {}).get("displayName", "")
                or owner_data.get("urn", "")
            )
            owner_type = o.get("type", "USER")
            if name:
                owners.append(Owner(name=name, type=owner_type))
        return owners

    def _map_schema_fields(self, schema: dict) -> list[SchemaField]:
        fields: list[SchemaField] = []
        for f in (schema.get("fields") or []):
            raw_path = f.get("fieldPath", "")
            fields.append(SchemaField(
                name=_normalize_field_path(raw_path),
                type=f.get("nativeDataType") or f.get("type", ""),
                description=f.get("description"),
                nullable=f.get("nullable", True),
                is_primary_key=f.get("isPartOfKey", False),
            ))
        return fields

    @staticmethod
    def _extract_lineage_urns(raw: dict) -> tuple[list[str], list[str]]:
        upstreams: list[str] = []
        downstreams: list[str] = []
        for direction, key in [("upstream", "upstreamLineage"), ("downstream", "downstreamLineage")]:
            side = raw.get(key) or raw.get("lineage", {}).get(direction) or {}
            for rel in (side.get("relationships") or []):
                ent = rel.get("entity") or {}
                if ent.get("urn"):
                    if direction == "upstream":
                        upstreams.append(ent["urn"])
                    else:
                        downstreams.append(ent["urn"])
        return upstreams, downstreams

    def _map_domain(self, domain_info: dict) -> str | None:
        domains = domain_info.get("domains") or []
        if domains:
            domain = domains[0].get("domain") or {}
            props = domain.get("properties") or {}
            return props.get("name") or domain.get("name") or domain.get("urn")
        single = domain_info.get("domain") or {}
        if isinstance(single, dict):
            d = single.get("domain") or single
            props = d.get("properties") or {}
            return props.get("name") or d.get("name") or d.get("urn")
        return None

    def _map_glossary_terms(self, terms_info: dict) -> list[str]:
        return [t.get("term", {}).get("urn", "") for t in (terms_info.get("terms") or [])]

    def _map_tags(self, tags_info: dict) -> list[str]:
        return [t.get("tag", {}).get("name", "") for t in (tags_info.get("tags") or [])]

    @staticmethod
    def _name_from_urn(urn: str) -> str:
        m = _URN_NAME_RE.match(urn)
        if m and m.group(1).strip():
            return m.group(1).strip()
        return urn

    @staticmethod
    def _normalize_custom_properties(props: object) -> dict:
        if isinstance(props, dict):
            return props
        if isinstance(props, list):
            result = {}
            for entry in props:
                if isinstance(entry, dict) and "key" in entry:
                    result[entry["key"]] = entry.get("value", "")
            return result
        return {}

    @staticmethod
    def _parse_timestamp(ts: str | int | None) -> datetime.datetime | None:
        if ts is None:
            return None
        try:
            return datetime.datetime.fromtimestamp(int(ts) / 1000, tz=datetime.UTC)
        except (ValueError, OSError):
            return None
