from retrieval.context_builder import ContextDocument, build_context, format_fallback_answer
from retrieval.hybrid_search import SearchResult


def make_result(urn: str, name: str, score: float = 1.0, payload: dict | None = None) -> SearchResult:
    return SearchResult(urn=urn, entity_type="dataset", name=name, score=score, payload=payload or {})


def test_build_context_empty() -> None:
    docs, xml = build_context([])
    assert docs == []
    assert "<context>" in xml
    assert "</context>" in xml


def test_build_context_single() -> None:
    results = [make_result("urn:1", "entity1", payload={"content": "test content", "chunk_type": "entity_summary"})]
    docs, xml = build_context(results)
    assert len(docs) == 1
    assert docs[0].cid == "E1"
    assert docs[0].entity_urn == "urn:1"
    assert "test content" in xml
    assert "<context>" in xml
    assert "</context>" in xml


def test_build_context_max_chunks() -> None:
    results = [
        make_result(f"urn:{i}", f"e{i}", payload={"content": "x", "chunk_type": "entity_summary"})
        for i in range(20)
    ]
    docs, xml = build_context(results, max_chunks=3)
    assert len(docs) == 3


def test_build_context_max_characters() -> None:
    long_content = "x" * 50000
    results = [make_result("urn:1", "e1", payload={"content": long_content, "chunk_type": "entity_summary"})]
    docs, xml = build_context(results, max_chunks=1)
    assert len(docs) == 1
    assert len(docs[0].content) <= 24000


def test_context_document_to_xml() -> None:
    doc = ContextDocument("E1", "datahub_entity", "urn:1", "entity1", "content here", url="http://ex.com")
    xml = doc.to_xml()
    assert '<entity id="E1">' in xml
    assert "<urn>urn:1</urn>" in xml
    assert "<content>content here</content>" in xml
    assert "<url>http://ex.com</url>" in xml


def test_context_document_xml_escapes() -> None:
    doc = ContextDocument("E1", "datahub_entity", "urn:1", "e&1", "content <with> special chars &")
    xml = doc.to_xml()
    assert "&amp;" in xml
    assert "&lt;" in xml
    assert "&gt;" in xml


def test_format_fallback_answer_no_docs() -> None:
    answer = format_fallback_answer([], "test")
    assert "Không tìm thấy" in answer


def test_format_fallback_answer_with_docs() -> None:
    docs = [ContextDocument("E1", "datahub_entity", "urn:1", "entity1", "some content")]
    answer = format_fallback_answer(docs, "test")
    assert "entity1" in answer
    assert "some content" in answer
