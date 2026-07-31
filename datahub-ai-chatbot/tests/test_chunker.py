from indexing.chunker import chunk_text


def test_short_text_no_split() -> None:
    text = "Short text."
    result = chunk_text(text, max_tokens=1000)
    assert result == [text]


def test_long_text_splits() -> None:
    text = "Sentence one. " * 200
    result = chunk_text(text, max_tokens=100, overlap=10)
    assert len(result) > 1


def test_chunks_have_content() -> None:
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    result = chunk_text(text, max_tokens=10, overlap=2)
    assert all(len(c) > 0 for c in result)


def test_chunk_empty() -> None:
    assert chunk_text("") == [""]


def test_chunk_with_headings() -> None:
    text = "[Overview]\nThis is an overview.\n\n[Details]\nThese are the details."
    result = chunk_text(text, max_tokens=50, overlap=5)
    assert len(result) >= 1
    assert any("[Overview]" in c for c in result)


def test_deterministic() -> None:
    text = "A. " * 100 + "B. " * 100
    r1 = chunk_text(text, max_tokens=50, overlap=10)
    r2 = chunk_text(text, max_tokens=50, overlap=10)
    assert r1 == r2
