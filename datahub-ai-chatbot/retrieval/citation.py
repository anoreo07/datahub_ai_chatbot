from collections.abc import Sequence

from retrieval.context_builder import ContextDocument


class Citation:
    def __init__(self, cid: str, source_type: str, entity_urn: str, entity_name: str,
                 url: str | None = None, page: int | None = None,
                 section: str | None = None) -> None:
        self.cid = cid
        self.source_type = source_type
        self.entity_urn = entity_urn
        self.entity_name = entity_name
        self.url = url
        self.page = page
        self.section = section

    def to_dict(self) -> dict:
        return {
            "id": self.cid,
            "source_type": self.source_type,
            "entity_urn": self.entity_urn,
            "entity_name": self.entity_name,
            "url": self.url,
            "page": self.page,
            "section": self.section,
        }


def build_citations(docs: Sequence[ContextDocument], citation_ids: list[str]) -> list[Citation]:
    doc_map = {d.cid: d for d in docs}
    citations: list[Citation] = []
    seen: set[str] = set()
    for cid in citation_ids:
        doc = doc_map.get(cid)
        if not doc:
            continue
        if doc.entity_urn in seen:
            continue
        seen.add(doc.entity_urn)
        citations.append(Citation(
            cid=doc.cid,
            source_type=doc.source_type,
            entity_urn=doc.entity_urn,
            entity_name=doc.entity_name,
            url=doc.url,
            page=doc.page,
            section=doc.section,
        ))
    return citations


def validate_citations(citations: list[Citation], docs: Sequence[ContextDocument]) -> list[Citation]:
    doc_urns = {d.entity_urn for d in docs}
    valid: list[Citation] = []
    for c in citations:
        if c.entity_urn in doc_urns or c.entity_urn == "":
            valid.append(c)
    return valid


def build_listing_citations(
    entities: list[dict],
    source_type: str = "database",
) -> list[Citation]:
    """Build citations for deterministic listing results (counts, domain lists, missing metadata)."""
    citations: list[Citation] = []
    seen: set[str] = set()
    for i, ent in enumerate(entities):
        urn = ent.get("urn", "")
        if urn in seen:
            continue
        seen.add(urn)
        citations.append(Citation(
            cid=f"LS{i+1}",
            source_type=source_type,
            entity_urn=urn,
            entity_name=ent.get("name", ""),
            url=ent.get("url"),
        ))
    return citations
