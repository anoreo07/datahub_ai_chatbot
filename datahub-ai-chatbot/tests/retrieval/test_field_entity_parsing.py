
from retrieval.evidence import (
    extract_field_entity,
    parse_field_operation,
)


def test_entity_first_quoted_dataset() -> None:
    """'trong dataset "X" có trường "Y" nghĩa là gì?' names the entity before
    the field; the parser must extract (entity, field) in that order."""
    entity, field = extract_field_entity(
        'trong dataset "dim_businessunit" có trường "bu_short_name" nghĩa là gì?'
    )
    assert entity == "dim_businessunit"
    assert field == "bu_short_name"


def test_entity_first_unquoted_dataset() -> None:
    entity, field = extract_field_entity(
        "trong dataset fact_sale_orders có trường sod_total_amount nghĩa là gì?"
    )
    assert entity == "fact_sale_orders"
    assert field == "sod_total_amount"


def test_entity_first_parse_field_operation() -> None:
    op = parse_field_operation(
        'trong dataset "dim_plant" có trường "is_manufacturing" nghĩa là gì?'
    )
    assert op is not None
    assert op.field == "is_manufacturing"
    assert op.property == "description"


def test_entity_first_does_not_match_discovery_questions() -> None:
    """Discovery / domain questions must not be hijacked by the field pattern."""
    for q in (
        "nhu cầu linh kiện trong domain SẢN XUẤT",
        "các dashboard về doanh thu 2025",
        "trong tháng này có bao nhiêu entity WIP",
    ):
        entity, field = extract_field_entity(q)
        assert "trường" not in q.lower() or field is None
