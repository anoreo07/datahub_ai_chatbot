"""Test retry policy."""
import pytest

from sync.retry import RetryPolicy


class RetryableError(Exception):
    pass


class NonRetryableError(Exception):
    pass


@pytest.mark.asyncio
async def test_retry_success():
    policy = RetryPolicy(max_attempts=3, base_delay=0.01)
    call_count = 0

    async def fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RetryableError("try again")
        return "success"

    result = await policy.execute(fn)
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted():
    policy = RetryPolicy(max_attempts=2, base_delay=0.01)

    async def fn():
        raise RetryableError("always fail")

    with pytest.raises(RetryableError):
        await policy.execute(fn)


@pytest.mark.asyncio
async def test_non_retryable_error():
    policy = RetryPolicy(max_attempts=3, base_delay=0.01)

    async def fn():
        raise ValueError("non-retryable")

    with pytest.raises(ValueError):
        await policy.execute(fn)


@pytest.mark.asyncio
async def test_is_retryable():
    policy = RetryPolicy()
    assert policy.is_retryable(RetryableError("test"))
    assert not policy.is_retryable(ValueError("test"))
    assert not policy.is_retryable(KeyError("test"))
