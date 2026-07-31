from abc import ABC, abstractmethod
from typing import Any

from sync.models import MetadataChangeEvent


class EventConsumer(ABC):
    @abstractmethod
    async def subscribe(self, channel: str = "metadata_changes") -> None:
        ...

    @abstractmethod
    async def poll(self, timeout_seconds: float = 1.0) -> MetadataChangeEvent | None:
        ...

    @abstractmethod
    async def ack(self, event: MetadataChangeEvent) -> None:
        ...

    @abstractmethod
    async def nack(self, event: MetadataChangeEvent) -> None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class InMemoryEventConsumer(EventConsumer):
    def __init__(self) -> None:
        self._queue: list[MetadataChangeEvent] = []
        self._acked: set[str] = set()

    async def subscribe(self, channel: str = "metadata_changes") -> None:
        pass

    async def poll(self, timeout_seconds: float = 1.0) -> MetadataChangeEvent | None:
        if self._queue:
            return self._queue.pop(0)
        return None

    async def ack(self, event: MetadataChangeEvent) -> None:
        self._acked.add(event.event_id)

    async def nack(self, event: MetadataChangeEvent) -> None:
        pass

    async def close(self) -> None:
        self._queue.clear()

    def publish(self, event: MetadataChangeEvent) -> None:
        if event.event_id not in self._acked:
            self._queue.append(event)


class RedisStreamEventConsumer(EventConsumer):
    def __init__(self, redis_url: str = "redis://localhost:6380/0") -> None:
        self._redis_url = redis_url
        self._client: Any = None
        self._stream_key = "metadata_changes"
        self._group = "sync_workers"
        self._consumer = "worker_1"

    async def _get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = await aioredis.from_url(self._redis_url)
            try:
                await self._client.xgroup_create(
                    self._stream_key, self._group, id="0", mkstream=True
                )
            except Exception:
                pass
        return self._client

    async def subscribe(self, channel: str = "metadata_changes") -> None:
        self._stream_key = channel

    async def poll(self, timeout_seconds: float = 1.0) -> MetadataChangeEvent | None:
        try:
            client = await self._get_client()
            results = await client.xreadgroup(
                groupname=self._group,
                consumername=self._consumer,
                streams={self._stream_key: ">"},
                count=1,
                block=int(timeout_seconds * 1000),
            )
            if results:
                for stream_key, messages in results:
                    for msg_id, msg_data in messages:
                        event = MetadataChangeEvent(
                            event_id=msg_data.get(b"event_id", b"").decode(),
                            entity_urn=msg_data.get(b"entity_urn", b"").decode(),
                            entity_type=msg_data.get(b"entity_type", b"").decode(),
                        )
                        event.metadata = {"redis_msg_id": msg_id.decode()}
                        return event
        except Exception:
            pass
        return None

    async def ack(self, event: MetadataChangeEvent) -> None:
        redis_msg_id = event.metadata.get("redis_msg_id") if event.metadata else None
        if redis_msg_id:
            client = await self._get_client()
            await client.xack(self._stream_key, self._group, redis_msg_id)

    async def nack(self, event: MetadataChangeEvent) -> None:
        pass

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
