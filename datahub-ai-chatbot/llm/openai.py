from llm.base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI LLM provider."""

    async def generate(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
    ) -> str:
        raise NotImplementedError("OpenAI LLM is not implemented yet.")
