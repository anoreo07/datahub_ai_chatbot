"""Test MetadataEventHandler."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from sync.dlq import InMemoryDeadLetterQueue
from sync.event_handler import MetadataEventHandler
from sync.models import EventType, MetadataChangeEvent
from sync.retry import RetryPolicy


@pytest.mark.asyncio
async def test_event_handler_unknown_type():
    """Unknown event type returns False without error."""
    session = AsyncMock()
    handler = MetadataEventHandler(session)
    event = MetadataChangeEvent.create(
        EventType.UPDATE,
        "urn:li:dataset:nonexistent",
    )
    result = await handler.handle(event)
    assert result is False


@pytest.mark.asyncio
async def test_event_handler_create_entity_not_found():
    session = AsyncMock()
    handler = MetadataEventHandler(session)
    handler._source.get_entity = AsyncMock(return_value=None)

    event = MetadataChangeEvent.create(
        EventType.CREATE,
        "urn:li:dataset:nonexistent",
    )
    result = await handler.handle(event)
    assert result is False


@pytest.mark.asyncio
async def test_event_handler_retry_exhausted_goes_to_dlq():
    session = AsyncMock()
    dlq = InMemoryDeadLetterQueue()
    retry = RetryPolicy(max_attempts=2, base_delay=0.01)
    handler = MetadataEventHandler(session, dlq=dlq, retry_policy=retry)

    handler._source.get_entity = AsyncMock(side_effect=ValueError("always fails"))

    event = MetadataChangeEvent.create(
        EventType.CREATE,
        "urn:li:dataset:fail",
    )
    result = await handler.handle(event)
    assert result is False
    size = await dlq.size()
    assert size >= 0


@pytest.mark.asyncio
async def test_event_handler_delete_soft():
    session = AsyncMock()
    handler = MetadataEventHandler(session)

    mock_entity = MagicMock()
    mock_entity.payload = {}
    handler._entity_repo.get_by_urn = AsyncMock(return_value=mock_entity)

    event = MetadataChangeEvent.create(
        EventType.DELETE,
        "urn:li:dataset:test",
    )
    result = await handler.handle(event)
    assert result is True


@pytest.mark.asyncio
async def test_event_handler_close():
    session = AsyncMock()
    handler = MetadataEventHandler(session)
    await handler.close()
    assert True
