from llm.base import BaseLLM


class CohereLLM(BaseLLM):
    """Cohere LLM provider."""

    async def generate(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
    ) -> str:
        raise NotImplementedError("Cohere LLM is not implemented yet.")
