"""Validator / Guardrail for the Query Understanding contract.

Every structured claim in an ``UnderstandingResult`` is advice, never an order.
This module checks those claims against ground truth the system actually has:

* **Schema grounding** — ``field_ref`` (and ``focus_field``) must resolve to a
  real column of the active dataset's ``schema_fields`` (exact-name lookup,
  case/diacritic-tolerant). An invented column is dropped, not forwarded.
* **Entity grounding** — ``entity_ref.explicit_name`` / ``anaphora_target`` must
  resolve to a real catalog entity from the supplied name index (exact-match
  lookup, independent of any intent heuristic). Unresolvable names are dropped.
* **Evidence-quality check** — when a sub-question sets
  ``evidence_quality_check_needed`` but the conversation has no evidence for the
  active entity, answering from "context" is unsafe; the answer must come from a
  fresh, grounded retrieval instead.
* **Confidence gating** — a low-``parse_confidence`` claim that names a field or
  entity it did not ground is not trusted for routing.

Every check is logged under ``validator_check`` with its verdict. Nothing here
mutates state; it returns a ``ValidationResult`` the caller merges into routing.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import structlog

from retrieval.query_understanding import SubQuestion, UnderstandingResult

log = structlog.get_logger()


class ConversationMemory(Protocol):
    def get_evidence(self, user_id: str, conversation_id: str) -> list[dict[str, object]]: ...


class NamedEntity(Protocol):
    display_name: str | None
    name: str | None
    payload: dict[str, object] | None


class EntityRepository(Protocol):
    async def search_by_name(
        self, name: str, entity_type: str | None = None,
    ) -> Sequence[NamedEntity]: ...

    async def list_all(
        self, entity_type: str | None = None, limit: int = 500,
    ) -> Sequence[NamedEntity]: ...


@dataclass
class GroundingContext:
    """Everything the QU layer + Validator need to ground a question.

    ``evidence`` is the conversation's recent structured extracts (E1...),
    ``active_entity`` the conversation's canonical subject, ``field_names`` the
    active dataset's real schema columns (ground truth for schema checks) and
    ``catalog_names`` the resolvable entity names (ground truth for entity
    checks). ``has_evidence_for_active`` tells the evidence-quality check whether
    the conversation actually holds metadata for the active entity.
    """

    evidence: list[dict[str, object]] = field(default_factory=list)
    active_entity: str | None = None
    field_names: list[str] = field(default_factory=list)
    catalog_names: list[str] = field(default_factory=list)
    has_evidence_for_active: bool = False


async def build_grounding_context(
    memory: ConversationMemory,
    entity_repo: EntityRepository,
    user_id: str,
    conversation_id: str,
    active_entities: list[dict[str, object]] | None = None,
    trace_id: str | None = None,
) -> GroundingContext:
    """Assemble the grounding facts for one question from the conversation.

    Evidence is pulled from the conversation store; the active entity is the
    first active entity the conversation last talked about; its schema fields
    come from the resolved dataset's stored ``schema_fields``; catalog names are
    drawn from the entity repository (bounded, so a large catalog stays cheap).
    All of it is best-effort: any failure degrades the block to an empty context,
    and the Validator then grounds nothing (regex fallback keeps routing).
    """
    evidence: list[dict[str, object]] = []
    try:
        evidence = list(memory.get_evidence(user_id, conversation_id) or [])
    except Exception:  # noqa: BLE001
        log.warning("grounding_evidence_failed", trace_id=trace_id)

    active_name: str | None = None
    for e in active_entities or []:
        name = str((e or {}).get("name") or "").strip()
        if name:
            active_name = name
            break

    field_names: list[str] = []
    if active_name:
        for ev in evidence:
            if str(ev.get("entity_name") or "").strip().lower() == active_name.lower():
                structured = (ev.get("structured") or {})
                fields = structured.get("fields") if isinstance(structured, dict) else None
                if isinstance(fields, list):
                    field_names = [
                        str(f).strip() for f in fields
                        if isinstance(f, str) and f.strip()
                    ]
                    break
        if not field_names:
            try:
                repo_entity = await entity_repo.search_by_name(active_name, "dataset")
                for ent in repo_entity or []:
                    payload = getattr(ent, "payload", None) or {}
                    fields = payload.get("schema_fields") or []
                    if fields:
                        field_names = [
                            (f.get("name") or "").strip()
                            for f in fields if (f.get("name") or "").strip()
                        ]
                        break
            except Exception:  # noqa: BLE001
                log.warning("grounding_schema_failed", trace_id=trace_id)

    catalog_names: list[str] = []
    try:
        entities = await entity_repo.list_all(limit=400)
        for ent in entities or []:
            display = getattr(ent, "display_name", None) or getattr(ent, "name", None)
            if display:
                catalog_names.append(str(display))
    except Exception:  # noqa: BLE001
        log.warning("grounding_catalog_failed", trace_id=trace_id)
    catalog_names = list(dict.fromkeys(n for n in catalog_names if n))
    if active_name:
        catalog_names.append(active_name)

    has_active = False
    if active_name:
        for ev in evidence:
            if str(ev.get("entity_name") or "").strip().lower() == active_name.lower():
                has_active = True
                break

    return GroundingContext(
        evidence=evidence,
        active_entity=active_name,
        field_names=field_names,
        catalog_names=catalog_names[:500],
        has_evidence_for_active=has_active,
    )


def _norm(text: str) -> str:
    """Lowercase + NFKD fold so exact-name matching ignores case & diacritics."""
    return (
        unicodedata.normalize("NFKD", (text or "").strip().lower())
        .encode("ascii", "ignore").decode("ascii")
    )


def exact_name_index(names: list[str] | None) -> dict[str, str]:
    """Build ``{normalized: original}`` from a list of known names.

    This is the decoupled exact-name catalog lookup: a pure, intent-independent
    index that the Validator (and callers) use to ground entity *names* before
    anything routes on intent. It answers ``exact`` only; fuzzy/typo resolution
    stays where it already lives (entity resolver / fuzzy module).
    """
    index: dict[str, str] = {}
    for name in names or []:
        key = _norm(name)
        if key and key not in index:
            index[key] = name
    return index


def resolve_exact(
    name: str | None,
    index: dict[str, str],
) -> str | None:
    """Resolve ``name`` to a canonical known name via the exact-name index."""
    if not name:
        return None
    key = _norm(name)
    if not key:
        return None
    return index.get(key)


def field_exists(name: str | None, schema_fields: list[str] | None) -> bool:
    if not name:
        return False
    key = _norm(name)
    if not key:
        return False
    return any(_norm(f or "") == key for f in (schema_fields or []))


@dataclass
class ValidationResult:
    """Verdict of the guardrail over one ``UnderstandingResult``."""

    grounded: bool = True
    overall_parse_confidence: str = "medium"
    trusted_field: str | None = None
    trusted_entity: str | None = None
    trusted_anaphora_target: str | None = None
    embargoed_sub_questions: list[str] = field(default_factory=list)
    evidence_insufficient: bool = False
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "grounded": self.grounded,
            "overall_parse_confidence": self.overall_parse_confidence,
            "trusted_field": self.trusted_field,
            "trusted_entity": self.trusted_entity,
            "trusted_anaphora_target": self.trusted_anaphora_target,
            "embargoed_sub_questions": self.embargoed_sub_questions,
            "evidence_insufficient": self.evidence_insufficient,
            "reasons": self.reasons,
        }


def validate_understanding(
    understanding: UnderstandingResult,
    *,
    schema_fields: list[str] | None = None,
    catalog_names: list[str] | None = None,
    active_entity: str | None = None,
    entity_type: str | None = None,
    has_evidence_for_active: bool = False,
    trace_id: str | None = None,
) -> ValidationResult:
    """Guardrail over a parsed understanding contract.

    The contract is only trusted for routing when it survives this check:
    field/entity claims must resolve against real schema and catalog names, and
    evidence-quality flags must not contradict what the conversation actually
    holds. Verdicts are logged under ``validator_check`` per check.
    """
    result = ValidationResult(
        overall_parse_confidence=understanding.parse_confidence or "medium",
    )
    checks: list[str] = []

    def _check(name: str, ok: bool, detail: str = "") -> None:
        checks.append(name)
        log.info(
            "validator_check",
            trace_id=trace_id,
            check=name,
            ok=ok,
            parse_confidence=understanding.parse_confidence,
            detail=detail[:200],
        )

    # 1. Schema grounding of the focus field (if the contract names one).
    focus = understanding.focus_field
    schema_pool = schema_fields or []
    if focus:
        if field_exists(focus, schema_pool):
            result.trusted_field = focus
            _check("field_grounding", True, f"field={focus!r}")
        else:
            # The field is not in the active dataset's schema: the claim is
            # either wrong or refers to a different entity. Drop the signal so a
            # hallucinated column never drives routing.
            result.trusted_field = None
            result.reasons.append(f"field not grounded: {focus!r}")
            _check("field_grounding", False, f"field={focus!r}")

    # 2. Entity grounding of explicit names / anaphora target.
    index = exact_name_index(catalog_names)
    pool_has_active = bool(active_entity and resolve_exact(active_entity, index))

    explicit = understanding.entity_refs or []
    for sub in understanding.sub_question_details:
        ref = sub.entity_ref
        if ref and ref.explicit_name and ref.explicit_name not in explicit:
            explicit.append(ref.explicit_name)

    trusted_entity: list[str] = []
    for name in explicit:
        resolved = resolve_exact(name, index)
        if resolved is not None:
            trusted_entity.append(resolved)
        else:
            result.reasons.append(f"entity not grounded: {name!r}")
    if trusted_entity:
        result.trusted_entity = trusted_entity[0]

    anaphora = understanding.anaphora_target
    if anaphora:
        resolved = resolve_exact(anaphora, index)
        if resolved is not None:
            result.trusted_anaphora_target = resolved
            _check("anaphora_grounding", True, f"anaphora={anaphora!r}")
        else:
            result.trusted_anaphora_target = None
            result.reasons.append(f"anaphora not grounded: {anaphora!r}")
            _check("anaphora_grounding", False, f"anaphora={anaphora!r}")
    else:
        _check("anaphora_grounding", True, "no anaphora present")

    # 3. Entity grounding per sub-question detail.
    for sub in understanding.sub_question_details:
        ref = sub.entity_ref
        if sub.field_ref and not field_exists(sub.field_ref, schema_pool):
            result.embargoed_sub_questions.append(sub.question)
            result.reasons.append(
                f"sub-question field not grounded: {sub.field_ref!r}"
            )
            _check("sub_question_field_grounding", False,
                   f"field={sub.field_ref!r} question={sub.question[:60]!r}")
        sub_entity = ref.explicit_name if ref else None
        if sub_entity and resolve_exact(sub_entity, index) is None:
            result.embargoed_sub_questions.append(sub.question)
            result.reasons.append(f"sub-question entity not grounded: {sub_entity!r}")
            _check("sub_question_entity_grounding", False,
                   f"entity={sub_entity!r}")

    # 4. Evidence-quality check: a sub-question that demands verifying the
    #    current evidence is grounded in a real schema field must not be answered
    #    purely from context when the conversation holds no such evidence.
    if any(sq.evidence_quality_check_needed for sq in understanding.sub_question_details):
        # An empty active-entity evidence store or an ungrounded active entity
        # means the claimed field-level answer would be unfounded.
        insufficient = not has_evidence_for_active or not pool_has_active
        result.evidence_insufficient = insufficient
        _check(
            "evidence_quality",
            not insufficient,
            f"has_evidence_for_active={has_evidence_for_active}, "
            f"active_grounded={pool_has_active}",
        )

    # 5. Confidence gate: a low-confidence parse that named a field/entity it did
    #    not ground must not drive routing. We keep the grounded signals but drop
    #    the ungrounded ones (already reflected in trusted_*).
    if understanding.parse_confidence == "low" and (
        understanding.focus_field or understanding.property
    ) and result.trusted_field is None:
        result.reasons.append("low confidence + ungrounded field claim dropped")
        _check("confidence_gate", False, "low confidence ungrounded field")

    result.grounded = not any("not grounded" in r for r in result.reasons)
    # Trim duplication for stable logs.
    result.reasons = list(dict.fromkeys(result.reasons))
    return result


def apply_validation(
    understanding: UnderstandingResult,
    validation: ValidationResult | None,
) -> UnderstandingResult:
    """Merge the guardrail verdict into the contract routers consume.

    Returns a copy of ``understanding`` whose ungrounded signals are dropped
    (focus_field / property cleared, sub-questions embargoed), leaving the
    original untouched so the raw QU+Validator telemetry stays comparable.
    """
    if validation is None:
        return understanding

    import copy

    result = copy.deepcopy(understanding)

    if validation.trusted_field is None and (
        result.focus_field or result.property
    ):
        # The LLM claimed a field/property that the schema check could not ground.
        result.focus_field = None
        result.property = None
        result.is_field_property_question = False

    embargoed = set(validation.embargoed_sub_questions)
    if embargoed:
        kept_text: list[str] = []
        kept_details: list[SubQuestion] = []
        for text, detail in zip(result.sub_questions, result.sub_question_details):
            if text in embargoed or detail.question in embargoed:
                continue
            kept_text.append(text)
            kept_details.append(detail)
        result.sub_questions = kept_text
        result.sub_question_details = kept_details
        result.needs_decomposition = bool(kept_details)

    return result
