"""Tests for Phase 1-7 features: Confirmation, Entity Detection, Missing Metadata, Field Property."""


from retrieval.confirmation import ConfirmationDetector
from retrieval.entity_detection import EntityNameDetector
from retrieval.intent import QueryIntent, classify_intent


class TestConfirmationDetector:
    """Tests for stateless ConfirmationDetector."""

    def test_detect_confirm_vng(self):
        detector = ConfirmationDetector()
        history = [
            ("tìm dataset vgreen", "Ý bạn là domain 'vgreen' đúng không?"),
        ]
        result = detector.detect("đúng", history)
        assert result.action == "confirm"

    def test_detect_deny(self):
        detector = ConfirmationDetector()
        history = [
            ("tìm dataset vgreen", "Ý bạn là domain 'vgreen' đúng không?"),
        ]
        result = detector.detect("không phải", history)
        assert result.action == "deny"

    def test_detect_new_query(self):
        detector = ConfirmationDetector()
        history = [
            ("tìm dataset vgreen", "Đây là thông tin về dataset..."),
        ]
        result = detector.detect("tìm report mới", history)
        assert result.action == "new_query"

    def test_detect_no_history(self):
        detector = ConfirmationDetector()
        result = detector.detect("hello", [])
        assert result.action == "new_query"


class TestEntityNameDetector:
    """Tests for EntityNameDetector (snake_case, dotted path, etc.)."""

    def test_snake_case_detection(self):
        detector = EntityNameDetector()
        result = detector.detect("plant_id")
        assert result.is_entity_name
        assert "snake_case" in result.signals

    def test_dotted_path_signal(self):
        detector = EntityNameDetector()
        result = detector.detect("schema.table.column")
        # Dotted path detected as signal, but needs 4+ signals total
        assert "dotted_path" in result.signals

    def test_quoted_detection(self):
        detector = EntityNameDetector()
        result = detector.detect("'Analyse Product Cost Collector'")
        assert result.is_entity_name
        assert "quoted" in result.signals

    def test_no_detection(self):
        detector = EntityNameDetector()
        result = detector.detect("tìm dataset cost collector")
        assert len(result.signals) < 4


class TestIntentClassification:
    """Tests for new intents."""

    def test_missing_domain_intent(self):
        intent = classify_intent("dataset thiếu domain")
        assert intent == QueryIntent.MISSING_DOMAIN

    def test_schema_lookup_still_works(self):
        intent = classify_intent("có những field nào trong dataset cost collector")
        assert intent == QueryIntent.SCHEMA_LOOKUP

    def test_count_still_works(self):
        intent = classify_intent("có bao nhiêu dataset")
        assert intent == QueryIntent.COUNT_ENTITIES

    def test_domain_listing_still_works(self):
        intent = classify_intent("liệt kê domain")
        assert intent == QueryIntent.DOMAIN_QUERY
