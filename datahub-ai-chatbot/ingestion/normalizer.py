import hashlib
import json

from ingestion.models import CanonicalEntity


def clean_name(value: str | None) -> str | None:
    """Collapse stray whitespace in a stored name/display_name/platform.

    Source metadata occasionally carries leading/trailing spaces or double
    spaces ("  EV VIN Battery Report", "Báo cáo ... tế xe "). They are not
    part of the name and silently break exact display / exact-ish matching,
    so every mapper trims + collapses whitespace before the value is stored.
    """
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def compute_content_hash(entity: CanonicalEntity) -> str:
    normalized = {
        "urn": entity.urn,
        "entity_type": entity.entity_type,
        "name": entity.name,
        "display_name": entity.display_name,
        "description": entity.description,
        "platform": entity.platform,
        "environment": entity.environment,
        "domain": entity.domain,
        "owners": sorted(
            [{"name": o.name, "type": o.type} for o in entity.owners],
            key=lambda x: x["name"],
        ),
        "glossary_terms": sorted(entity.glossary_terms),
        "tags": sorted(entity.tags),
        "schema_fields": sorted(
            [
                {
                    "name": f.name,
                    "type": f.type,
                    "description": f.description,
                    "nullable": f.nullable,
                    "primary_key": f.is_primary_key,
                }
                for f in entity.schema_fields
            ],
            key=lambda x: x["name"],
        ),
        "upstreams": sorted(entity.upstreams),
        "downstreams": sorted(entity.downstreams),
        "linked_documents": sorted(entity.linked_documents),
        "source_url": entity.source_url,
        "raw_properties": {k: v for k, v in entity.raw_properties.items()},
    }
    raw = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()
