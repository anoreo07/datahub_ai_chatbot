"""Crawler for fetching entities from DataHub."""


class Crawler:
    """Base crawler for DataHub entities."""

    async def crawl(self, entity_type: str) -> list[dict]:
        raise NotImplementedError("Subclasses must implement crawl method.")
