from ingestion.crawler import Crawler


class GlossaryCrawler(Crawler):
    """Crawler for DataHub GlossaryTerm entities."""

    async def crawl(self, entity_type: str = "glossaryTerm") -> list[dict]:
        raise NotImplementedError("Glossary crawling is not implemented yet.")
