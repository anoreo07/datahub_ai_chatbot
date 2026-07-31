import datetime
import uuid
from enum import StrEnum

from pydantic import BaseModel


class EventType(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class MetadataChangeEvent(BaseModel):
    event_id: str = ""
    event_type: EventType = EventType.UPDATE
    entity_urn: str = ""
    entity_type: str = ""
    timestamp: datetime.datetime | None = None
    payload: dict = {}
    source: str = "graphql"

    @classmethod
    def create(
        cls,
        event_type: EventType,
        entity_urn: str,
        entity_type: str = "",
        payload: dict | None = None,
        source: str = "graphql",
    ) -> "MetadataChangeEvent":
        return cls(
            event_id=uuid.uuid4().hex[:16],
            event_type=event_type,
            entity_urn=entity_urn,
            entity_type=entity_type or cls._infer_type(entity_urn),
            timestamp=datetime.datetime.now(datetime.UTC),
            payload=payload or {},
            source=source,
        )

    @staticmethod
    def _infer_type(urn: str) -> str:
        if ":dataset:" in urn or ":dataset(" in urn:
            return "dataset"
        if ":glossaryTerm:" in urn:
            return "glossary_term"
        if ":dashboard:" in urn:
            return "dashboard"
        if ":document:" in urn:
            return "document"
        return "unknown"


class DeleteMode(StrEnum):
    SOFT = "soft"
    HARD = "hard"


class SyncMode(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    EVENT = "event"
