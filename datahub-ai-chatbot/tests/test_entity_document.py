from indexing.entity_document import build_chunks_for_entity


def test_dataset_chunks(sample_dataset) -> None:
    chunks = build_chunks_for_entity(sample_dataset)
    assert len(chunks) >= 3
    types = {c.chunk_type for c in chunks}
    assert "entity_summary" in types
    assert "schema_fields" in types
    assert "upstream_lineage" in types or "downstream_lineage" in types


def test_glossary_term_chunks(sample_glossary_term) -> None:
    chunks = build_chunks_for_entity(sample_glossary_term)
    assert len(chunks) >= 1
    assert chunks[0].chunk_type == "term_definition"
    assert "Net Revenue" in chunks[0].content
    assert "Doanh thu còn lại" in chunks[0].content


def test_dashboard_chunks(sample_dashboard) -> None:
    chunks = build_chunks_for_entity(sample_dashboard)
    assert len(chunks) >= 1
    assert chunks[0].chunk_type == "dashboard_summary"
    assert "Monthly Revenue" in chunks[0].content
    assert "Finance Analytics" in chunks[0].content


def test_chunk_metadata(sample_dataset) -> None:
    chunks = build_chunks_for_entity(sample_dataset)
    chunk = chunks[0]
    assert chunk.entity_urn == sample_dataset.urn
    assert chunk.entity_type == "dataset"
    assert chunk.metadata.get("owner_names") == "Sales Analytics"
    assert chunk.metadata.get("domain") == "Sales"
    assert chunk.metadata.get("datahub_url") == sample_dataset.datahub_url


def test_chunk_content_hash_deterministic(sample_dataset) -> None:
    chunks1 = build_chunks_for_entity(sample_dataset)
    chunks2 = build_chunks_for_entity(sample_dataset)
    assert chunks1[0].content_hash == chunks2[0].content_hash


def test_document_chunks_with_content(sample_glossary_term) -> None:
    entity = sample_glossary_term.model_copy(update={
        "entity_type": "document",
        "urn": "urn:li:document:TestDoc",
        "name": "Test Document",
        "raw_payload": {
            "_doc_content": [
                {"heading": "Section 1", "content": "Content for section one."},
                {"heading": "Section 2", "content": "Content for section two."},
            ]
        },
    })
    chunks = build_chunks_for_entity(entity)
    assert len(chunks) >= 2
    types = [c.chunk_type for c in chunks]
    assert "document_summary" in types
    assert "document_chunk" in types
