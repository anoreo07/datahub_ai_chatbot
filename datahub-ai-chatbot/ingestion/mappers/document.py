from ingestion.mappers import BaseMapper
from ingestion.models import CanonicalEntity, Owner
from ingestion.normalizer import clean_name


class DocumentMapper(BaseMapper):
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        info = raw.get("info") or {}
        ownership = raw.get("ownership") or {}
        platform_info = raw.get("platform") or {}

        urn = raw.get("urn", "")
        name = clean_name(info.get("title") or raw.get("name", "")) or ""
        contents_obj = info.get("contents") or {}
        contents_text = contents_obj.get("text") if isinstance(contents_obj, dict) else contents_obj
        description = contents_text or raw.get("description") or raw.get("documentation")

        owners: list[Owner] = []
        for o in (ownership.get("owners") or []):
            owner_data = o.get("owner", {})
            owner_name = (
                owner_data.get("username")
                or owner_data.get("info", {}).get("displayName", "")
                or owner_data.get("urn", "")
            )
            if owner_name:
                owners.append(Owner(name=owner_name, type=o.get("type", "USER")))

        return CanonicalEntity(
            urn=urn,
            entity_type="document",
            name=name,
            display_name=clean_name(raw.get("displayName") or name) or name,
            description=description,
            platform=clean_name(platform_info.get("name")),
            owners=owners,
            source_url=self._build_url(url_builder, urn) if url_builder else None,
            deleted=False,
            raw_payload=raw,
        )

    @staticmethod
    def _build_url(url_builder: object, urn: str) -> str | None:
        if hasattr(url_builder, "document_url"):
            return url_builder.document_url(urn)
        if hasattr(url_builder, "entity_url"):
            return url_builder.entity_url("document", urn)
        return None
