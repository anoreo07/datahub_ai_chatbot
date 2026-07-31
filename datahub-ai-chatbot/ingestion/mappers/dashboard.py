from ingestion.mappers import BaseMapper
from ingestion.models import CanonicalEntity, Owner


class DashboardMapper(BaseMapper):
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        properties = raw.get("properties") or {}
        ownership = raw.get("ownership") or {}
        platform_info = raw.get("platform") or {}
        domain_info = raw.get("domain") or {}

        urn = raw.get("urn", "")
        name = properties.get("name") or raw.get("name", "")
        description = properties.get("description") or raw.get("description")
        owners = self._map_owners(ownership)
        upstreams, downstreams = self._extract_lineage(raw)

        return CanonicalEntity(
            urn=urn,
            entity_type="dashboard",
            name=name,
            display_name=raw.get("displayName") or name,
            description=description,
            platform=platform_info.get("name"),
            environment="PROD",
            domain=self._map_domain(domain_info),
            owners=owners,
            upstreams=upstreams,
            downstreams=downstreams,
            source_url=self._build_url(url_builder, "dashboard", urn) if url_builder else None,
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
    def _extract_lineage(raw: dict) -> tuple[list[str], list[str]]:
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
        if hasattr(url_builder, "dashboard_url"):
            return url_builder.dashboard_url(urn)
        return None
