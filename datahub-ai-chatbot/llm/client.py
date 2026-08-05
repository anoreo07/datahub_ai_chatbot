from config.settings import settings
from llm.base import BaseLLM


def create_llm_client(provider: str | None = None) -> BaseLLM:
    """Create an LLM client for ``provider`` (default: settings.LLM_PROVIDER).

    ``provider`` is one of "fireworks", "nvidia", "openai", "bedrock", "cohere",
    or a full model id like "meta/llama-3.3-70b-instruct" (mapped to the
    provider that serves it). Pass None to use the configured default.
    """
    if settings.USE_MOCK_LLM:
        from llm.mock import MockLLM
        return MockLLM()

    resolved = resolve_provider(provider or settings.LLM_PROVIDER)

    if resolved == "nvidia":
        from llm.nvidia import NVIDIAProvider
        return NVIDIAProvider()
    if resolved == "openai":
        from llm.openai import OpenAILLM
        return OpenAILLM()
    if resolved == "bedrock":
        from llm.bedrock import BedrockLLM
        return BedrockLLM()
    if resolved == "cohere":
        from llm.cohere import CohereLLM
        return CohereLLM()
    if resolved == "fireworks":
        from llm.fireworks import FireworksLLM
        return FireworksLLM()
    raise ValueError(f"Unsupported LLM provider: {resolved}")


def resolve_provider(model_or_provider: str) -> str:
    """Map a model id or provider name to a provider key.

    Known NVIDIA model ids resolve to "nvidia"; provider names pass through.
    """
    name = (model_or_provider or "").strip().lower()
    if name in {"nvidia", "nvcf", "nim"}:
        return "nvidia"
    if name in {"fireworks", "openai", "bedrock", "cohere"}:
        return name
    if model_or_provider and "/" in model_or_provider:
        # A full model id like "meta/llama-3.3-70b-instruct" - assume
        # NVIDIA NIM/NVCF unless it is a known Fireworks model.
        if model_or_provider.startswith("accounts/fireworks"):
            return "fireworks"
        return "nvidia"
    return (settings.LLM_PROVIDER or "fireworks").lower()
