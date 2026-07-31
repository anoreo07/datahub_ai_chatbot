"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        raise NotImplementedError("Subclasses must implement generate method.")

    async def generate_structured(self, prompt: str, context_xml: str = "",
                                  history: list[tuple[str, str]] | None = None) -> dict[str, Any]:
        raw = await self.generate(prompt, context=[context_xml] if context_xml else None, history=history)
        return {"answer": raw, "citation_ids": [], "confidence": "low", "insufficient_context": True}

    async def healthcheck(self) -> bool:
        """Verify the LLM provider is reachable and the API key is valid."""
        return True
