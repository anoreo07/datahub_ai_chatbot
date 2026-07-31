"""Test event consumers."""
import pytest

from sync.consumer import InMemoryEventConsumer
from sync.models import EventType, MetadataChangeEvent


@pytest.mark.asyncio
async def test_inmemory_poll_empty():
    consumer = InMemoryEventConsumer()
    event = await consumer.poll()
    assert event is None
    await consumer.close()


@pytest.mark.asyncio
async def test_inmemory_publish_poll():
    consumer = InMemoryEventConsumer()
    event = MetadataChangeEvent.create(
        EventType.CREATE,
        "urn:li:dataset:test",
    )
    consumer.publish(event)
    polled = await consumer.poll()
    assert polled is not None
    assert polled.event_id == event.event_id
    await consumer.close()


@pytest.mark.asyncio
async def test_inmemory_ack():
    consumer = InMemoryEventConsumer()
    event = MetadataChangeEvent.create(
        EventType.UPDATE,
        "urn:li:dataset:test",
    )
    consumer.publish(event)
    await consumer.ack(event)
    await consumer.close()


@pytest.mark.asyncio
async def test_inmemory_close():
    consumer = InMemoryEventConsumer()
    await consumer.close()
    assert True
