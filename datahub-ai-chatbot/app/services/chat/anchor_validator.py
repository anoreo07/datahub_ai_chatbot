"""anchor_validator.py

AnchorValidator là cross-cutting concern chạy ở 3 điểm trong pipeline:
  1. Sau entity resolution -> validate search filters (E-DRIFT, E-MISS)
  2. Sau retrieval -> validate context có đúng entity không (Context Drift)
  3. Sau LLM generation -> validate answer không đề cập entity ngoài anchor (E-GHOST)

Đây là lớp phòng thủ chính chống lại E-DRIFT, E-MISS, và E-GHOST.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.services.chat.query_anchor import QueryAnchor

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    stage: str
    passed: bool = True
    error_code: str | None = None  # "E-DRIFT", "E-MISS", "E-GHOST", etc.
    error_detail: str = ""
    recommended_action: str = ""  # "warn_user", "abort_or_clarify", "retry_with_entity_filter"
    warnings: list[str] = field(default_factory=list)
    matched_entities: list[Any] = field(default_factory=list)
    drift_entities: list[Any] = field(default_factory=list)
    retrieved_urns: set[str] = field(default_factory=set)
    anchor_overlap_urns: set[str] = field(default_factory=set)
    ghost_entities: list[str] = field(default_factory=list)


class AnchorValidator:
    """Validator inspecting the data flow at three key pipeline checkpoints."""

    # ----------------------------------------------------------------
    # CHECKPOINT 1: Sau Entity Resolution
    # ----------------------------------------------------------------

    def validate_resolution(
        self,
        anchor: QueryAnchor,
        resolved_entities: list[Any],
    ) -> ValidationReport:
        """Kiểm tra entity resolution có consistent với anchor không."""
        report = ValidationReport(stage="entity_resolution")

        if anchor.is_free_query():
            report.passed = True
            return report

        anchor_mentions_lower = {
            m.lower()
            for m in [a.raw_mention for a in anchor.anchors]
            + [a.resolved_name for a in anchor.anchors if a.resolved_name]
        }

        if not resolved_entities:
            # Anchor có mention nhưng không resolve được -> E-MISS
            report.passed = False
            report.error_code = "E-MISS"
            report.error_detail = (
                f"Query mentions {[a.raw_mention for a in anchor.anchors]} "
                "but no entity was resolved. "
                "Retrieval will be unanchored -> high risk of E-DRIFT."
            )
            report.recommended_action = "warn_user_entity_not_found"
            logger.warning(f"[anchor_validator] E-MISS: {report.error_detail}")
            return report

        # Kiểm tra entity resolved có liên quan đến anchor không
        drift_entities: list[Any] = []
        matched_entities: list[Any] = []

        for entity in resolved_entities:
            entity_name = getattr(entity, "name", "") or ""
            entity_name_lower = entity_name.lower()
            entity_urn = getattr(entity, "urn", "") or ""

            # Check xem entity này có trong anchor URN không
            if entity_urn and entity_urn in anchor.anchor_urns:
                matched_entities.append(entity)
                continue

            # Check tên có overlap với anchor mention không
            name_overlap = any(
                anchor_m in entity_name_lower or entity_name_lower in anchor_m
                for anchor_m in anchor_mentions_lower
                if anchor_m
            )
            if name_overlap:
                matched_entities.append(entity)
                continue

            drift_entities.append(entity)

        if drift_entities and not matched_entities:
            # Tất cả resolved entities đều drift -> E-DRIFT nghiêm trọng
            report.passed = False
            report.error_code = "E-DRIFT"
            report.error_detail = (
                "All resolved entities are unrelated to anchor. "
                f"Anchor: {anchor.anchor_names}. "
                f"Resolved: {[getattr(e, 'name', str(e)) for e in drift_entities]}."
            )
            report.recommended_action = "abort_or_clarify"
            logger.error(f"[anchor_validator] E-DRIFT: {report.error_detail}")
        elif drift_entities:
            report.passed = True
            m_names = [getattr(e, "name", str(e)) for e in matched_entities]
            d_names = [getattr(e, "name", str(e)) for e in drift_entities]
            report.warnings.append(f"Mixed resolution: {m_names} matched, {d_names} unrelated.")
        else:

            report.passed = True

        report.matched_entities = matched_entities
        report.drift_entities = drift_entities
        return report

    # ----------------------------------------------------------------
    # CHECKPOINT 2: Sau Retrieval — Validate Context
    # ----------------------------------------------------------------

    def validate_context(
        self,
        anchor: QueryAnchor,
        search_results: list[Any],
        context_xml: str = "",
    ) -> ValidationReport:
        """Kiểm tra context được build có chứa entity từ anchor không."""
        report = ValidationReport(stage="context_assembly")

        if anchor.is_free_query():
            report.passed = True
            return report

        retrieved_urns = {
            getattr(r, "urn", None) or getattr(r, "entity_urn", None)
            for r in search_results
            if getattr(r, "urn", None) or getattr(r, "entity_urn", None)
        }
        retrieved_names = {
            (getattr(r, "name", None) or getattr(r, "entity_name", None) or "").lower()
            for r in search_results
            if getattr(r, "name", None) or getattr(r, "entity_name", None)
        }

        anchor_urns = anchor.anchor_urns
        anchor_names = anchor.anchor_names

        # URN overlap
        urn_overlap = retrieved_urns & anchor_urns

        # Name overlap
        name_overlap = {
            rn for rn in retrieved_names if any(an in rn or rn in an for an in anchor_names if an)
        }

        has_overlap = bool(urn_overlap or name_overlap)

        if not has_overlap and not anchor.is_free_query():
            report.passed = False
            report.error_code = "E-DRIFT"
            report.error_detail = (
                "Context contains ZERO entities related to anchor. "
                f"Anchor expects: {anchor.anchor_names}. "
                f"Context has: {list(retrieved_names)[:5]}. "
                "LLM will answer about wrong entity -> abort or retry retrieval."
            )
            report.recommended_action = "retry_with_entity_filter"
            logger.error(
                f"[anchor_validator] Context drift detected!\n"
                f"  Anchor: {anchor.anchor_names}\n"
                f"  Retrieved: {list(retrieved_names)[:5]}"
            )
        else:
            coverage = len(urn_overlap) / max(len(anchor_urns), 1)
            report.passed = True
            if coverage < 0.5 and anchor_urns:
                report.warnings.append(
                    f"Low anchor coverage in context: {coverage:.0%} of anchor entities present."
                )

        report.retrieved_urns = retrieved_urns
        report.anchor_overlap_urns = urn_overlap
        return report

    # ----------------------------------------------------------------
    # CHECKPOINT 3: Sau Generation — Validate Answer
    # ----------------------------------------------------------------

    def validate_answer(
        self,
        anchor: QueryAnchor,
        answer: str,
        citations: list[Any],
        resolved_entities: list[Any],
    ) -> ValidationReport:
        """Kiểm tra answer có consistent với anchor và citations không."""
        report = ValidationReport(stage="answer_generation")

        if anchor.is_free_query():
            report.passed = True
            return report

        ghost_entities = self._detect_ghost_entities(anchor, answer, resolved_entities)
        if ghost_entities:
            report.warnings.append(
                f"E-GHOST: Answer mentions entity names not in anchor or context: {ghost_entities}."
            )

        if citations:
            citation_drift = self._check_citation_drift(anchor, citations)
            if citation_drift:
                report.warnings.append(
                    f"Citations reference entities unrelated to anchor: {citation_drift}"
                )

        primary = anchor.primary_anchor
        if primary and primary.resolved_name:
            primary_name_lower = primary.resolved_name.lower()
            if primary_name_lower not in answer.lower():
                report.warnings.append(
                    f"Primary anchor entity '{primary.resolved_name}' not mentioned in answer."
                )

        report.passed = True
        report.ghost_entities = ghost_entities
        return report

    def _detect_ghost_entities(
        self,
        anchor: QueryAnchor,
        answer: str,
        context_entities: list[Any],
    ) -> list[str]:
        """Tìm entity names trong answer không có trong anchor hoặc context."""
        entity_pattern = r"\b((?:dim|fact|fct|stg|mart|rpt|agg|raw)_\w+)\b"
        answer_entities = set(re.findall(entity_pattern, answer, re.IGNORECASE))

        allowed = anchor.anchor_names.copy()
        for e in context_entities:
            ename = getattr(e, "name", None) or getattr(e, "entity_name", None)
            if ename:
                allowed.add(ename.lower())

        ghosts = [e for e in answer_entities if e.lower() not in allowed]
        return ghosts

    def _check_citation_drift(
        self,
        anchor: QueryAnchor,
        citations: list[Any],
    ) -> list[str]:
        """Check citations có refer đến entity không liên quan không."""
        anchor_names = anchor.anchor_names
        drift: list[str] = []
        for citation in citations:
            entity_name = getattr(citation, "entity_name", "") or ""
            entity_urn = getattr(citation, "entity_urn", "") or getattr(citation, "urn", "") or ""

            if entity_urn and entity_urn in anchor.anchor_urns:
                continue

            if any(
                an in entity_name.lower() or entity_name.lower() in an for an in anchor_names if an
            ):
                continue

            if entity_name:
                drift.append(entity_name)
        return drift
