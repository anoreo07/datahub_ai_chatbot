"""Regression test for bug: 'PVB QDAT lấy dữ liệu từ đâu?'
-> Chatbot previously drifted to 'Báo cáo ước KQKD'.

Bug root cause: E-DRIFT — entity resolver failed, HybridSearch retrieved wrong entity.
Expected: AnchorValidator blocks the drift response.
"""

from app.services.chat.anchor_builder import AnchorBuilder
from app.services.chat.anchor_validator import AnchorValidator

REGRESSION_QUERY = "PVB QDAT lấy dữ liệu từ đâu?"
WRONG_ENTITY_NAME = "Báo cáo ước KQKD"
WRONG_ENTITY_URN = "urn:li:dataset:baocao_uoc_kqkd"


def test_anchor_built_for_pvb_qdat() -> None:
    """Anchor must be built from 'PVB QDAT'."""
    anchor = AnchorBuilder().build(REGRESSION_QUERY, [])
    mentions = [a.raw_mention for a in anchor.anchors]
    assert len(mentions) > 0, "No anchor built — AnchorBuilder failed to detect 'PVB QDAT'"
    assert any("PVB" in m or "QDAT" in m for m in mentions), (
        f"Expected anchor about PVB QDAT, got: {mentions}"
    )


def test_drift_detected_when_wrong_entity_resolved() -> None:
    """If resolver returns 'Báo cáo ước KQKD' instead of 'PVB QDAT', E-DRIFT must be detected."""
    anchor = AnchorBuilder().build(REGRESSION_QUERY, [])

    class WrongEntity:
        name = WRONG_ENTITY_NAME
        urn = WRONG_ENTITY_URN
        entity_type = "dataset"

    report = AnchorValidator().validate_resolution(
        anchor=anchor,
        resolved_entities=[WrongEntity()],
    )
    assert not report.passed, (
        f"Validator did NOT detect drift! Anchor: {[a.raw_mention for a in anchor.anchors]}, "
        f"Resolved: {WRONG_ENTITY_NAME}"
    )
    assert report.error_code in ("E-DRIFT", "E-MISS")


def test_context_drift_detected() -> None:
    """Context containing 'Báo cáo ước KQKD' instead of 'PVB QDAT' triggers context drift."""
    anchor = AnchorBuilder().build(REGRESSION_QUERY, [])

    class WrongResult:
        entity_urn = WRONG_ENTITY_URN
        entity_name = WRONG_ENTITY_NAME

    report = AnchorValidator().validate_context(
        anchor=anchor,
        search_results=[WrongResult()],
        context_xml=f"<entity name='{WRONG_ENTITY_NAME}'>...</entity>",
    )
    assert not report.passed, "Context drift NOT detected for PVB QDAT regression case"
