"""Query Understanding: an optional LLM layer over the question router.

The keyword/regex pipeline in ``intent_resolver`` reads a question into an
intent + entity hint, but it is blind to several signals that an LLM reads
reliably:

* an exact *field + property* pair even when the field name is not snake_case
  ("quantity có kiểu dữ liệu gì?"),
* *thinking* needs (compare / impact / multi-hop / system-level) that the
  complexity gate under-detects,
* *decomposition* needs (several independent sub-questions),
* the *anaphora target* for follow-ups ("nó", "đó", "bảng này") when the
  conversation context establishes the subject.

This module turns the question (+ conversation history) into that structured
JSON contract. It is **opt-in** via ``settings.QU_ENABLED``: when disabled (the
default) every public function returns ``None`` so the existing pipeline runs
byte-for-byte unchanged (regression-protected). On LLM failure the fallback is
also ``None`` — the router simply keeps its current heuristic behaviour.

Design constraints (mirroring ``retrieval/classifier.py``):
* The contract is "advice", never an order: each caller applies it only where
  the existing handler already covers that question shape.
* Fields are validated and sanitised before use; an unparsable / low-confidence
  payload degrades to ``None`` instead of hard-failing.
* No entity names are ever invented: ``entity_refs`` only echoes what the user
  wrote and ``anaphora_target`` must come from the conversation context.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import structlog

from config.prompts import QUERY_UNDERSTANDING_PROMPT
from config.settings import settings
from llm.base import BaseLLM

log = structlog.get_logger()

# Properties the downstream field-operation handler understands. Anything else
# the LLM emits is dropped (the handler falls back to its own detection).
VALID_PROPERTIES = {
    "data_type", "native_data_type", "description", "nullable",
    "is_primary_key", "glossary", "tags",
}

_VALID_PROPERTY_PATTERN = re.compile(
    r"^(?:data_type|native_data_type|description|nullable|"
    r"is_primary_key|glossary|tags)$",
    re.I,
)


@dataclass
class UnderstandingResult:
    """The structured read of one user question."""

    focus_field: str | None = None
    property: str | None = None
    is_field_property_question: bool = False
    needs_thinking: bool = False
    needs_decomposition: bool = False
    sub_questions: list[str] = field(default_factory=list)
    anaphora_target: str | None = None
    entity_refs: list[str] = field(default_factory=list)
    confidence: str = "medium"
    source: str = "llm"

    def to_dict(self) -> dict[str, object]:
        return {
            "focus_field": self.focus_field,
            "property": self.property,
            "is_field_property_question": self.is_field_property_question,
            "needs_thinking": self.needs_thinking,
            "needs_decomposition": self.needs_decomposition,
            "sub_questions": self.sub_questions,
            "anaphora_target": self.anaphora_target,
            "entity_refs": self.entity_refs,
            "confidence": self.confidence,
            "source": self.source,
        }


def _first_json(raw: str) -> object:
    """Extract the first JSON object from ``raw`` (fences and prose tolerated)."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    candidate = json.loads(cleaned[start:i + 1])
                    if isinstance(candidate, dict):
                        return candidate
                except json.JSONDecodeError:
                    pass
                break
    return None


def _clean_str(value: object, limit: int = 256) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text[:limit]


def _clean_str_list(value: object, limit: int = 8) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for item in value or []:
        if len(out) >= limit:
            break
        if isinstance(item, str) and item.strip():
            out.append(item.strip()[:512])
    return out


def _flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _conf(value: object) -> str:
    text = (str(value or "").strip().lower() if value is not None else "")
    return text if text in ("high", "medium", "low") else "medium"


def parse_understanding(raw: str) -> UnderstandingResult | None:
    """Build an ``UnderstandingResult`` from the LLM's raw JSON payload.

    Returns ``None`` when the payload is missing or structurally unusable, so
    callers keep the pre-QU behaviour.
    """
    data = _first_json(raw)
    if not isinstance(data, dict):
        return None

    result = UnderstandingResult(
        focus_field=_clean_str(data.get("focus_field")),
        is_field_property_question=_flag(data.get("is_field_property_question")),
        needs_thinking=_flag(data.get("needs_thinking")),
        needs_decomposition=_flag(data.get("needs_decomposition")),
        sub_questions=_clean_str_list(data.get("sub_questions")),
        anaphora_target=_clean_str(data.get("anaphora_target")),
        entity_refs=_clean_str_list(data.get("entity_refs")),
        confidence=_conf(data.get("confidence")),
        source="llm",
    )

    prop = _clean_str(data.get("property"))
    if prop:
        prop = prop.strip().lower()
        if _VALID_PROPERTY_PATTERN.match(prop) and prop in VALID_PROPERTIES:
            result.property = prop

    # A field-property question must name (or at least carry) a property and a
    # focus field. Otherwise it cannot be routed as one.
    if result.is_field_property_question and result.property is None:
        result.is_field_property_question = False
        result.property = None
    if result.is_field_property_question and result.focus_field is None:
        result.is_field_property_question = False

    return result


def _format_history(history: list[tuple[str, str]] | None, limit: int = 6) -> str:
    if not history:
        return "(no prior conversation)"
    lines: list[str] = []
    for question, answer in history[-limit:]:
        q = (question or "")[:200]
        a = (answer or "")[:300].replace("\n", " ")
        lines.append(f"- user: {q}\n  assistant: {a}")
    return "\n".join(lines)


async def understand_query(
    question: str,
    llm: BaseLLM,
    history: list[tuple[str, str]] | None = None,
) -> UnderstandingResult | None:
    """Read ``question`` into a structured ``UnderstandingResult``.

    Returns ``None`` when QU is disabled, the provider is fake, the LLM call
    fails, or the payload is unusable — every caller then keeps its existing
    behaviour.
    """
    if not settings.QU_ENABLED or settings.USE_MOCK_LLM:
        return None

    try:
        system_prompt = QUERY_UNDERSTANDING_PROMPT.replace(
            "[HISTORY]", _format_history(history) if history else "(no prior conversation)",
        ).replace("[QUESTION]", question[:2000])
        raw = await llm.generate(
            question,
            history=history,
            system_prompt=system_prompt,
        )
    except Exception:  # noqa: BLE001
        log.exception("query_understanding_failed", question=question[:120])
        log.info("query_understanding_fallback", question=question[:120],
                 reason="llm_failure")
        return None

    result = parse_understanding(raw)
    if result is None:
        log.info("query_understanding_fallback", question=question[:120],
                 reason="unparsable_payload", raw=raw[:200])
        return None

    # Low-confidence payloads carry no signal the router can trust.
    if result.confidence == "low" and not (
        result.is_field_property_question or result.needs_thinking
        or result.needs_decomposition or result.anaphora_target
    ):
        log.info("query_understanding_fallback", question=question[:120],
                 reason="low_confidence_redundant")
        return None

    return result