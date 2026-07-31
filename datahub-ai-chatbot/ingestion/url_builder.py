from config.settings import settings


class DataHubUrlBuilder:
    ROUTES: dict[str, str] = {
        "dataset": "dataset",
        "dashboard": "dashboard",
        "glossary_term": "glossary",
        "glossary_node": "glossaryNode",
        "document": "document",
        "chart": "chart",
        "dataJob": "dataJob",
        "dataFlow": "dataFlow",
        "container": "container",
        "tag": "tag",
        "mlModel": "mlModel",
        "mlFeatureTable": "mlFeatureTable",
    }

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or settings.DATAHUB_FRONTEND_URL).rstrip("/")

    def entity_url(self, entity_type: str, urn: str) -> str:
        route = self.ROUTES.get(entity_type, "entity")
        return f"{self._base}/{route}/{urn}"

    def dataset_url(self, urn: str) -> str:
        return self.entity_url("dataset", urn)

    def dashboard_url(self, urn: str) -> str:
        return self.entity_url("dashboard", urn)

    def glossary_url(self, urn: str) -> str:
        return self.entity_url("glossary_term", urn)

    def document_url(self, urn: str) -> str:
        return self.entity_url("document", urn)

    def search_url(self, query: str) -> str:
        return f"{self._base}/search?q={query}"
