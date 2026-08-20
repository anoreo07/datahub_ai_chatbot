import structlog

from config.settings import settings
from ingestion.source import DataHubSource

log = structlog.get_logger()


class DataHubSourceFactory:
    @staticmethod
    def create() -> DataHubSource:
        if settings.USE_MOCK_DATAHUB:
            log.info("datahub_source_factory", mode="mock")
            from ingestion.mock_source import MockDataHubSource
            source = MockDataHubSource()
            return source

        from urllib.parse import urlparse
        host = urlparse(settings.DATAHUB_GMS_URL).netloc or settings.DATAHUB_GMS_URL
        log.info("datahub_source_factory", mode="graphql", gms_host=host)
        from ingestion.graphql_source import GraphQLDataHubSource
        source = GraphQLDataHubSource(
            gms_url=settings.DATAHUB_GMS_URL,
            token=settings.DATAHUB_TOKEN,
            timeout_seconds=settings.DATAHUB_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.DATAHUB_MAX_RETRIES,
        )
        return source
