from retrieval.citation import Citation, build_citations, validate_citations
from retrieval.context_builder import ContextDocument


def make_doc(cid: str, urn: str, name: str = "") -> ContextDocument:
    return ContextDocument(
        cid=cid, source_type="datahub_entity", entity_urn=urn,
        entity_name=name or urn, content="test",
    )


def test_build_citations() -> None:
    docs = [make_doc("E1", "urn:1"), make_doc("E2", "urn:2")]
    citations = build_citations(docs, ["E1", "E2"])
    assert len(citations) == 2
    assert citations[0].entity_urn == "urn:1"
    assert citations[1].entity_urn == "urn:2"


def test_build_citations_deduplicates_urn() -> None:
    docs = [make_doc("E1", "urn:1"), make_doc("E2", "urn:1")]
    citations = build_citations(docs, ["E1", "E2"])
    assert len(citations) == 1


def test_validate_citations() -> None:
    docs = [make_doc("E1", "urn:1")]
    citations = [Citation("E1", "datahub_entity", "urn:1", "e1")]
    valid = validate_citations(citations, docs)
    assert len(valid) == 1


def test_validate_citations_removes_invalid() -> None:
    docs = [make_doc("E1", "urn:1")]
    citations = [Citation("E1", "datahub_entity", "urn:1", "e1"),
                 Citation("E2", "datahub_entity", "urn:unknown", "unk")]
    valid = validate_citations(citations, docs)
    assert len(valid) == 1
    assert valid[0].entity_urn == "urn:1"


def test_citation_to_dict() -> None:
    c = Citation("E1", "datahub_entity", "urn:1", "entity1", url="http://example.com", page=1, section="sec")
    d = c.to_dict()
    assert d["id"] == "E1"
    assert d["entity_urn"] == "urn:1"
    assert d["url"] == "http://example.com"
    assert d["page"] == 1
    assert d["section"] == "sec"
