from ingestion.crawler import Crawler


class DocumentCrawler(Crawler):
    """Crawler for DataHub Document entities."""

    async def crawl(self, entity_type: str = "document") -> list[dict]:
        raise NotImplementedError("Document crawling is not implemented yet.")
