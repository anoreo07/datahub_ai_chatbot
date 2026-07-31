from llm.base import BaseLLM


class BedrockLLM(BaseLLM):
    """AWS Bedrock LLM provider."""

    async def generate(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
    ) -> str:
        raise NotImplementedError("Bedrock LLM is not implemented yet.")
