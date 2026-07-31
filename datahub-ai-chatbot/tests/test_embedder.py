import pytest_asyncio

from indexing.embedder import MockEmbedder


@pytest_asyncio.fixture
async def embedder() -> MockEmbedder:
    return MockEmbedder()


class TestMockEmbedder:
    async def test_embed_dimension(self, mock_embedder: MockEmbedder) -> None:
        vecs = await mock_embedder.embed(["hello"])
        assert len(vecs) == 1
        assert len(vecs[0]) == 384

    async def test_embed_deterministic(self, mock_embedder: MockEmbedder) -> None:
        v1 = await mock_embedder.embed(["test input"])
        v2 = await mock_embedder.embed(["test input"])
        assert v1[0] == v2[0]

    async def test_different_input_different_vector(self, mock_embedder: MockEmbedder) -> None:
        v1 = await mock_embedder.embed(["hello"])
        v2 = await mock_embedder.embed(["world"])
        assert v1[0] != v2[0]

    async def test_embed_query(self, mock_embedder: MockEmbedder) -> None:
        v = await mock_embedder.embed_query("test")
        assert len(v) == 384

    async def test_embed_query_same_as_single_embed(self, mock_embedder: MockEmbedder) -> None:
        v1 = await mock_embedder.embed_query("test")
        v2 = (await mock_embedder.embed(["test"]))[0]
        assert v1 == v2

    async def test_batch_embed(self, mock_embedder: MockEmbedder) -> None:
        texts = ["a", "b", "c"]
        vecs = await mock_embedder.embed(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    async def test_dimension_property(self, mock_embedder: MockEmbedder) -> None:
        assert mock_embedder.dimension == 384

    async def test_model_name(self, mock_embedder: MockEmbedder) -> None:
        assert mock_embedder.model_name == "mock-hash-v1"

    async def test_not_all_zeros(self, mock_embedder: MockEmbedder) -> None:
        vecs = await mock_embedder.embed(["hello", "world"])
        for v in vecs:
            assert any(abs(x) > 0.001 for x in v), "Vector should not be all zeros"
