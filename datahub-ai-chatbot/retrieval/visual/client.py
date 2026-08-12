"""Vision model clients for the Visual Understanding layer.

A thin, independent client abstraction over the vision model (Qwen2.5-VL via the
Fireworks OpenAI-compatible endpoint). The real client sends the image as a
``data:`` URL content part and asks for a JSON object; a deterministic mock
client is used for tests / mock mode so no network or API key is required.
"""

from __future__ import annotations

import re
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings
from retrieval.visual.parser import parse_vision_json
from retrieval.visual.prompts import (
    VISION_SYSTEM_PROMPT,
    build_vision_prompt,
)

_DATA_URL_RE = re.compile(r"^data:([^;,]+)(;base64)?,(.+)$", re.DOTALL)


class VisionClientError(Exception):
    pass


class VisionClient:
    """Abstract vision client: analyze(data_url, image_text_hint) -> dict."""

    async def analyze(self, data_url: str, image_text_hint: str = "") -> dict[str, Any]:
        raise NotImplementedError  # pragma: no cover


class FireworksVisionClient(VisionClient):
    """Calls Qwen2.5-VL-72B-Instruct through the Fireworks OpenAI-compatible API."""

    def __init__(self) -> None:
        self._api_key = settings.FIREWORKS_API_KEY
        self._model = settings.FIREWORKS_VISION_MODEL_ID
        self._client = AsyncOpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self._api_key,
            timeout=settings.VISION_TIMEOUT_SECONDS,
            max_retries=0,
        )

    async def analyze(self, data_url: str, image_text_hint: str = "") -> dict[str, Any]:
        content: list[dict[str, Any]] = [
            {"type": "image_url", "image_url": {"url": data_url}},
            {"type": "text", "text": build_vision_prompt(image_text_hint)},
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
        response = await self._client.chat.completions.create(  # type: ignore[call-overload]
            model=self._model,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        parsed = parse_vision_json(raw)
        return parsed


class MockVisionClient(VisionClient):
    """Deterministic vision client used in mock mode / tests (no network)."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self._response = response
        self.calls: list[str] = []

    async def analyze(self, data_url: str, image_text_hint: str = "") -> dict[str, Any]:
        self.calls.append(data_url)
        return self.response_for(data_url)

    def response_for(self, data_url: str) -> dict[str, Any]:
        if self._response is not None:
            return dict(self._response)
        # Heuristic-free deterministic default: signal a generic data-related
        # image so lower layers can still run in mock mode without over-inferring.
        return {
            "image_type": "dashboard",
            "quality": "clear",
            "ocr_text": data_url[:80],
            "detected_entities": [],
            "detected_metrics": [],
            "detected_tables": [],
            "detected_columns": [],
            "detected_relationships": [],
            "detected_errors": [],
            "detected_questions": [],
            "confidence": 0.0,
            "recommended_skills": [],
            "irrelevant": False,
            "notes": ["mock vision mode"],
            "candidates": [],
        }


def create_vision_client(
    mock: bool | None = None, response: dict[str, Any] | None = None
) -> VisionClient:
    """Factory: use the mock client in mock mode / tests, else the real one."""
    use_mock = bool(settings.USE_MOCK_VISION) if mock is None else mock
    if use_mock or settings.USE_MOCK_LLM or not settings.FIREWORKS_API_KEY:
        return MockVisionClient(response=response)
    return FireworksVisionClient()


def parse_data_url(data_url: str) -> tuple[str, str]:
    """Split a ``data:`` URL into (mime_type, base64_payload)."""
    m = _DATA_URL_RE.match(data_url or "")
    if not m:
        return "", ""
    return m.group(1), m.group(3)
