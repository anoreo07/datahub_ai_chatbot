"""Unit tests for grounded filter extraction and the constrained hybrid guard.

Covers:
1. ``extract_filter_values`` parses ``col = 'value'`` from natural language and
   only matches whole identifiers (never a substring like ``name`` inside
   ``warehouse_name``).
2. ``_validate_grounded_sql``: accepts read-only SELECT on allowed columns and
   rejects DDL/DML, multi-statement input, and any out-of-schema column.
"""
from app.services.action_service import extract_filter_values
from app.services.sql_llm import _validate_grounded_sql


def test_filter_extracts_quoted_value() -> None:
    out = extract_filter_values(
        "truy vấn đối tượng có warehouse_name là 'ABC123'",
        ["warehouse_name", "id", "name"],
    )
    assert out == {"warehouse_name": "ABC123"}


def test_filter_matches_full_identifier_not_substring() -> None:
    out = extract_filter_values(
        "truy vấn đối tượng có warehouse_name là 'ABC123'",
        ["name", "warehouse_name"],
    )
    assert out == {"warehouse_name": "ABC123"}
    assert "name" not in out, "name is a substring of warehouse_name and must not match"


def test_filter_with_equals_and_number() -> None:
    out = extract_filter_values("thống kê amount bằng 150", ["id", "amount", "name"])
    assert out == {"amount": "150"}


def test_filter_ignores_when_no_value() -> None:
    assert extract_filter_values("không có filter nào ở đây", ["warehouse_name"]) == {}


def test_filter_escapes_apostrophe() -> None:
    # The value extraction strips surrounding quotes; an embedded apostrophe must
    # be preserved so the caller can escape it when building the SQL literal.
    out = extract_filter_values("tìm name bằng \"O'Brien\"", ["name"])
    assert out.get("name") == "O'Brien"


def test_validate_accepts_grounded_select() -> None:
    sql = (
        "SELECT t.warehouse_name, t.warehouse_id FROM dim_warehouse AS t "
        "WHERE t.warehouse_name = 'ABC123'"
    )
    assert _validate_grounded_sql(sql, {"warehouse_name", "warehouse_id"}) is True


def test_validate_rejects_unknown_column() -> None:
    sql = "SELECT t.secret_column FROM dim_warehouse AS t"
    assert _validate_grounded_sql(sql, {"warehouse_name"}) is False


def test_validate_rejects_ddl_and_dml() -> None:
    for stmt in [
        "DROP TABLE dim_warehouse",
        "DELETE FROM dim_warehouse",
        "INSERT INTO dim_warehouse VALUES (1)",
        "ALTER TABLE dim_warehouse ADD COLUMN x",
        "UPDATE dim_warehouse SET x = 1",
    ]:
        assert _validate_grounded_sql(stmt, {"warehouse_name"}) is False


def test_validate_rejects_multi_statement() -> None:
    sql = "SELECT t.warehouse_name FROM dim_warehouse AS t; SELECT t.id FROM dim_warehouse AS t"
    assert _validate_grounded_sql(sql, {"warehouse_name"}) is False


def test_validate_allows_trailing_semicolon() -> None:
    sql = "SELECT t.warehouse_name FROM dim_warehouse AS t;"
    assert _validate_grounded_sql(sql, {"warehouse_name"}) is True
