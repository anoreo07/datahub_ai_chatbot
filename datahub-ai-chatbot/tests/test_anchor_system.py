"""Tests for QueryAnchor, AnchorBuilder, AnchorValidator, and DataFidelityChecker."""

import pytest

from app.services.chat.anchor_builder import AnchorBuilder
from app.services.chat.anchor_validator import AnchorValidator
from app.services.chat.query_anchor import (
    AnchorConfidence,
    AnchorSource,
    EntityAnchor,
    QueryAnchor,
)


class TestAnchorBuilder:
    def test_extract_dim_entity(self) -> None:
        """dim_ prefix must be identified."""
        anchor = AnchorBuilder().build("dim_KhachHang có những cột nào?", [])
        assert len(anchor.anchors) == 1
        assert anchor.anchors[0].raw_mention == "dim_KhachHang"

    def test_extract_fact_entity(self) -> None:
        anchor = AnchorBuilder().build("fact_DonHang lấy dữ liệu từ đâu?", [])
        assert any(a.raw_mention == "fact_DonHang" for a in anchor.anchors)

    def test_extract_named_entity_pvb_qdat(self) -> None:
        """Test case from actual bug report."""
        anchor = AnchorBuilder().build("PVB QDAT lấy dữ liệu từ đâu?", [])
        assert len(anchor.anchors) >= 1
        assert any("PVB" in a.raw_mention or "QDAT" in a.raw_mention for a in anchor.anchors)

    def test_free_query_no_anchor(self) -> None:
        """General question mentioning no entity."""
        anchor = AnchorBuilder().build("Hệ thống có bao nhiêu dataset?", [])
        assert anchor.is_free_query()

    def test_anaphora_resolution(self) -> None:
        """'Nó' resolves back to the previous turn's entity."""
        history = [
            {
                "query": "dim_KhachHang là gì?",
                "answer": "dim_KhachHang là bảng chiều...",
                "entities": [
                    {
                        "name": "dim_KhachHang",
                        "urn": "urn:li:dataset:dim_KhachHang",
                        "entity_type": "dataset",
                    }
                ],
            }
        ]
        anchor = AnchorBuilder().build("Nó lấy dữ liệu từ đâu?", history)
        assert len(anchor.anchors) == 1
        assert anchor.anchors[0].raw_mention == "dim_KhachHang"
        assert anchor.anchors[0].source == AnchorSource.ANAPHORA

    def test_multiple_entities_in_query(self) -> None:
        anchor = AnchorBuilder().build("So sánh dim_KhachHang và dim_SanPham", [])
        names = [a.raw_mention for a in anchor.anchors]
        assert "dim_KhachHang" in names
        assert "dim_SanPham" in names


class TestAnchorValidator:
    def test_drift_detection(self) -> None:
        """Resolve to unrelated entity -> E-DRIFT."""
        anchor = QueryAnchor(original_query="PVB QDAT lấy dữ liệu từ đâu?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="PVB QDAT",
                resolved_urn=None,
                resolved_name=None,
                entity_type=None,
                source=AnchorSource.EXPLICIT_MENTION,
                confidence=AnchorConfidence.LOW,
            )
        )

        class FakeEntity:
            name = "Báo cáo ước KQKD"
            urn = "urn:li:dataset:baocao_kqkd"
            entity_type = "dataset"

        report = AnchorValidator().validate_resolution(
            anchor=anchor,
            resolved_entities=[FakeEntity()],
        )
        assert not report.passed
        assert report.error_code == "E-DRIFT"

    def test_miss_detection(self) -> None:
        """Anchor mentions entity, but resolver returns empty -> E-MISS."""
        anchor = QueryAnchor(original_query="dim_BaoCeoLayout có gì?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="dim_BaoCeoLayout",
                resolved_urn=None,
                resolved_name=None,
                entity_type=None,
                source=AnchorSource.EXPLICIT_MENTION,
                confidence=AnchorConfidence.LOW,
            )
        )
        report = AnchorValidator().validate_resolution(
            anchor=anchor,
            resolved_entities=[],
        )
        assert not report.passed
        assert report.error_code == "E-MISS"

    def test_correct_resolution_passes(self) -> None:
        """Resolver returns the correct entity -> passed."""
        anchor = QueryAnchor(original_query="dim_KhachHang có gì?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="dim_KhachHang",
                resolved_urn="urn:li:dataset:dim_KhachHang",
                resolved_name="dim_KhachHang",
                entity_type="dataset",
                source=AnchorSource.EXPLICIT_MENTION,
                confidence=AnchorConfidence.HIGH,
            )
        )

        class FakeEntity:
            name = "dim_KhachHang"
            urn = "urn:li:dataset:dim_KhachHang"
            entity_type = "dataset"

        report = AnchorValidator().validate_resolution(
            anchor=anchor,
            resolved_entities=[FakeEntity()],
        )
        assert report.passed

    def test_context_drift_detection(self) -> None:
        """Context lacks anchor entity -> E-DRIFT at retrieval stage."""
        anchor = QueryAnchor(original_query="PVB QDAT lineage?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="PVB QDAT",
                resolved_urn="urn:li:dashboard:pvb_qdat",
                resolved_name="PVB QDAT",
                entity_type="dashboard",
                source=AnchorSource.EXPLICIT_MENTION,
                confidence=AnchorConfidence.HIGH,
            )
        )

        class FakeResult:
            entity_urn = "urn:li:dataset:baocao_kqkd"
            entity_name = "Báo cáo ước KQKD"

        report = AnchorValidator().validate_context(
            anchor=anchor,
            search_results=[FakeResult()],
            context_xml="",
        )
        assert not report.passed
        assert report.error_code == "E-DRIFT"

    def test_ghost_entity_detection(self) -> None:
        """Answer contains ungrounded entity -> E-GHOST recorded."""
        anchor = QueryAnchor(original_query="dim_KhachHang owner?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="dim_KhachHang",
                resolved_urn="urn:li:dataset:dim_KhachHang",
                resolved_name="dim_KhachHang",
                entity_type="dataset",
                source=AnchorSource.EXPLICIT_MENTION,
                confidence=AnchorConfidence.HIGH,
            )
        )

        answer = (
            "dim_KhachHang được quản lý bởi team Data. "
            "Ngoài ra, dim_SanPham cũng thuộc cùng domain."
        )


        report = AnchorValidator().validate_answer(
            anchor=anchor,
            answer=answer,
            citations=[],
            resolved_entities=[],
        )
        assert "dim_SanPham" in report.ghost_entities


class TestDataFidelityChecker:
    @pytest.mark.asyncio
    async def test_lineage_contradiction(self) -> None:
        from app.services.chat.data_fidelity_checker import DataFidelityChecker

        class FakeDbEntity:
            urn = "urn:li:dataset:pvb_qdat"
            name = "PVB QDAT"
            display_name = "PVB QDAT"
            entity_type = "dataset"
            payload = {
                "upstreams": ["urn:li:dataset:source1", "urn:li:dataset:source2"],
                "downstreams": [],
            }

        class MockEntityRepo:
            async def get_by_urn(self, urn: str):
                if urn == "urn:li:dataset:pvb_qdat":
                    return FakeDbEntity()
                return None

        anchor = QueryAnchor(original_query="PVB QDAT lấy dữ liệu từ đâu?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="PVB QDAT",
                resolved_urn="urn:li:dataset:pvb_qdat",
                resolved_name="PVB QDAT",
                confidence=AnchorConfidence.HIGH,
            )
        )

        class FakeEntity:
            urn = "urn:li:dataset:pvb_qdat"
            name = "PVB QDAT"

        checker = DataFidelityChecker(entity_repository=MockEntityRepo())
        ans = (
            "Dataset PVB QDAT hiện không có lineage (upstream/downstream) "
            "được ghi nhận trong DataHub."
        )

        report = await checker.check(
            anchor=anchor,
            intent="LINEAGE",
            answer=ans,
            resolved_entities=[FakeEntity()],
        )

        assert not report.passed
        assert any(v.violation_type == "E-CONTRA" for v in report.violations)
        assert report.corrected_answer is not None
        assert "⚠️" in report.corrected_answer

    @pytest.mark.asyncio
    async def test_correct_lineage_answer_passes(self) -> None:
        from app.services.chat.data_fidelity_checker import DataFidelityChecker

        class FakeDbEntity:
            urn = "urn:li:dataset:pvb_qdat"
            name = "PVB QDAT"
            display_name = "PVB QDAT"
            entity_type = "dataset"
            payload = {"upstreams": ["urn:li:dataset:source1"], "downstreams": []}

        class MockEntityRepo:
            async def get_by_urn(self, urn: str):
                return FakeDbEntity()

        anchor = QueryAnchor(original_query="PVB QDAT lineage?")
        anchor.add_anchor(
            EntityAnchor(
                raw_mention="PVB QDAT",
                resolved_urn="urn:li:dataset:pvb_qdat",
                resolved_name="PVB QDAT",
                confidence=AnchorConfidence.HIGH,
            )
        )

        class FakeEntity:
            urn = "urn:li:dataset:pvb_qdat"
            name = "PVB QDAT"

        checker = DataFidelityChecker(entity_repository=MockEntityRepo())
        report = await checker.check(
            anchor=anchor,
            intent="LINEAGE",
            answer="PVB QDAT có 1 upstream dataset là source1.",
            resolved_entities=[FakeEntity()],
        )
        assert report.passed
        assert not report.violations
