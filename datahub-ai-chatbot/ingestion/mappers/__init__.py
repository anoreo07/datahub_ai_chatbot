from abc import ABC, abstractmethod

from ingestion.models import CanonicalEntity


class BaseMapper(ABC):
    @abstractmethod
    def to_canonical(self, raw: dict, url_builder: object | None = None) -> CanonicalEntity:
        ...
