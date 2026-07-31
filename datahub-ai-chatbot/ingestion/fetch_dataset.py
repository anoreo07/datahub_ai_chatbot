from ingestion.crawler import Crawler


class DatasetCrawler(Crawler):
    """Crawler for DataHub Dataset entities."""

    async def crawl(self, entity_type: str = "dataset") -> list[dict]:
        raise NotImplementedError("Dataset crawling is not implemented yet.")
