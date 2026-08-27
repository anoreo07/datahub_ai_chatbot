"""Metadata report generation service."""
from __future__ import annotations

import structlog

from app.auth.models import UserContext
from app.schemas.actions import ReportAssessment, ReportResponse, ReportSection
from app.services.actions.base import BaseActionService
from app.services.actions.quality_service import owner_names
from app.services.actions.schema_service import extract_schema_columns

log = structlog.get_logger()


def _rating(score: int) -> tuple[str, int]:
    if score >= 80:
        return "Excellent", 5
    if score >= 60:
        return "Good", 4
    if score >= 40:
        return "Needs Improvement", 3
    if score > 0:
        return "Needs Improvement", 2
    return "Missing", 1


class MetadataReportService(BaseActionService):
    """Generates structured metadata overview and maturity reports."""

    async def metadata_report(
        self,
        dataset_query: str,
        user: UserContext | None = None,
    ) -> ReportResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return ReportResponse(
                dataset=dataset_query,
                recommendations=["Không tìm thấy dataset trong metadata DataHub."],
                valid=False,
            )
        payload = entity.payload or {}
        description = (payload.get("description") or "").strip()
        business_purpose = (payload.get("business_purpose") or "").strip()
        owners = owner_names(payload)
        tags = [str(t) for t in (payload.get("tags") or [])]
        glossary = [str(g) for g in (payload.get("glossary_terms") or [])]
        domain = (payload.get("domain") or "").strip()
        platform = (payload.get("platform") or "").strip()
        environment = (payload.get("environment") or "").strip()
        certified = bool(payload.get("certified"))
        schema = extract_schema_columns(payload)
        upstreams, downstreams = await self._lineage_urns(entity.urn)

        sections: list[ReportSection] = []
        sections.append(
            ReportSection(
                title="Dataset Overview",
                lines=[
                    f"- Name: {entity.display_name or entity.name}",
                    f"- Platform: {platform or '(chưa có)'} · Environment: {environment or '(chưa có)'}"
                    + (f" · Domain: {domain}" if domain else ""),
                    f"- URN: `{entity.urn}`",
                ],
            )
        )
        sections.append(
            ReportSection(
                title="Business Description",
                lines=[
                    business_purpose or description or "(chưa có mô tả business)",
                ],
            )
        )
        sections.append(
            ReportSection(
                title="Technical Summary",
                lines=[
                    f"- {len(schema)} cột trong schema",
                    f"- {len(upstreams)} upstream · {len(downstreams)} downstream",
                    f"- Certified: {'Có' if certified else 'Không'}",
                ],
            )
        )
        schema_lines = [
            f"- {f.get('name')} ({f.get('type') or f.get('native_data_type') or '?'})"
            + (f": {f.get('description')}" if f.get("description") else "")
            for f in schema
        ]
        sections.append(
            ReportSection(
                title="Schema Summary",
                lines=schema_lines[:30] or ["(không có schema)"],
            )
        )

        sections.append(
            ReportSection(
                title="Ownership",
                lines=["; ".join(owners) if owners else "(chưa có owner)"],
            )
        )
        sections.append(
            ReportSection(
                title="Glossary",
                lines=[" · ".join(glossary) if glossary else "(chưa gắn glossary term)"],
            )
        )
        sections.append(
            ReportSection(
                title="Tags",
                lines=[" · ".join(tags) if tags else "(chưa có tag)"],
            )
        )
        lineage_lines: list[str] = []
        if upstreams:
            lineage_lines.append("Upstream:")
            lineage_lines += [f"- {u}" for u in upstreams]
        else:
            lineage_lines.append("Upstream: (không có)")
        if downstreams:
            lineage_lines.append("Downstream:")
            lineage_lines += [f"- {d}" for d in downstreams]
        else:
            lineage_lines.append("Downstream: (không có)")
        sections.append(ReportSection(title="Lineage", lines=lineage_lines))
        sections.append(
            ReportSection(
                title="Data Quality",
                lines=[
                    f"- Assertions: {len(payload.get('assertions') or [])}",
                    f"- Profiling: {'Có' if payload.get('profiling') else 'Chưa có'}",
                    f"- Freshness: {'Có' if payload.get('freshness') else 'Chưa có'}",
                ],
            )
        )
        sections.append(
            ReportSection(
                title="Documentation Quality",
                lines=[
                    f"- Độ dài mô tả: {len(description)} ký tự",
                ],
            )
        )

        def _pct(cond: bool) -> int:
            return 100 if cond else 0

        assessment: list[ReportAssessment] = []
        assessment.append(
            self._assess(
                "Metadata Completeness",
                _pct(bool(description)) + (50 if description else 0),
            )
        )
        assessment.append(
            self._assess(
                "Documentation Quality",
                100 if len(description) >= 50 else (60 if description else 0),
            )
        )
        assessment.append(
            self._assess(
                "Governance Readiness",
                int(
                    (
                        sum([bool(domain), bool(owners), bool(tags), bool(glossary)])
                        / 4
                    )
                    * 100
                ),
            )
        )
        assessment.append(
            self._assess(
                "Discoverability",
                int(((len(description) > 0) + bool(tags) + bool(glossary)) / 3 * 100),
            )
        )
        assessment.append(
            self._assess(
                "Lineage Completeness",
                _pct(bool(upstreams or downstreams)),
            )
        )
        assessment.append(
            self._assess(
                "Overall Metadata Maturity",
                int(
                    (
                        (100 if description else 0)
                        + (100 if owners else 0)
                        + (100 if domain else 0)
                        + (100 if tags else 0)
                        + (100 if bool(upstreams or downstreams) else 0)
                    )
                    / 5
                ),
            )
        )

        overall_score = assessment[-1].score
        overall_rating, _ = _rating(overall_score)

        recommendations: list[str] = []
        if not description:
            recommendations.append("Cải thiện mô tả (Improve Description)")
        if not owners:
            recommendations.append("Gán owner (Assign Owner)")
        if not glossary:
            recommendations.append("Thêm glossary (Add Glossary)")
        if not tags:
            recommendations.append("Cải thiện tags (Improve Tags)")
        if not payload.get("assertions"):
            recommendations.append("Thêm assertions (Add Assertions)")
        if not payload.get("profiling"):
            recommendations.append("Bật profiling (Enable Profiling)")
        if not upstreams and not downstreams:
            recommendations.append("Thêm lineage (Add Lineage)")
        if not recommendations:
            recommendations.append("Metadata đã đầy đủ. Duy trì cập nhật định kỳ.")

        return ReportResponse(
            dataset=entity.display_name or entity.name,
            urn=entity.urn,
            sections=sections,
            assessment=assessment,
            overall_score=overall_score,
            overall_rating=overall_rating,
            recommendations=recommendations,
            valid=True,
        )

    @staticmethod
    def _assess(dimension: str, score: int) -> ReportAssessment:
        rating, stars = _rating(score)
        return ReportAssessment(
            dimension=dimension,
            score=min(100, score),
            rating=rating,
            stars=stars,
        )
