"""Integration tests for the Data Quality Report feature.

Covers:
1. Metadata-only fallback (no profiling) -> 8 sections + ``not_evaluated_checks``.
2. Full profiling payload -> real metrics, no not-evaluated entries.
3. TXT / PDF renderers produce exportable, non-empty artifacts.
4. Chat dispatch with ``selected_action="quality"`` returns a QUALITY_CHECK
   answer carrying the structured report for the export UI.
"""
import pytest

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.quality import QualityStatus
from app.services.action_service import ActionService
from app.services.quality_report import (
    render_markdown,
    render_pdf_bytes,
    render_summary_markdown,
    render_txt,
)
from database.models import Entity
from database.repositories.entity_repository import EntityRepository

_QUALITY_URN = "urn:li:dataset:(urn:li:dataPlatform:snowflake,quality_orders,PROD)"


def _admin() -> UserContext:
    return UserContext(user_id="admin", roles=["admin"], is_admin=True)


def _dataset(payload: dict) -> Entity:
    return Entity(
        urn=_QUALITY_URN, entity_type="dataset", name="quality_orders",
        display_name="quality_orders", description="Bảng đơn hàng chất lượng.",
        platform="snowflake", domain="Sales",
        datahub_url=f"http://localhost:9002/dataset/{_QUALITY_URN}",
        payload=payload,
    )


def _base_payload(**extra: object) -> dict:
    return {
        "description": "Bảng đơn hàng chất lượng.",
        "domain": "Sales",
        "platform": "snowflake",
        "environment": "PROD",
        "owners": ["data.team@example.com"],
        "tags": ["gold", "pii"],
        "glossary_terms": ["sales_order"],
        "schema_fields": [
            {"name": "order_id", "type": "string", "description": "Mã đơn"},
            {"name": "amount", "type": "decimal", "description": "Giá trị đơn"},
        ],
        **extra,
    }


async def _seed(db_session, entity: Entity) -> None:
    await EntityRepository(db_session).upsert(entity)


@pytest.mark.asyncio
async def test_quality_metadata_only_fallback(db_session) -> None:
    """No profiling data -> metadata checks run and missing dims are flagged."""
    await _seed(db_session, _dataset(_base_payload()))
    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    report = await svc.quality_check("quality_orders", user=_admin())

    assert report.valid is True
    assert report.dataset == "quality_orders"
    assert report.profiling_available is False
    assert report.rating in {"Excellent", "Good", "Fair", "Poor"}
    assert [s.key for s in report.sections] == [
        "metadata", "schema", "completeness", "uniqueness",
        "validity", "consistency", "freshness", "lineage",
    ]
    for expected in [
        "Completeness (NULL percentage)", "Duplicate rate",
        "Record count anomaly", "Schema drift",
        "Type validity (profiling)", "Freshness",
    ]:
        assert expected in report.not_evaluated_checks
    comp = next(s for s in report.sections if s.key == "completeness")
    assert comp.status == QualityStatus.NOT_EVALUATED
    assert report.recommendations, "metadata gaps must produce recommendations"


@pytest.mark.asyncio
async def test_quality_with_profiling(db_session) -> None:
    """Full profiling payload -> real metrics, no not-evaluated entries."""
    profiling = {
        "column_stats": [
            {"name": "order_id", "null_rate": 0.0, "type_validity": 1.0},
            {"name": "amount", "null_rate": 25.0, "type_validity": 0.99},
        ],
        "duplicate_rate": 2.5,
        "row_count": 5000,
        "row_count_delta_pct": 35.0,
        "schema_drift": {"detected": False, "detail": "không đổi"},
    }
    payload = _base_payload(
        profiling=profiling,
        freshness={"last_updated": "2026-08-01", "frequency": "daily"},
    )
    await _seed(db_session, _dataset(payload))
    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    report = await svc.quality_check("quality_orders", user=_admin())

    assert report.valid is True
    assert report.profiling_available is True
    assert report.not_evaluated_checks == [], report.not_evaluated_checks

    completeness = next(s for s in report.sections if s.key == "completeness")
    assert completeness.status != QualityStatus.NOT_EVALUATED
    assert completeness.score < 100, "25% NULL on a column must lower the score"

    uniqueness = next(s for s in report.sections if s.key == "uniqueness")
    assert uniqueness.status == QualityStatus.WARNING

    consistency = next(s for s in report.sections if s.key == "consistency")
    assert consistency.status == QualityStatus.FAILED, "35% row delta must fail"

    texts = [r.text for r in report.recommendations]
    assert any("trùng lặp" in t for t in texts)
    assert any("biến động" in t for t in texts)
    assert any("NULL" in t for t in texts)


@pytest.mark.asyncio
async def test_quality_render_txt_and_pdf(db_session) -> None:
    """Renderers produce non-empty, deterministic export artifacts."""
    await _seed(db_session, _dataset(_base_payload()))
    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    report = await svc.quality_check("quality_orders", user=_admin())

    txt = render_txt(report)
    assert report.dataset in txt
    assert "Overall" in txt
    assert "RECOMMENDATIONS" in txt.upper()
    assert "quality_orders" in txt
    assert txt.count("\n") > 15

    pdf = render_pdf_bytes(report)
    assert pdf, "PDF must be non-empty"
    assert pdf[:4] == b"%PDF"

    md = render_markdown(report)
    assert md.startswith("# 📊 Data Quality Report: quality_orders")

    summary = render_summary_markdown(report)
    assert summary.startswith("# 📊 Data Quality Report: quality_orders")
    assert f"**{report.overall_score}/100 — {report.rating}**" in summary
    for label in ("Metadata", "Schema", "Profiling", "Lineage"):
        assert f"**{label}**" in summary
    assert "Vấn đề quan trọng" in summary
    assert "Khuyến nghị hàng đầu" in summary


@pytest.mark.asyncio
async def test_quality_summary_no_issues(db_session) -> None:
    """A clean report renders a compact summary without a duplicated checklist."""
    from app.schemas.quality import (
        QualityFinding,
        QualityRecommendation,
        QualityReport,
        QualitySection,
    )

    sections = [
        QualitySection(
            key="metadata", title="Metadata", score=100,
            status=QualityStatus.PASSED,
            findings=[QualityFinding(name="Description", status=QualityStatus.PASSED)],
        ),
        QualitySection(
            key="schema", title="Schema", score=100,
            status=QualityStatus.PASSED,
            findings=[QualityFinding(name="Column types", status=QualityStatus.PASSED)],
        ),
        QualitySection(
            key="lineage", title="Lineage", score=100,
            status=QualityStatus.PASSED,
            findings=[QualityFinding(name="Lineage coverage", status=QualityStatus.PASSED)],
        ),
    ]
    report = QualityReport(
        dataset="quality_orders",
        urn=_QUALITY_URN,
        overall_score=100,
        rating="Excellent",
        profiling_available=False,
        sections=sections,
        recommendations=[QualityRecommendation(priority="low", text="Maintain ownership.")],
    )

    summary = render_summary_markdown(report)
    assert "Không có vấn đề đáng chú ý" in summary
    assert "Profiling metrics unavailable" not in summary
    assert "Khuyến nghị hàng đầu" in summary


@pytest.mark.asyncio
async def test_quality_chat_dispatch(db_session) -> None:
    """Chat with selected_action='quality' routes to the deterministic report."""
    await _seed(db_session, _dataset(_base_payload()))
    from app.services.chat_service import ChatService

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response = await service.answer(
        "Data quality check cho dataset quality_orders",
        user=_admin(),
        selected_action="quality",
    )
    assert response.intent == "QUALITY_CHECK"
    assert response.quality_report is not None
    assert response.quality_report.dataset == "quality_orders"
    assert response.quality_report.valid is True
    assert "# 📊 Data Quality Report: quality_orders" in response.answer
    assert "Tổng quan từng khía cạnh" in response.answer
    assert "View Full Report" in response.answer


@pytest.mark.asyncio
async def test_quality_chat_dispatch_full_when_requested(db_session) -> None:
    """Asking for the full report returns the complete audit table."""
    await _seed(db_session, _dataset(_base_payload()))
    from app.services.chat_service import ChatService

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response = await service.answer(
        "Cho tôi báo cáo đầy đủ data quality của quality_orders",
        user=_admin(),
        selected_action="quality",
    )
    assert response.intent == "QUALITY_CHECK"
    assert "| Section | Score | Status | Checks |" in response.answer
    assert "View Full Report" not in response.answer


@pytest.mark.asyncio
async def test_quality_followup_owner_from_evidence(db_session) -> None:
    """After a quality report, "owner của nó" resolves to the dataset's owner
    from the recorded quality evidence."""
    await _seed(db_session, _dataset(_base_payload(
        owners=[{"name": "Data Team", "type": "USER"}],
    )))
    from app.services.chat_service import ChatService

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    cid = "quality-owner"

    r1 = await service.answer(
        "Data quality check cho dataset quality_orders",
        user=_admin(), conversation_id=cid, selected_action="quality",
    )
    assert r1.intent == "QUALITY_CHECK", r1.answer

    r2 = await service.answer("owner của nó?", user=_admin(), conversation_id=cid)
    assert r2.intent == "OWNER_LOOKUP", r2.answer
    assert "Data Team" in r2.answer
