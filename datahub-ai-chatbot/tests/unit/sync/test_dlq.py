"""Test dead-letter queue implementations."""
import pytest

from sync.dlq import InMemoryDeadLetterQueue
from sync.models import EventType, MetadataChangeEvent


@pytest.mark.asyncio
async def test_dlq_push_size():
    dlq = InMemoryDeadLetterQueue()
    event = MetadataChangeEvent.create(EventType.UPDATE, "urn:li:dataset:test")
    await dlq.push(event, "test error")
    size = await dlq.size()
    assert size == 1
    await dlq.close()


@pytest.mark.asyncio
async def test_dlq_pop():
    dlq = InMemoryDeadLetterQueue()
    event = MetadataChangeEvent.create(EventType.CREATE, "urn:li:dataset:test")
    await dlq.push(event, "error msg")
    popped, error = await dlq.pop()
    assert popped is not None
    assert popped.event_id == event.event_id
    assert error == "error msg"
    size = await dlq.size()
    assert size == 0
    await dlq.close()


@pytest.mark.asyncio
async def test_dlq_empty_pop():
    dlq = InMemoryDeadLetterQueue()
    result = await dlq.pop()
    assert result is None
    await dlq.close()


@pytest.mark.asyncio
async def test_dlq_close():
    dlq = InMemoryDeadLetterQueue()
    await dlq.close()
    size = await dlq.size()
    assert size == 0
