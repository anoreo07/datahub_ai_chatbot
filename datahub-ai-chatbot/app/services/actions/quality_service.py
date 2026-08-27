"""Data quality auditing action service."""
from __future__ import annotations

import structlog

from app.auth.models import UserContext
from app.schemas.quality import (
    QualityFinding,
    QualityRecommendation,
    QualityReport,
    QualitySection,
    QualityStatus,
)
from app.services.actions.base import BaseActionService
from app.services.actions.schema_service import extract_schema_columns
from app.services.quality_report import _rating_of

log = structlog.get_logger()


def owner_names(payload: dict) -> list[str]:
    out: list[str] = []
    for o in payload.get("owners") or []:
        if isinstance(o, dict) and o.get("name"):
            out.append(str(o["name"]))
    return out


def profiling_stats(payload: dict) -> dict | None:
    """Normalise profiling data into a flat stats dict, or None if unusable."""
    raw = payload.get("profiling")
    if raw is None:
        return None
    if isinstance(raw, list):
        raw = next((p for p in raw if isinstance(p, dict)), None)
        if raw is None:
            return None
    if not isinstance(raw, dict):
        return None
    if (
        raw.get("column_stats") is None
        and raw.get("duplicate_rate") is None
        and raw.get("row_count") is None
    ):
        return None
    return raw


class QualityActionService(BaseActionService):
    """Generates professional, deterministic Data Quality Reports against DataHub metadata."""

    async def quality_check(
        self,
        dataset_query: str,
        user: UserContext | None = None,
        entity_type: str | None = None,
    ) -> QualityReport:
        entity = await self.resolve_entity(dataset_query, user=user, entity_type=entity_type)
        if entity is None:
            return QualityReport(dataset=dataset_query, entity_name=dataset_query, valid=False)

        real_type = (entity.entity_type or "dataset").lower()
        payload = entity.payload or {}
        generated_at = QualityReport.now_iso()
        generated_by = ""
        if user is not None:
            generated_by = user.display_name or user.user_id or ""

        profiling = profiling_stats(payload)
        profiling_available = profiling is not None

        description = (entity.description or payload.get("description") or "").strip()
        owners = owner_names(payload)
        tags = [str(t) for t in (payload.get("tags") or [])]
        glossary = [str(g) for g in (payload.get("glossary_terms") or [])]
        domain = (entity.domain or payload.get("domain") or "").strip()
        platform = (entity.platform or payload.get("platform") or "").strip()
        environment = (entity.environment or payload.get("environment") or "").strip()
        schema = extract_schema_columns(payload)
        deprecated = bool(payload.get("deprecated"))
        assertions = payload.get("assertions") or []
        upstreams, downstreams = await self._lineage_urns(entity.urn)
        has_lineage = bool(upstreams or downstreams)

        missing_fields: list[str] = []
        not_applicable_fields: list[str] = []

        def section(key: str, title: str, findings: list[QualityFinding]) -> QualitySection:
            if all(f.status == QualityStatus.NOT_APPLICABLE for f in findings):
                return QualitySection(
                    key=key,
                    title=title,
                    score=100,
                    status=QualityStatus.NOT_APPLICABLE,
                    findings=findings,
                )

            active = [
                f for f in findings
                if f.status not in (QualityStatus.NOT_APPLICABLE, QualityStatus.NOT_EVALUATED)
            ]
            if not active:
                return QualitySection(
                    key=key,
                    title=title,
                    score=0,
                    status=QualityStatus.NOT_EVALUATED,
                    findings=findings,
                )

            weights = {
                QualityStatus.PASSED: 1.0,
                QualityStatus.WARNING: 0.5,
                QualityStatus.UNKNOWN: 0.25,
                QualityStatus.FAILED: 0.0,
                QualityStatus.SOURCE_ERROR: 0.0,
            }
            total = sum(weights.get(f.status, 0.0) for f in active)
            score = int((total / len(active)) * 100)

            if any(f.status == QualityStatus.SOURCE_ERROR for f in active):
                sec_status = QualityStatus.SOURCE_ERROR
            elif any(f.status == QualityStatus.FAILED for f in active):
                sec_status = QualityStatus.FAILED
            elif any(f.status == QualityStatus.WARNING for f in active):
                sec_status = QualityStatus.WARNING
            elif all(f.status == QualityStatus.PASSED for f in active):
                sec_status = QualityStatus.PASSED
            else:
                sec_status = QualityStatus.UNKNOWN

            return QualitySection(
                key=key,
                title=title,
                score=score,
                status=sec_status,
                findings=findings,
            )

        sections: list[QualitySection] = []
        recommendations: list[QualityRecommendation] = []
        not_evaluated: list[str] = []

        def _rec(priority: str, text: str) -> None:
            recommendations.append(QualityRecommendation(priority=priority, text=text))

        # -------------------------------------------------------------- #
        # 1. Metadata Completeness
        # -------------------------------------------------------------- #
        meta_findings: list[QualityFinding] = []
        if description:
            meta_findings.append(
                QualityFinding(
                    item="Description",
                    status=QualityStatus.PASSED,
                    message=f"Đầy đủ ({len(description)} ký tự)",
                )
            )
        else:
            missing_fields.append("description")
            meta_findings.append(
                QualityFinding(
                    item="Description",
                    status=QualityStatus.FAILED,
                    message="Chưa có mô tả cho thực thể này.",
                )
            )
            _rec("HIGH", "Bổ sung Business Description để tăng tính khám phá và hiểu dữ liệu.")

        if owners:
            meta_findings.append(
                QualityFinding(
                    item="Owners",
                    status=QualityStatus.PASSED,
                    message=f"Đã gán ({', '.join(owners)})",
                )
            )
        else:
            missing_fields.append("owners")
            meta_findings.append(
                QualityFinding(
                    item="Owners",
                    status=QualityStatus.FAILED,
                    message="Chưa gán owner. Không xác định được người chịu trách nhiệm.",
                )
            )
            _rec("HIGH", "Gán ít nhất một Owner (kỹ thuật hoặc nghiệp vụ) cho thực thể.")

        if domain:
            meta_findings.append(
                QualityFinding(
                    item="Domain",
                    status=QualityStatus.PASSED,
                    message=f"Thuộc domain '{domain}'",
                )
            )
        else:
            missing_fields.append("domain")
            meta_findings.append(
                QualityFinding(
                    item="Domain",
                    status=QualityStatus.WARNING,
                    message="Chưa phân loại domain.",
                )
            )
            _rec("MEDIUM", "Phân loại domain cho thực thể để hỗ trợ Data Mesh / quản trị phân vùng.")

        if tags:
            meta_findings.append(
                QualityFinding(
                    item="Tags",
                    status=QualityStatus.PASSED,
                    message=f"{len(tags)} tag ({', '.join(tags[:4])})",
                )
            )
        else:
            missing_fields.append("tags")
            meta_findings.append(
                QualityFinding(
                    item="Tags",
                    status=QualityStatus.WARNING,
                    message="Chưa có tag nào.",
                )
            )

        if glossary:
            meta_findings.append(
                QualityFinding(
                    item="Glossary Terms",
                    status=QualityStatus.PASSED,
                    message=f"{len(glossary)} thuật ngữ ({', '.join(glossary[:4])})",
                )
            )
        else:
            missing_fields.append("glossary_terms")
            meta_findings.append(
                QualityFinding(
                    item="Glossary Terms",
                    status=QualityStatus.WARNING,
                    message="Chưa gắn Glossary Term nghiệp vụ.",
                )
            )
            _rec("LOW", "Gắn Glossary Term để chuẩn hoá thuật ngữ nghiệp vụ.")

        if deprecated:
            meta_findings.append(
                QualityFinding(
                    item="Lifecycle Status",
                    status=QualityStatus.WARNING,
                    message="Thực thể này đã được đánh dấu DEPRECATED.",
                )
            )
            _rec("HIGH", "Thực thể đã Deprecated — lên kế hoạch chuyển đổi sang nguồn dữ liệu thay thế.")
        else:
            meta_findings.append(
                QualityFinding(
                    item="Lifecycle Status",
                    status=QualityStatus.PASSED,
                    message="Đang hoạt động bình thường (Active).",
                )
            )

        sections.append(section("metadata", "Metadata Completeness", meta_findings))

        # -------------------------------------------------------------- #
        # 2. Schema Quality
        # -------------------------------------------------------------- #
        schema_findings: list[QualityFinding] = []
        if real_type in ("dataset", "table"):
            if schema:
                schema_findings.append(
                    QualityFinding(
                        item="Schema Registered",
                        status=QualityStatus.PASSED,
                        message=f"{len(schema)} cột được ghi nhận trong schema.",
                    )
                )
                cols_without_desc = [
                    f.get("name") or "?" for f in schema if not (f.get("description") or "").strip()
                ]
                if cols_without_desc:
                    ratio = (len(schema) - len(cols_without_desc)) / len(schema)
                    schema_status = QualityStatus.PASSED if ratio >= 0.8 else (
                        QualityStatus.WARNING if ratio >= 0.4 else QualityStatus.FAILED
                    )
                    schema_findings.append(
                        QualityFinding(
                            item="Column Descriptions",
                            status=schema_status,
                            message=f"{len(cols_without_desc)}/{len(schema)} cột chưa có mô tả "
                            f"({', '.join(cols_without_desc[:4])}{'...' if len(cols_without_desc) > 4 else ''}).",
                        )
                    )
                    if ratio < 0.8:
                        _rec("MEDIUM", f"Bổ sung mô tả cho {len(cols_without_desc)} cột còn thiếu trong schema.")
                else:
                    schema_findings.append(
                        QualityFinding(
                            item="Column Descriptions",
                            status=QualityStatus.PASSED,
                            message="100% các cột đều có mô tả đầy đủ.",
                        )
                    )

                cols_without_type = [
                    f.get("name") or "?"
                    for f in schema
                    if not (f.get("type") or f.get("native_data_type") or "").strip()
                ]
                if cols_without_type:
                    schema_findings.append(
                        QualityFinding(
                            item="Column Data Types",
                            status=QualityStatus.WARNING,
                            message=f"{len(cols_without_type)} cột chưa xác định rõ kiểu dữ liệu.",
                        )
                    )
                else:
                    schema_findings.append(
                        QualityFinding(
                            item="Column Data Types",
                            status=QualityStatus.PASSED,
                            message="Tất cả các cột đều có kiểu dữ liệu tường minh.",
                        )
                    )
            else:
                missing_fields.append("schema")
                schema_findings.append(
                    QualityFinding(
                        item="Schema Registered",
                        status=QualityStatus.FAILED,
                        message="Chưa có schema nào được đồng bộ vào DataHub.",
                    )
                )
                _rec("HIGH", "Chạy ingest để đồng bộ schema đầy đủ từ nguồn dữ liệu.")
        else:
            not_applicable_fields.append("schema")
            schema_findings.append(
                QualityFinding(
                    item="Schema",
                    status=QualityStatus.NOT_APPLICABLE,
                    message=f"Không áp dụng cấu trúc bảng cho loại thực thể '{real_type}'.",
                )
            )

        sections.append(section("schema", "Schema Quality", schema_findings))

        # -------------------------------------------------------------- #
        # 3. Profiling Checks
        # -------------------------------------------------------------- #
        if profiling_available and profiling:
            def _eval_ratio(
                name: str,
                rate: float | None,
                warn_thresh: float,
                fail_thresh: float,
                unit: str = "%",
            ) -> QualityFinding:
                if rate is None:
                    not_evaluated.append(name)
                    return QualityFinding(
                        item=name,
                        status=QualityStatus.NOT_EVALUATED,
                        message="Chỉ số chưa được tính toán trong profiling gần nhất.",
                    )
                pct = round(rate * 100, 2)
                if rate >= fail_thresh:
                    st = QualityStatus.FAILED
                    msg = f"Vượt ngưỡng nghiêm trọng: {pct}{unit} (ngưỡng cho phép < {fail_thresh * 100:.0f}{unit})."
                elif rate >= warn_thresh:
                    st = QualityStatus.WARNING
                    msg = f"Cảnh báo: {pct}{unit} (ngưỡng khuyến nghị < {warn_thresh * 100:.0f}{unit})."
                else:
                    st = QualityStatus.PASSED
                    msg = f"Tốt: {pct}{unit}."
                return QualityFinding(item=name, status=st, message=msg)

            completeness_findings: list[QualityFinding] = []
            null_rate = profiling.get("null_rate") or profiling.get("null_percentage")
            if null_rate is not None and null_rate > 1:
                null_rate = null_rate / 100.0
            completeness_findings.append(
                _eval_ratio("Null Rate (Tỷ lệ giá trị rỗng)", null_rate, 0.05, 0.20)
            )
            sections.append(section("completeness", "Completeness (Tính Đầy Đủ)", completeness_findings))

            uniqueness_findings: list[QualityFinding] = []
            dup_rate = profiling.get("duplicate_rate") or profiling.get("duplicate_percentage")
            if dup_rate is not None and dup_rate > 1:
                dup_rate = dup_rate / 100.0
            uniqueness_findings.append(
                _eval_ratio("Duplicate Rate (Tỷ lệ bản ghi trùng lặp)", dup_rate, 0.01, 0.05)
            )
            sections.append(section("uniqueness", "Uniqueness (Tính Duy Nhất)", uniqueness_findings))

            validity_findings: list[QualityFinding] = []
            invalid_rate = profiling.get("invalid_rate") or profiling.get("invalid_percentage")
            if invalid_rate is not None and invalid_rate > 1:
                invalid_rate = invalid_rate / 100.0
            validity_findings.append(
                _eval_ratio("Invalid Format Rate (Tỷ lệ sai định dạng)", invalid_rate, 0.02, 0.10)
            )
            sections.append(section("validity", "Validity (Tính Hợp Lệ)", validity_findings))

            consistency_findings: list[QualityFinding] = []
            assertion_runs = profiling.get("assertion_runs") or assertions
            if assertion_runs:
                passed_a = sum(1 for a in assertion_runs if (a.get("result") or {}).get("type") == "SUCCESS")
                failed_a = len(assertion_runs) - passed_a
                if failed_a == 0:
                    c_status = QualityStatus.PASSED
                    c_msg = f"100% assertions thành công ({len(assertion_runs)}/{len(assertion_runs)} rules)."
                else:
                    c_status = QualityStatus.FAILED
                    c_msg = f"{failed_a}/{len(assertion_runs)} assertion rules thất bại."
                    _rec("HIGH", f"Kiểm tra và sửa {failed_a} DataHub Assertions đang bị fail.")
                consistency_findings.append(
                    QualityFinding(item="DataHub Assertions", status=c_status, message=c_msg)
                )
            else:
                not_evaluated.append("DataHub Assertions")
                consistency_findings.append(
                    QualityFinding(
                        item="DataHub Assertions",
                        status=QualityStatus.NOT_EVALUATED,
                        message="Chưa cấu hình assertion rules cho dataset này.",
                    )
                )
            sections.append(section("consistency", "Consistency (Tính Nhất Quán)", consistency_findings))

            freshness_findings: list[QualityFinding] = []
            freshness_sec = profiling.get("freshness_seconds") or profiling.get("age_seconds")
            if freshness_sec is not None:
                hours = round(freshness_sec / 3600, 1)
                if hours > 48:
                    f_st = QualityStatus.FAILED
                    f_msg = f"Dữ liệu trễ {hours} giờ (> 48h)."
                    _rec("HIGH", "Kiểm tra pipeline ingest/ETL — dữ liệu đang bị chậm trễ cập nhật.")
                elif hours > 24:
                    f_st = QualityStatus.WARNING
                    f_msg = f"Dữ liệu cập nhật cách đây {hours} giờ."
                else:
                    f_st = QualityStatus.PASSED
                    f_msg = f"Dữ liệu mới cập nhật ({hours} giờ trước)."
                freshness_findings.append(QualityFinding(item="Data Freshness", status=f_st, message=f_msg))
            else:
                not_evaluated.append("Data Freshness")
                freshness_findings.append(
                    QualityFinding(
                        item="Data Freshness",
                        status=QualityStatus.NOT_EVALUATED,
                        message="Chưa có thông tin SLA freshness.",
                    )
                )
            sections.append(section("freshness", "Freshness (Tính Kịp Thời)", freshness_findings))
        else:
            if real_type in ("dataset", "table"):
                not_evaluated.extend([
                    "Null Rate (Tỷ lệ giá trị rỗng)",
                    "Duplicate Rate (Tỷ lệ bản ghi trùng lặp)",
                    "Invalid Format Rate (Tính hợp lệ)",
                    "Data Freshness (Tính kịp thời)",
                ])
                for key, title in (
                    ("completeness", "Completeness (Tính Đầy Đủ)"),
                    ("uniqueness", "Uniqueness (Tính Duy Nhất)"),
                    ("validity", "Validity (Tính Hợp Lệ)"),
                    ("freshness", "Freshness (Tính Kịp Thời)"),
                ):
                    sections.append(
                        QualitySection(
                            key=key,
                            title=title,
                            score=0,
                            status=QualityStatus.NOT_EVALUATED,
                            findings=[
                                QualityFinding(
                                    item="Profiling Data",
                                    status=QualityStatus.NOT_EVALUATED,
                                    message=(
                                        "Chưa có dữ liệu profiling. Hãy bật GE/Great "
                                        "Expectations profiling để đo lường tự động."
                                    ),
                                )
                            ],
                        )
                    )
                _rec(
                    "HIGH",
                    "Cấu hình DataHub Profiling để đo lường Completeness, Uniqueness và Freshness tự động.",
                )
            else:
                for key, title in (
                    ("completeness", "Completeness"),
                    ("uniqueness", "Uniqueness"),
                    ("validity", "Validity"),
                    ("freshness", "Freshness"),
                ):
                    not_applicable_fields.append(key)
                    sections.append(
                        QualitySection(
                            key=key,
                            title=title,
                            score=100,
                            status=QualityStatus.NOT_APPLICABLE,
                            findings=[
                                QualityFinding(
                                    item=title,
                                    status=QualityStatus.NOT_APPLICABLE,
                                    message=(
                                        f"Không áp dụng kiểm tra profiling cho loại thực thể '{real_type}'."
                                    ),
                                )
                            ],
                        )
                    )

        # -------------------------------------------------------------- #
        # 4. Lineage & Traceability
        # -------------------------------------------------------------- #
        lineage_findings: list[QualityFinding] = []
        if has_lineage:
            lineage_findings.append(
                QualityFinding(
                    item="Lineage Connected",
                    status=QualityStatus.PASSED,
                    message=(
                        f"Đã liên kết ({len(upstreams)} upstream, {len(downstreams)} downstream)."
                    ),
                )
            )
        else:
            missing_fields.append("lineage")
            lineage_findings.append(
                QualityFinding(
                    item="Lineage Connected",
                    status=QualityStatus.WARNING,
                    message="Chưa có thông tin lineage (upstream/downstream).",
                )
            )
            _rec(
                "MEDIUM",
                "Khai báo Lineage để theo dõi nguồn gốc và phân tích tác động (Impact Analysis).",
            )
        sections.append(section("lineage", "Lineage & Traceability", lineage_findings))

        # Overall calculation across evaluated sections
        evaluated_sections = [
            s for s in sections
            if s.status not in (QualityStatus.NOT_APPLICABLE, QualityStatus.NOT_EVALUATED)
        ]
        overall = (
            int(sum(s.score for s in evaluated_sections) / len(evaluated_sections))
            if evaluated_sections
            else 100
        )
        rating = _rating_of(overall)

        return QualityReport(
            dataset=entity.display_name or entity.name or dataset_query,
            entity_name=entity.display_name or entity.name or dataset_query,
            entity_type=real_type,
            platform=platform,
            urn=entity.urn,
            url=entity.datahub_url,
            generated_at=generated_at,
            generated_by=generated_by,
            overall_score=overall,
            rating=rating,
            profiling_available=profiling_available,
            sections=sections,
            recommendations=recommendations,
            not_evaluated_checks=sorted(set(not_evaluated)),
            missing_fields=missing_fields,
            not_applicable_fields=not_applicable_fields,
            valid=True,
        )
