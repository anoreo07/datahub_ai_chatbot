"""Regression tests for implicit schema-field identification.

Requirement #2: when a user names a column directly (e.g. "warehouse_id là gì?")
without the words "trường/field", the pipeline must treat the identifier as a
schema field instead of normalizing it and letting the glossary resolver blur it
into an unrelated fuzzy match.

Bug fix: "Dataset X có trường gì?" must NOT extract "g" from "gì" (Vietnamese
question word "what").  The regex must reject single-char and question-word
candidates.
"""

import pytest

from app.services.chat_service import ChatService


@pytest.mark.parametrize(
    "question,expected",
    [
        ("warehouse_id là gì?", "warehouse_id"),
        ("uom_name là gì?", "uom_name"),
        ("order_id là gì?", "order_id"),
        ("for the quantity_on_hand column", "quantity_on_hand"),
        ("schema của dim.tbl_orders", "dim.tbl_orders"),
    ],
)
def test_extract_field_identifier_detects_snake_case(question: str, expected: str) -> None:
    assert ChatService._extract_field_identifier(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "doanh thu là gì?",
        "lĩnh vực của dashboard là gì?",
        "đơn hàng được tạo khi nào?",
        "fdf có gì?",
    ],
)
def test_extract_field_identifier_returns_none_for_non_column(question: str) -> None:
    # In these cases the identifier regex must find no snake/dotted word.
    result = ChatService._extract_field_identifier(question)
    assert result is None


@pytest.mark.parametrize(
    "question",
    [
        "Dataset Báo cáo BOM có trường gì?",
        "Dataset Dim_BaoCaoLayout có trường gì?",
        "Dataset account có trường gì?",
        "Dataset customer có trường gì?",
        "X có những trường nào?",
        "có trường gì?",
        "trường gì?",
        "cột gì?",
        "field gì?",
    ],
)
def test_extract_field_identifier_rejects_vietnamese_question_words(question: str) -> None:
    """'gì' (what) is a Vietnamese question word, NOT a field name.

    Bug fix: the regex [a-z0-9_]+ could only match ASCII letters, so "gì"
    was truncated to "g" which was returned as a field name.
    """
    result = ChatService._extract_field_identifier(question)
    assert result is None, f"Expected None for '{question}', got '{result}'"
