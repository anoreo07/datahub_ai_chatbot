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
class SubQuestionConstraint:
    """Routing constraints attached to one decomposed sub-question."""

    context_only: bool = False
    output_format_constraint: str | None = None


@dataclass
class SubQuestionEntityRef:
    """How a decomposed sub-question points at its target entity."""

    explicit_name: str | None = None
    anaphora_target: str | None = None


@dataclass
class SubQuestion:
    """A concrete, self-contained sub-question the LLM reads off the question.

    Carries the routing-relevant fields the pipeline needs to answer it without
    re-architecting the whole plan: the intent it contributes, the entity it
    targets (explicit name or conversation anaphora), the field/property pair,
    the routing constraints, and whether answering it requires checking that the
    current evidence is actually grounded in the entity's real schema.
    """

    question: str = ""
    intent: str | None = None
    entity_ref: SubQuestionEntityRef | None = None
    field_ref: str | None = None
    property: str | None = None
    constraint: SubQuestionConstraint = field(default_factory=SubQuestionConstraint)
    evidence_quality_check_needed: bool = False


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
    complexity_reason: str | None = None
    parse_confidence: str = "medium"
    sub_question_details: list[SubQuestion] = field(default_factory=list)

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
            "complexity_reason": self.complexity_reason,
            "parse_confidence": self.parse_confidence,
            "sub_question_details": [
                {
                    "question": sq.question,
                    "intent": sq.intent,
                    "entity_ref": {
                        "explicit_name": (
                            sq.entity_ref.explicit_name if sq.entity_ref else None
                        ),
                        "anaphora_target": (
                            sq.entity_ref.anaphora_target if sq.entity_ref else None
                        ),
                    } if sq.entity_ref else None,
                    "field_ref": sq.field_ref,
                    "property": sq.property,
                    "constraint": {
                        "context_only": sq.constraint.context_only,
                        "output_format_constraint": (
                            sq.constraint.output_format_constraint
                            if sq.constraint.output_format_constraint else None
                        ),
                    },
                    "evidence_quality_check_needed": sq.evidence_quality_check_needed,
                }
                for sq in self.sub_question_details
            ],
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


def _parse_sub_questions(raw: object) -> list[tuple[str, SubQuestion]]:
    """Parse the new structured ``sub_questions`` schema.

    The old schema used a plain list of strings; the new one uses a list of
    objects. Both are tolerated: a string entry degrades gracefully to
    ``SubQuestion(question=str)`` so callers that read plain text keep working.
    Returns ``(text, detail)`` pairs.
    """
    if not isinstance(raw, list):
        return []
    out: list[tuple[str, SubQuestion]] = []
    for item in raw[:8]:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append((text, SubQuestion(question=text)))
            continue
        if not isinstance(item, dict):
            continue
        text = _clean_str(item.get("question")) or ""
        if not text:
            continue
        entity = item.get("entity_ref")
        entity_ref: SubQuestionEntityRef | None = None
        if isinstance(entity, dict):
            entity_ref = SubQuestionEntityRef(
                explicit_name=_clean_str(entity.get("explicit_name")),
                anaphora_target=_clean_str(entity.get("anaphora_target")),
            )
        elif isinstance(entity, str):
            entity_ref = SubQuestionEntityRef(explicit_name=entity.strip() or None)
        constraint_raw = item.get("constraint")
        constraint = SubQuestionConstraint()
        if isinstance(constraint_raw, dict):
            constraint.context_only = _flag(constraint_raw.get("context_only"))
            constraint.output_format_constraint = _clean_str(
                constraint_raw.get("output_format_constraint"), limit=256
            )
        elif isinstance(constraint_raw, bool):
            constraint.context_only = constraint_raw
        prop = _clean_str(item.get("property"))
        if prop:
            prop = prop.strip().lower()
            if not (_VALID_PROPERTY_PATTERN.match(prop) and prop in VALID_PROPERTIES):
                prop = None
        detail = SubQuestion(
            question=text,
            intent=_clean_str(item.get("intent"), limit=64),
            entity_ref=entity_ref,
            field_ref=_clean_str(item.get("field_ref"), limit=256),
            property=prop,
            constraint=constraint,
            evidence_quality_check_needed=_flag(
                item.get("evidence_quality_check_needed")
            ),
        )
        out.append((text, detail))
    return out


def parse_understanding(raw: str) -> UnderstandingResult | None:
    """Build an ``UnderstandingResult`` from the LLM's raw JSON payload.

    Returns ``None`` when the payload is missing or structurally unusable, so
    callers keep the pre-QU behaviour.
    """
    data = _first_json(raw)
    if not isinstance(data, dict):
        return None

    sub_pairs = _parse_sub_questions(data.get("sub_questions"))
    sub_texts = [t for t, _d in sub_pairs]
    sub_details = [d for _t, d in sub_pairs]
    needs_decomposition = _flag(data.get("needs_decomposition")) or bool(sub_details)

    result = UnderstandingResult(
        focus_field=_clean_str(data.get("focus_field")),
        is_field_property_question=_flag(data.get("is_field_property_question")),
        needs_thinking=_flag(data.get("needs_thinking")),
        needs_decomposition=needs_decomposition,
        sub_questions=sub_texts,
        anaphora_target=_clean_str(data.get("anaphora_target")),
        entity_refs=_clean_str_list(data.get("entity_refs")),
        confidence=_conf(data.get("confidence")),
        source="llm",
        complexity_reason=_clean_str(data.get("complexity_reason"), limit=256),
        parse_confidence=_conf(data.get("parse_confidence")),
        sub_question_details=sub_details,
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


def _format_context_inputs(
    evidence: list[dict[str, object]] | None,
    active_entity: str | None,
    field_names: list[str] | None,
    catalog_names: list[str] | None,
) -> str:
    """Build the grounding block (evidence / active entity / known field names /
    known catalog names) fed to the LLM so its structured output can be checked
    against real schema when it flows through the Validator."""
    blocks: list[str] = []
    if active_entity:
        blocks.append(f"Active entity: {active_entity[:160]}")
    if field_names:
        listed = ", ".join((f or "").strip() for f in field_names[:60] if f)
        blocks.append(f"Known schema fields of the active entity: {listed[:1200]}")
    if catalog_names:
        listed = ", ".join((n or "").strip() for n in catalog_names[:120] if n)
        blocks.append(f"Known catalog entities: {listed[:2000]}")
    if evidence:
        ev_lines: list[str] = []
        for ev in evidence[-6:]:
            ev_id = str(ev.get("evidence_id") or "?")[:8]
            ent = str(ev.get("entity_name") or "")[:80]
            kind = str(ev.get("kind") or "")[:20]
            ev_lines.append(f"- {ev_id} [{kind}] entity={ent}")
        if ev_lines:
            blocks.append("Conversation evidence (already fetched):\n" + "\n".join(ev_lines))
    return "\n".join(blocks or ["(no checklist context)"])


async def understand_query(
    question: str,
    llm: BaseLLM,
    history: list[tuple[str, str]] | None = None,
    *,
    evidence: list[dict[str, object]] | None = None,
    active_entity: str | None = None,
    field_names: list[str] | None = None,
    catalog_names: list[str] | None = None,
) -> UnderstandingResult | None:
    """Read ``question`` into a structured ``UnderstandingResult``.

    Returns ``None`` when QU is disabled, the provider is fake, the LLM call
    fails, or the payload is unusable — every caller then keeps its existing
    behaviour. When provided, ``evidence`` / ``active_entity`` / ``field_names``
    / ``catalog_names`` are exposed as grounding context in the prompt (the
    Validator then checks every structured claim against them).
    """
    if not settings.QU_ENABLED or settings.USE_MOCK_LLM:
        return None

    try:
        context_block = _format_context_inputs(
            evidence, active_entity, field_names, catalog_names,
        )
        system_prompt = QUERY_UNDERSTANDING_PROMPT.replace(
            "[HISTORY]", _format_history(history) if history else "(no prior conversation)",
        ).replace("[QUESTION]", question[:2000]).replace(
            "[CHECKLIST_CONTEXT]", context_block,
        )
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
