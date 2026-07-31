from ingestion.crawler import Crawler


class DashboardCrawler(Crawler):
    """Crawler for DataHub Dashboard entities."""

    async def crawl(self, entity_type: str = "dashboard") -> list[dict]:
        raise NotImplementedError("Dashboard crawling is not implemented yet.")
