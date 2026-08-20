from ingestion.mappers import BaseMapper
from ingestion.models import CanonicalEntity, Owner
from ingestion.normalizer import clean_name


class GlossaryTermMapper(BaseMapper):
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        props = raw.get("properties") or {}
        ownership = raw.get("ownership") or {}
        domain_info = raw.get("domain") or {}

        urn = raw.get("urn", "")
        name = clean_name(props.get("name") or raw.get("name", "")) or ""
        description = props.get("description") or raw.get("description")

        owners = self._map_owners(ownership)

        related_urns: list[str] = []
        related = raw.get("relatedEntities") or raw.get("relatedTerms") or {}
        for rel in (related.get("relationships") or []) or (related.get("terms") or []):
            entity = rel.get("entity") or rel.get("term") or {}
            if entity.get("urn"):
                related_urns.append(entity["urn"])

        return CanonicalEntity(
            urn=urn,
            entity_type="glossary_term",
            name=name,
            display_name=clean_name(raw.get("displayName") or name) or name,
            description=description,
            domain=self._map_domain(domain_info),
            owners=owners,
            downstreams=related_urns,
            source_url=self._build_url(url_builder, "glossary_term", urn) if url_builder else None,
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
            if name:
                owners.append(Owner(name=name, type=o.get("type", "USER")))
        return owners

    @staticmethod
    def _map_domain(domain_info: dict) -> str | None:
        domains = domain_info.get("domains") or []
        if domains:
            domain = domains[0].get("domain") or {}
            props = domain.get("properties") or {}
            return props.get("name") or domain.get("name")
        single = domain_info.get("domain") or {}
        if isinstance(single, dict):
            d = single.get("domain") or single
            props = d.get("properties") or {}
            return props.get("name") or d.get("name")
        return None

    @staticmethod
    def _build_url(url_builder: object, entity_type: str, urn: str) -> str | None:
        if hasattr(url_builder, "entity_url"):
            return url_builder.entity_url(entity_type, urn)
        if hasattr(url_builder, "glossary_url"):
            return url_builder.glossary_url(urn)
        return None


class GlossaryNodeMapper(BaseMapper):
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        props = raw.get("properties") or {}
        urn = raw.get("urn", "")
        name = clean_name(props.get("name") or raw.get("name", "")) or ""
        description = props.get("description") or raw.get("description")

        children: list[str] = []
        for child in (raw.get("children") or {}).get("relationships") or []:
            entity = child.get("entity") or {}
            if entity.get("urn"):
                children.append(entity["urn"])

        return CanonicalEntity(
            urn=urn,
            entity_type="glossary_node",
            name=name,
            display_name=clean_name(raw.get("displayName") or name) or name,
            description=description,
            downstreams=children,
            deleted=False,
            raw_payload=raw,
        )
