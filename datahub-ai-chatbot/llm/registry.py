"""Model registry - exposes selectable LLM models to the chat UI."""

from dataclasses import dataclass

from config.settings import settings


@dataclass(frozen=True)
class ModelDef:
    id: str
    name: str
    provider: str


def available_models() -> list[ModelDef]:
    """Models the user can pick from the chat model selector."""
    models: list[ModelDef] = [
        ModelDef(
            id="deepseek-v4-flash",
            name="DeepSeek V4 Flash",
            provider="fireworks",
        ),
        ModelDef(
            id=settings.NVIDIA_MODEL_ID,
            name="Llama 3.3 70B (NVIDIA)",
            provider="nvidia",
        ),
    ]
    return models
