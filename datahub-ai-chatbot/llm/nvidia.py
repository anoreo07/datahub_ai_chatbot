import json
from collections.abc import Awaitable, Callable

import structlog
from openai import AsyncOpenAI

from config.prompts import GUARDRAIL_RULES
from config.settings import settings
from llm.base import BaseLLM
from llm.fireworks import STREAM_SYSTEM_PROMPT

log = structlog.get_logger()

# A lighter JSON contract improves structured-answer parsing.
NVIDIA_SYSTEM_PROMPT = (
    "You are a DataHub metadata assistant for VinFast automotive manufacturing. "
    "You have metadata about datasets, dashboards, glossary terms, schema, "
    "ownership, and lineage - NOT actual business data.\n"
    "- Answer using ONLY the provided context. Cite sources with [E1], [E2], ...\n"
    "- If the context does not answer the question, say so in ONE short sentence "
    "and do NOT invent entities.\n"
    "- Never create entity names, URNs, owners, or URLs.\n"
    "- Respond in Vietnamese if the question is in Vietnamese.\n"
    "- Return ONLY a JSON object with this exact shape:\n"
    '{"answer": "...", "citation_ids": ["E1", "E2"], '
    '"confidence": "high|medium|low", "insufficient_context": false}\n\n'
    + GUARDRAIL_RULES
)


class NVIDIAProvider(BaseLLM):
    """NVIDIA NIM / NVCF OpenAI-compatible LLM provider."""

    def __init__(self) -> None:
        self._api_key = settings.NVIDIA_API_KEY
        self._base_url = settings.NVIDIA_BASE_URL.rstrip("/")
        self._model = settings.NVIDIA_MODEL_ID
        self._timeout = min(settings.LLM_TIMEOUT_SECONDS, 60)
        self._client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=1,
        )

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    @property
    def model_id(self) -> str:
        return self._model

    async def healthcheck(self) -> bool:
        if not self._api_key:
            return False
        try:
            await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        messages: list[dict[str, str | list[dict[str, str]]]] = [
            {"role": "system", "content": system_prompt or NVIDIA_SYSTEM_PROMPT}
        ]
        if history:
            for q, a in history:
                messages.append({"role": "user", "content": q})
                messages.append({"role": "assistant", "content": a})
        if context:
            messages.append({"role": "user", "content": "Context:\n" + "\n\n".join(context)})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    async def stream(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
        on_token: Callable[[str], Awaitable[None]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        messages: list[dict[str, str | list[dict[str, str]]]] = [
            {"role": "system", "content": system_prompt or STREAM_SYSTEM_PROMPT}
        ]
        if history:
            for q, a in history:
                messages.append({"role": "user", "content": q})
                messages.append({"role": "assistant", "content": a})
        if context:
            messages.append({"role": "user", "content": "Context:\n" + "\n\n".join(context)})
        messages.append({"role": "user", "content": prompt})

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            stream=True,
        )
        parts: list[str] = []
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = (chunk.choices[0].delta or {}).content or ""
            if not delta:
                continue
            parts.append(delta)
            if on_token is not None:
                await on_token(delta)
        return "".join(parts)

    async def generate_structured(self, prompt: str, context_xml: str = "",
                                  history: list[tuple[str, str]] | None = None) -> dict:
        ctx_list = [context_xml] if context_xml else None
        raw = await self.generate(prompt, context=ctx_list, history=history)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.warning("llm_json_parse_failed", raw=raw[:200])
            return {
                "answer": raw,
                "citation_ids": [],
                "confidence": "low",
                "insufficient_context": True,
            }
