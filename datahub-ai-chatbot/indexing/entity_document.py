from pydantic import BaseModel

from ingestion.models import CanonicalEntity


class ChunkItem(BaseModel):
    entity_urn: str
    entity_type: str
    entity_name: str
    chunk_type: str
    chunk_index: int
    content: str
    metadata: dict
    content_hash: str


def build_chunks_for_entity(entity: CanonicalEntity) -> list[ChunkItem]:
    chunks: list[ChunkItem] = []
    owners_str = ", ".join(o.name for o in entity.owners)
    terms = entity.glossary_terms or []

    if entity.entity_type == "dataset":
        summary_text = f"Dataset: {entity.display_name or entity.name}. "
        if entity.description:
            summary_text += f"Description: {entity.description}. "
        if entity.domain:
            summary_text += f"Domain: {entity.domain}. "
        if entity.platform:
            summary_text += f"Platform: {entity.platform}. "
        if owners_str:
            summary_text += f"Owners: {owners_str}. "
        if terms:
            summary_text += f"Glossary terms: {', '.join(terms)}. "
        chunks.append(_make_chunk(entity, "entity_summary", 0, summary_text, owners_str, terms))

        if entity.schema_fields:
            schema_text = f"Schema fields for {entity.name}:\n"
            for i, f in enumerate(entity.schema_fields):
                desc = f" - {f.name} ({f.type}): {f.description or 'N/A'}"
                schema_text += desc + "\n"
            chunks.append(_make_chunk(entity, "schema_fields", 1, schema_text, owners_str, terms))

        if entity.upstreams:
            up_text = f"Upstream dependencies of {entity.name}: {', '.join(entity.upstreams)}"
            chunks.append(_make_chunk(entity, "upstream_lineage", 2, up_text, owners_str, terms))
        if entity.downstreams:
            down_text = f"Downstream dependents of {entity.name}: {', '.join(entity.downstreams)}"
            chunks.append(_make_chunk(entity, "downstream_lineage", 3, down_text, owners_str, terms))

    elif entity.entity_type == "glossary_term":
        term_text = f"Glossary term: {entity.display_name or entity.name}. "
        if entity.description:
            term_text += f"Definition: {entity.description}. "
        if entity.domain:
            term_text += f"Domain: {entity.domain}. "
        if owners_str:
            term_text += f"Owners: {owners_str}. "
        chunks.append(_make_chunk(entity, "term_definition", 0, term_text, owners_str, terms))
        if entity.upstreams or entity.downstreams:
            rel_text = f"Related terms for {entity.name}: "
            if entity.upstreams:
                rel_text += f"Parents: {', '.join(entity.upstreams)}. "
            if entity.downstreams:
                rel_text += f"Children: {', '.join(entity.downstreams)}."
            chunks.append(_make_chunk(entity, "term_relationship", 1, rel_text, owners_str, terms))

    elif entity.entity_type == "dashboard":
        dash_text = f"Dashboard: {entity.display_name or entity.name}. "
        if entity.description:
            dash_text += f"Description: {entity.description}. "
        if entity.domain:
            dash_text += f"Domain: {entity.domain}. "
        if owners_str:
            dash_text += f"Owners: {owners_str}. "
        if entity.upstreams:
            dash_text += f"Input datasets: {', '.join(entity.upstreams)}. "
        chunks.append(_make_chunk(entity, "dashboard_summary", 0, dash_text, owners_str, terms))

    elif entity.entity_type == "document":
        doc_text = f"Document: {entity.display_name or entity.name}. "
        if entity.description:
            doc_text += f"Description: {entity.description}. "
        if entity.domain:
            doc_text += f"Domain: {entity.domain}. "
        if owners_str:
            doc_text += f"Owners: {owners_str}. "
        if entity.upstreams:
            doc_text += f"Related entities: {', '.join(entity.upstreams)}. "
        chunks.append(_make_chunk(entity, "document_summary", 0, doc_text, owners_str, terms))

        raw = (entity.raw_payload or {})
        doc_sections = raw.get("_doc_content", [])
        for i, section in enumerate(doc_sections):
            heading = section.get("heading", "")
            content = section.get("content", "")
            section_text = f"[{heading}]\n{content}" if heading else content
            chunks.append(_make_chunk(
                entity, "document_chunk", i + 1, section_text,
                owners_str, terms,
                extra={"source_title": entity.display_name or entity.name, "section": heading},
            ))

    return chunks


def _make_chunk(
    entity: CanonicalEntity,
    chunk_type: str,
    idx: int,
    content: str,
    owners_str: str,
    term_urns: list[str],
    extra: dict | None = None,
) -> ChunkItem:
    import hashlib
    meta = {
        "entity_urn": entity.urn,
        "entity_type": entity.entity_type,
        "entity_name": entity.display_name or entity.name,
        "chunk_type": chunk_type,
        "datahub_url": entity.datahub_url,
        "owner_names": owners_str or "",
        "term_urns": term_urns or [],
        "domain": entity.domain or "",
        "platform": entity.platform or "",
        "environment": entity.environment or "",
        "source_title": entity.display_name or entity.name,
        "page": None,
        "section": None,
    }
    if extra:
        meta.update(extra)
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return ChunkItem(
        entity_urn=entity.urn,
        entity_type=entity.entity_type,
        entity_name=entity.display_name or entity.name,
        chunk_type=chunk_type,
        chunk_index=idx,
        content=content,
        metadata=meta,
        content_hash=content_hash,
    )
