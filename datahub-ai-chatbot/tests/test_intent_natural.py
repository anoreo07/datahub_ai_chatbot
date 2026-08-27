"""Natural language intent detection tests (casual & formal Vietnamese queries)."""

import pytest

from retrieval.intent import QueryIntent, classify_intent, detect_intent


@pytest.mark.parametrize(
    ("query", "expected_intent"),
    [
        # Lineage (casual & formal)
        ("Bảng này lấy dữ liệu từ đâu?", QueryIntent.LINEAGE),
        ("bảng nào feed vào fact_sales", QueryIntent.LINEAGE),
        ("ai feed data vào dim_warehouse?", QueryIntent.LINEAGE),
        ("dữ liệu từ đâu ra vậy?", QueryIntent.LINEAGE),
        ("nguồn dữ liệu của bảng sales_order", QueryIntent.LINEAGE),
        ("data đến từ đâu?", QueryIntent.LINEAGE),
        ("bảng nào phụ thuộc vào dim_customer", QueryIntent.LINEAGE),
        ("kế thừa từ dataset nào", QueryIntent.LINEAGE),
        ("upstream của fact_revenue là gì?", QueryIntent.LINEAGE),
        ("downstream của dim_warehouse", QueryIntent.LINEAGE),

        # Glossary / Term Definition (casual & formal)
        ("Công thức tính Coverage date là gì?", QueryIntent.TERM_DEFINITION),
        ("Hiểu sao về term MRP?", QueryIntent.TERM_DEFINITION),
        ("Cách tính Net Revenue", QueryIntent.TERM_DEFINITION),
        ("giải thích cho tôi thuật ngữ Component Demand", QueryIntent.TERM_DEFINITION),
        ("KPI Gross Margin được tính như thế nào?", QueryIntent.TERM_DEFINITION),
        ("Ý nghĩa của term Gross Margin", QueryIntent.TERM_DEFINITION),
        ("Định nghĩa thuật ngữ BOM", QueryIntent.TERM_DEFINITION),
        ("khái niệm Part Demand là gì?", QueryIntent.TERM_DEFINITION),

        # Schema Lookup (casual & formal)
        ("Bảng dim_customer có những cột nào?", QueryIntent.SCHEMA_LOOKUP),
        ("cấu trúc bảng fact_orders gồm những trường nào?", QueryIntent.SCHEMA_LOOKUP),
        ("sales_order có bao nhiêu cột?", QueryIntent.SCHEMA_LOOKUP),
        ("danh sách cột của dim_warehouse", QueryIntent.SCHEMA_LOOKUP),
        ("bảng có field gì?", QueryIntent.SCHEMA_LOOKUP),
        ("schema của fact_inventory", QueryIntent.SCHEMA_LOOKUP),

        # Data Quality (casual & formal)
        ("Data của bảng này có tốt không?", QueryIntent.QUALITY_CHECK),
        ("dữ liệu có đầy đủ không?", QueryIntent.QUALITY_CHECK),
        ("bao nhiêu null trong bảng customer?", QueryIntent.QUALITY_CHECK),
        ("bảng này có lỗi không?", QueryIntent.QUALITY_CHECK),
        ("kiểm tra data quality cho dataset dim_product", QueryIntent.QUALITY_CHECK),
        ("dữ liệu đã mới chưa, freshness thế nào?", QueryIntent.QUALITY_CHECK),

        # Owner Lookup (casual & formal)
        ("Ai quản lý bảng dim_warehouse?", QueryIntent.OWNER_LOOKUP),
        ("Ai chịu trách nhiệm về dataset fact_sales?", QueryIntent.OWNER_LOOKUP),
        ("team nào phụ trách bảng này?", QueryIntent.OWNER_LOOKUP),
        ("liên hệ ai khi bảng bị lỗi?", QueryIntent.OWNER_LOOKUP),
        ("chủ sở hữu của dim_customer là ai?", QueryIntent.OWNER_LOOKUP),
        ("ai sở hữu bảng finance.monthly_revenue?", QueryIntent.OWNER_LOOKUP),

        # Greeting & Chitchat
        ("Xin chào", QueryIntent.GREETING),
        ("hello bot", QueryIntent.GREETING),
        ("Chào bạn", QueryIntent.GREETING),
        ("Bạn khỏe không?", QueryIntent.CHITCHAT),
        ("Bạn là ai?", QueryIntent.CHITCHAT),
        ("Cảm ơn bạn nhé", QueryIntent.CHITCHAT),
    ],
)
def test_casual_and_formal_intent_accuracy(query: str, expected_intent: QueryIntent) -> None:
    intent = classify_intent(query)
    assert intent == expected_intent, (
        f"Query '{query}' classified as {intent}, expected {expected_intent}"
    )



def test_detect_intent_alias() -> None:
    assert detect_intent("lấy dữ liệu từ đâu") == QueryIntent.LINEAGE
    assert detect_intent("hello") == QueryIntent.GREETING
