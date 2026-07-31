from config.settings import settings
from llm.base import BaseLLM


def create_llm_client() -> BaseLLM:
    if settings.USE_MOCK_LLM:
        from llm.mock import MockLLM
        return MockLLM()
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        from llm.openai import OpenAILLM
        return OpenAILLM()
    elif provider == "bedrock":
        from llm.bedrock import BedrockLLM
        return BedrockLLM()
    elif provider == "cohere":
        from llm.cohere import CohereLLM
        return CohereLLM()
    elif provider == "fireworks":
        from llm.fireworks import FireworksLLM
        return FireworksLLM()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
