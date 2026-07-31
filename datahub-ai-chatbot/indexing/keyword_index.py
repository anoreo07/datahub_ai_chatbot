"""Keyword index for fast entity lookup."""


class KeywordIndex:
    """Inverted index for keyword-based entity search."""

    async def index(self, entities: list[dict]) -> None:
        raise NotImplementedError("Keyword indexing is not implemented yet.")

    async def search(self, query: str, top_k: int = 10) -> list[dict]:
        raise NotImplementedError("Keyword search is not implemented yet.")
