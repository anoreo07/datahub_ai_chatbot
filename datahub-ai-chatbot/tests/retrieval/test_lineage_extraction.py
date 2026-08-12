from app.services.chat_service import ChatService

_LINEAGE_REMOVE = [
    "lấy dữ liệu từ đâu", "upstream", "downstream",
    "nguồn", "phụ thuộc", "source of data",
    "thông tin về lineage", "thông tin về linage",
    "lineage", "linage", "thông tin", "thong tin",
]


def _extract(query: str) -> str:
    return ChatService._extract_name(query, _LINEAGE_REMOVE)


def test_lineage_extracts_entity_name() -> None:
    assert _extract(
        "thông tin về lineage của dataset dim_inventory_category"
    ) == "dim inventory category"
    assert _extract(
        "thông tin về linage của dataset dim_inventory_category"
    ) == "dim inventory category"
    assert _extract("lineage của dim_inventory_category") == "dim inventory category"
    assert _extract("upstream của dim_inventory_category") == "dim inventory category"
    assert _extract("dim_inventory_category lấy dữ liệu từ đâu?") == "dim inventory category"
    assert _extract("upstream of sales.orders") == "sales orders"


def test_lineage_extract_keeps_entity_words() -> None:
    assert _extract("lineage của fact_general_ledger") == "fact general ledger"
    assert _extract("dim_material lấy dữ liệu từ đâu?") == "dim material"
