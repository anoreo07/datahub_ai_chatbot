from config.settings import settings
from ingestion.source import DataHubSource


def create_datahub_source() -> DataHubSource:
    if settings.USE_MOCK_DATAHUB:
        from ingestion.mock_source import MockDataHubSource
        return MockDataHubSource()
    if not settings.DATAHUB_GMS_URL:
        raise RuntimeError(
            "USE_MOCK_DATAHUB=false but DATAHUB_GMS_URL is not set. "
            "Set DATAHUB_GMS_URL or enable USE_MOCK_DATAHUB=true"
        )
    from ingestion.graphql_source import GraphQLDataHubSource
    return GraphQLDataHubSource(
        gms_url=settings.DATAHUB_GMS_URL,
        token=settings.DATAHUB_TOKEN or None,
        timeout_seconds=settings.DATAHUB_REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.DATAHUB_MAX_RETRIES,
    )


__all__ = ["DataHubSource", "create_datahub_source"]
