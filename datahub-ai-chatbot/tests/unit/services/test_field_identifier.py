"""Regression tests for implicit schema-field identification.

Requirement #2: when a user names a column directly (e.g. "warehouse_id là gì?")
without the words "trường/field", the pipeline must treat the identifier as a
schema field instead of normalizing it and letting the glossary resolver blur it
into an unrelated fuzzy match.
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
