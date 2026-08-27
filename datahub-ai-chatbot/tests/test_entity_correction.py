"""Tests for entity suggestion, typo correction note generation, and adaptive fuzzy matching."""

from app.services.chat.entity_suggestion import (
    EntityCorrection,
    EntitySuggestionService,
)
from retrieval.fuzzy import (
    adaptive_fuzzy_threshold,
    fuzzy_score,
    split_identifier_segments,
)


def test_build_correction_note_exact_no_typo() -> None:
    """When user types the exact entity name, no correction note should be output."""
    corrections = [
        EntityCorrection(
            original_name="dim_warehouse",
            corrected_name="dim_warehouse",
            confidence=1.0,
            entity_type="dataset",
        )
    ]
    note = EntitySuggestionService.build_correction_note(corrections)
    assert note == ""


def test_build_correction_note_with_typo() -> None:
    """When user types a typo (dim_BaoCeoLayout), the correction note must clearly inform."""
    corrections = [
        EntityCorrection(
            original_name="dim_BaoCeoLayout",
            corrected_name="dim_BaoCaoLayout",
            confidence=0.9375,
            entity_type="dataset",
            correction_type="fuzzy",
        )
    ]
    note = EntitySuggestionService.build_correction_note(corrections)
    assert "> ⚠️ **Lưu ý**:" in note
    assert "dim_BaoCaoLayout" in note
    assert "dim_BaoCeoLayout" in note


def test_build_correction_note_english() -> None:
    corrections = [
        EntityCorrection(
            original_name="sales_ordr",
            corrected_name="sales_order",
            confidence=0.90,
            entity_type="dataset",
        )
    ]
    note = EntitySuggestionService.build_correction_note(corrections, language="en")
    assert "> ⚠️ **Note**:" in note
    assert "sales_order" in note
    assert "sales_ordr" in note


def test_format_multiple_suggestions() -> None:
    candidates = [
        ("dim_customer", 0.78),
        ("dim_custom_order", 0.65),
    ]
    formatted = EntitySuggestionService.format_multiple_suggestions("customr", candidates)
    assert "Không tìm thấy thực thể chính xác cho **customr**" in formatted
    assert "dim_customer" in formatted
    assert "78%" in formatted


def test_adaptive_fuzzy_threshold() -> None:
    # Short names (<= 5 chars) require high precision
    assert adaptive_fuzzy_threshold("mrp") == 0.85
    assert adaptive_fuzzy_threshold("sales") == 0.85

    # Medium names (6-12 chars)
    assert adaptive_fuzzy_threshold("customer") == 0.80
    assert adaptive_fuzzy_threshold("fact_sales") == 0.80

    # Long names (> 12 chars) allow distance tolerance
    assert adaptive_fuzzy_threshold("dim_BaoCeoLayout") == 0.75
    assert adaptive_fuzzy_threshold("fact_monthly_revenue_report") == 0.75


def test_split_identifier_segments() -> None:
    assert split_identifier_segments("dim_BaoCeoLayout") == ["dim", "bao", "ceo", "layout"]
    assert split_identifier_segments("fact_sales_order") == ["fact", "sales", "order"]
    assert split_identifier_segments("PartDemand") == ["part", "demand"]
    assert split_identifier_segments("sales.order_details") == ["sales", "order", "details"]


def test_fuzzy_score_typo_matching() -> None:
    # CamelCase typo
    sc1 = fuzzy_score("dim_BaoCeoLayout", "dim_BaoCaoLayout")
    assert sc1 >= 0.85

    # Snake_case typo
    sc2 = fuzzy_score("fact_sales_ordr", "fact_sales_order")
    assert sc2 >= 0.85

    # Space/diacritic typo
    sc3 = fuzzy_score("nhu cau linh kien", "Nhu cầu linh kiện")
    assert sc3 >= 0.95
