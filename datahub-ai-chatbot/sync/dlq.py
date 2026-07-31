import json
from abc import ABC, abstractmethod
from typing import Any

from sync.models import MetadataChangeEvent


class DeadLetterQueue(ABC):
    @abstractmethod
    async def push(self, event: MetadataChangeEvent, error: str) -> None:
        ...

    @abstractmethod
    async def pop(self) -> tuple[MetadataChangeEvent, str] | None:
        ...

    @abstractmethod
    async def size(self) -> int:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class InMemoryDeadLetterQueue(DeadLetterQueue):
    def __init__(self) -> None:
        self._items: list[tuple[MetadataChangeEvent, str]] = []

    async def push(self, event: MetadataChangeEvent, error: str) -> None:
        self._items.append((event, error))

    async def pop(self) -> tuple[MetadataChangeEvent, str] | None:
        if self._items:
            return self._items.pop(0)
        return None

    async def size(self) -> int:
        return len(self._items)

    async def close(self) -> None:
        self._items.clear()


class RedisDeadLetterQueue(DeadLetterQueue):
    def __init__(self, redis_url: str = "redis://localhost:6380/0") -> None:
        self._redis_url = redis_url
        self._client: Any = None
        self._key = "dlq:metadata_changes"

    async def _get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = await aioredis.from_url(self._redis_url)
        return self._client

    async def push(self, event: MetadataChangeEvent, error: str) -> None:
        client = await self._get_client()
        data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "entity_urn": event.entity_urn,
            "entity_type": event.entity_type,
            "error": error,
        }
        await client.lpush(self._key, json.dumps(data))

    async def pop(self) -> tuple[MetadataChangeEvent, str] | None:
        client = await self._get_client()
        raw = await client.rpop(self._key)
        if raw:
            data = json.loads(raw)
            event = MetadataChangeEvent(
                event_id=data.get("event_id", ""),
                entity_urn=data.get("entity_urn", ""),
                entity_type=data.get("entity_type", ""),
            )
            return event, data.get("error", "unknown")
        return None

    async def size(self) -> int:
        client = await self._get_client()
        return await client.llen(self._key)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
