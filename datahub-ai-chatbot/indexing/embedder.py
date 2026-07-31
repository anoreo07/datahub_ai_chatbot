import hashlib
from abc import ABC, abstractmethod

import numpy as np
from openai import AsyncOpenAI

from config.settings import settings


class Embedder(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class MockEmbedder(Embedder):
    def __init__(self) -> None:
        self._dim = settings.EMBEDDING_DIMENSION
        self._model = settings.EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._hash_vector(text)

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model

    def _hash_vector(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:8], "big")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


class OllamaEmbedder(Embedder):
    def __init__(self) -> None:
        self._model = "nomic-embed-text"
        self._dim = 768
        base_url = settings.OLLAMA_BASE_URL or "http://localhost:11434/v1"
        self._client = AsyncOpenAI(base_url=base_url, api_key="ollama")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [r.embedding for r in response.data]

    async def embed_query(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=[text],
        )
        return response.data[0].embedding

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model


def create_embedder() -> Embedder:
    if settings.EMBEDDING_PROVIDER == "ollama":
        return OllamaEmbedder()
    return MockEmbedder()
