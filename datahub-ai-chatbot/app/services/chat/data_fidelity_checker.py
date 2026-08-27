"""data_fidelity_checker.py

Responsibility: So sánh answer của LLM với ground truth từ DB
để phát hiện contradiction (E-CONTRA) và confabulation (E-CONFABU).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.services.chat.query_anchor import QueryAnchor

logger = logging.getLogger(__name__)


@dataclass
class FidelityViolation:
    violation_type: str  # "E-CONTRA", "E-CONFABU", "E-SWAP"
    field: str  # Trường bị sai: "lineage", "owner", "schema", etc.
    db_value: str  # Giá trị thực tế trong DB
    answer_claim: str  # Cái LLM nói
    severity: str = "warning"  # "critical", "warning", "info"
    correction_text: str = ""  # Text sửa lỗi để append vào answer


@dataclass
class FidelityReport:
    passed: bool = True
    violations: list[FidelityViolation] = field(default_factory=list)
    corrected_answer: str | None = None


class DataFidelityChecker:
    """Checks thực hiện per-intent để đảm bảo câu trả lời trung thực với DB."""

    def __init__(self, entity_repository: Any) -> None:
        self.entity_repo = entity_repository

    async def check(
        self,
        anchor: QueryAnchor,
        intent: str,
        answer: str,
        resolved_entities: list[Any],
    ) -> FidelityReport:
        """Main entry point. Chạy checks phù hợp với intent."""
        report = FidelityReport(passed=True, violations=[])
        if anchor.is_free_query() or not resolved_entities:
            return report

        primary_entity = resolved_entities[0]
        if intent in ("LINEAGE", "IMPACT"):
            await self._check_lineage_fidelity(primary_entity, answer, report)
        elif intent == "SCHEMA_LOOKUP":
            await self._check_schema_fidelity(primary_entity, answer, report)
        elif intent == "OWNER_LOOKUP":
            await self._check_owner_fidelity(primary_entity, answer, report)
        elif intent in ("DATASET_QA", "DASHBOARD_QA", "DATASET_LOOKUP"):
            await self._check_general_fidelity(primary_entity, answer, report)

        critical_violations = [v for v in report.violations if v.severity == "critical"]
        if critical_violations:
            report.passed = False
            report.corrected_answer = self._build_corrected_answer(answer, critical_violations)
        return report

    async def _check_lineage_fidelity(
        self,
        entity: Any,
        answer: str,
        report: FidelityReport,
    ) -> None:
        """Check lineage answer fidelity (E-CONTRA)."""
        urn = getattr(entity, "urn", None)
        if not urn:
            return

        db_entity = await self.entity_repo.get_by_urn(urn)
        if not db_entity:
            return

        payload = getattr(db_entity, "payload", {}) or {}
        db_upstreams = payload.get("upstreams", [])
        db_downstreams = payload.get("downstreams", [])
        has_lineage_in_db = bool(db_upstreams or db_downstreams)

        no_lineage_patterns = [
            "không có lineage",
            "khong co lineage",
            "chưa có thông tin lineage",
            "không có upstream",
            "không có downstream",
            "không có dữ liệu nguồn",
            "no lineage",
            "no upstream",
            "no downstream",
        ]
        answer_claims_no_lineage = any(p in answer.lower() for p in no_lineage_patterns)

        if has_lineage_in_db and answer_claims_no_lineage:
            up_names = [u.split(":")[-1].rstrip(")") for u in db_upstreams[:3]]
            down_names = [d.split(":")[-1].rstrip(")") for d in db_downstreams[:3]]

            detail_parts: list[str] = []
            if db_upstreams:
                detail_parts.append(
                    f"**{len(db_upstreams)} upstream(s):** {', '.join(up_names)}"
                    + ("..." if len(db_upstreams) > 3 else "")
                )
            if db_downstreams:
                detail_parts.append(
                    f"**{len(db_downstreams)} downstream(s):** {', '.join(down_names)}"
                    + ("..." if len(db_downstreams) > 3 else "")
                )

            entity_display = (
                getattr(db_entity, "display_name", None) or getattr(db_entity, "name", "") or ""
            )
            correction = (
                f"\n\n> ⚠️ **Đính chính:** Theo dữ liệu trong hệ thống DataHub, "
                f"**{entity_display}** thực tế có lineage:\n"
                + "\n".join(f"> - {p}" for p in detail_parts)
            )

            report.violations.append(
                FidelityViolation(
                    violation_type="E-CONTRA",
                    field="lineage",
                    db_value=f"upstreams={db_upstreams}, downstreams={db_downstreams}",
                    answer_claim="không có lineage",
                    severity="critical",
                    correction_text=correction,
                )
            )
            logger.error(
                f"[fidelity] E-CONTRA lineage for {urn}: DB has lineage, answer claims none."
            )


    async def _check_schema_fidelity(
        self,
        entity: Any,
        answer: str,
        report: FidelityReport,
    ) -> None:
        """Check schema answer fidelity (E-CONFABU, E-CONTRA)."""
        urn = getattr(entity, "urn", None)
        if not urn:
            return

        db_entity = await self.entity_repo.get_by_urn(urn)
        if not db_entity:
            return

        payload = getattr(db_entity, "payload", {}) or {}
        schema_fields = payload.get("schema_fields", [])
        db_field_names = {
            f.get("name", "").lower()
            for f in schema_fields
            if isinstance(f, dict) and f.get("name")
        }
        if not db_field_names:
            return

        answer_field_candidates = set(
            re.findall(r"\b([a-z][a-z0-9_]{2,}|[A-Z][a-zA-Z0-9]{2,})\b", answer)
        )
        ghost_fields = {
            f
            for f in answer_field_candidates
            if (
                len(f) >= 4
                and f.lower() not in db_field_names
                and "_" in f
                and f.lower() not in {"from", "where", "group", "order", "inner", "join", "select"}
            )
        }

        if ghost_fields:
            entity_display = (
                getattr(db_entity, "display_name", None) or getattr(db_entity, "name", "") or ""
            )
            report.violations.append(
                FidelityViolation(
                    violation_type="E-CONFABU",
                    field="schema",
                    db_value=f"Valid fields: {list(db_field_names)[:10]}",
                    answer_claim=f"Mentioned non-existent fields: {ghost_fields}",
                    severity="warning",
                    correction_text=(
                        f"\n\n> ℹ️ **Lưu ý:** Một số tên trường trong câu trả lời trên "
                        f"có thể không chính xác so với schema catalog của **{entity_display}**."
                    ),
                )
            )

    async def _check_owner_fidelity(
        self,
        entity: Any,
        answer: str,
        report: FidelityReport,
    ) -> None:
        """Check owner answer fidelity (E-CONTRA)."""
        urn = getattr(entity, "urn", None)
        if not urn:
            return

        db_entity = await self.entity_repo.get_by_urn(urn)
        if not db_entity:
            return

        payload = getattr(db_entity, "payload", {}) or {}
        db_owners = payload.get("owners", [])
        if not db_owners:
            return

        db_owner_names = {
            o.get("name", "").lower() for o in db_owners if isinstance(o, dict) and o.get("name")
        }

        no_owner_patterns = [
            "không có owner",
            "khong co owner",
            "chưa có người quản lý",
            "chua co nguoi quan ly",
            "không xác định được",
            "không có thông tin owner",
        ]
        if any(p in answer.lower() for p in no_owner_patterns) and db_owner_names:
            entity_display = (
                getattr(db_entity, "display_name", None) or getattr(db_entity, "name", "") or ""
            )
            report.violations.append(
                FidelityViolation(
                    violation_type="E-CONTRA",
                    field="owner",
                    db_value=f"owners={list(db_owner_names)}",
                    answer_claim="không có owner",
                    severity="critical",
                    correction_text=(
                        f"\n\n> ⚠️ **Đính chính:** Theo dữ liệu trong hệ thống, "
                        f"**{entity_display}** có owner: **{', '.join(db_owner_names)}**."
                    ),
                )
            )

    async def _check_general_fidelity(
        self,
        entity: Any,
        answer: str,
        report: FidelityReport,
    ) -> None:
        """Check general fidelity (E-SWAP)."""
        urn = getattr(entity, "urn", None)
        if not urn:
            return

        db_entity = await self.entity_repo.get_by_urn(urn)
        if not db_entity:
            return

        type_claims = {
            "dataset": ["dataset", "bảng", "table"],
            "dashboard": ["dashboard", "báo cáo dashboard", "report"],
            "glossary_term": ["glossary term", "thuật ngữ", "business term"],
        }
        db_type = getattr(db_entity, "entity_type", "")
        for type_key, type_words in type_claims.items():
            if type_key == db_type:
                continue
            if any(word in answer.lower() for word in type_words):
                logger.debug(
                    f"[fidelity] Possible E-SWAP: entity is {db_type}, mentions {type_key}."
                )


    def _build_corrected_answer(
        self,
        original_answer: str,
        violations: list[FidelityViolation],
    ) -> str:
        """Append correction text vào cuối answer."""
        corrections = "\n".join(v.correction_text for v in violations if v.correction_text)
        return original_answer + corrections
