from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from ingestion.models import CanonicalEntity, Domain, EntityPage, Owner, SchemaField


class DataHubSource(ABC):
    @abstractmethod
    async def list_entities(
        self,
        entity_type: str,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> EntityPage:
        ...

    @abstractmethod
    async def search_entities(self, entity_type: str, query: str = "*") -> Sequence[CanonicalEntity]:
        ...

    @abstractmethod
    async def get_entity(self, urn: str) -> CanonicalEntity | None:
        ...

    @abstractmethod
    async def get_entity_by_urn(self, urn: str) -> CanonicalEntity | None:
        ...

    @abstractmethod
    async def list_entity_type(self, entity_type: str) -> Sequence[CanonicalEntity]:
        ...

    @abstractmethod
    async def list_datasets(self) -> Sequence[CanonicalEntity]:
        ...

    @abstractmethod
    async def list_dashboards(self) -> Sequence[CanonicalEntity]:
        ...

    @abstractmethod
    async def list_glossary_terms(self) -> Sequence[CanonicalEntity]:
        ...

    @abstractmethod
    async def list_documents(self) -> Sequence[CanonicalEntity]:
        ...

    @abstractmethod
    async def get_lineage(self, urn: str, direction: str = "both", depth: int = 1) -> dict[str, Any]:
        ...

    @abstractmethod
    async def healthcheck(self) -> bool:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    async def list_domains(self) -> list[Domain]:
        return []

    async def get_schema(self, urn: str) -> list[SchemaField]:
        entity = await self.get_entity(urn)
        if entity:
            return entity.schema_fields
        return []

    async def get_owners(self, urn: str) -> list[Owner]:
        entity = await self.get_entity(urn)
        if entity:
            return entity.owners
        return []

    async def get_by_domain(self, domain_name: str) -> list[CanonicalEntity]:
        return []

    async def get_by_platform(self, platform: str) -> list[CanonicalEntity]:
        return []

    async def get_by_environment(self, env: str) -> list[CanonicalEntity]:
        return []

    async def resolve_by_name(self, name: str) -> list[CanonicalEntity]:
        return []
