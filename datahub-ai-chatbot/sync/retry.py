import asyncio
import random
from typing import Any


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def is_retryable(self, error: Exception) -> bool:
        error_name = type(error).__name__
        non_retryable = [
            "DataHubAuthError",
            "ValueError",
            "TypeError",
            "KeyError",
            "DataHubMappingError",
        ]
        return error_name not in non_retryable

    async def delay(self, attempt: int) -> None:
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        await asyncio.sleep(delay)

    async def execute(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if not self.is_retryable(e):
                    raise
                if attempt < self.max_attempts:
                    await self.delay(attempt)
        if last_error:
            raise last_error
