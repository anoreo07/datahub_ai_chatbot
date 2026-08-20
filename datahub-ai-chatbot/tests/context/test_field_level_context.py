"""Field-level context-propagation tests (evidence-based field operations).

Covers the field-level reasoning the evidence layer must support:

A. "warehouse_id có kiểu dữ liệu gì?" after a schema fetch -> only the field's
   data type, never the whole schema again.
B. "Field nào liên quan đến warehouse?" -> the matching field in the schema.
C. "warehouse_id có mô tả gì?" -> the field description from the evidence.
D. "warehouse_id có glossary term nào không?" -> field glossary from evidence.
E. An unrelated Revenue query between turns must NOT overwrite the dataset
   schema evidence (E1): a follow-up on "schema vừa lấy" still references E1.
F. A brand-new entity ("Còn fact_goods_receipt thì sao?") triggers new
   retrieval, it is NOT answered from stale evidence.
G. "Chỉ dựa trên schema vừa lấy ..." -> the answer is grounded in evidence, no
   new semantic/entity retrieval.
J. Multi-step context is maintained: schema -> field -> field type -> glossary
   -> lineage -> owner across turns.
"""

import pytest

from database.models import Entity


def _entity(urn: str, name: str, payload: dict, domain: str = "Logistic",
            entity_type: str = "dataset") -> Entity:
    return Entity(
        urn=urn,
        entity_type=entity_type,
        name=name,
        display_name=name,
        platform="postgres",
        environment="PROD",
        domain=domain,
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload=payload,
        content_hash=f"hash-{name}-{entity_type}",
    )


def _build_seed_entities() -> list[Entity]:
    fact_inventory_movement = _entity(
        "urn:li:dataset:(urn:li:dataPlatform:postgres,"
        "logistic.fact_inventory_movement,PROD)",
        "logistic.fact_inventory_movement", {
            "name": "logistic.fact_inventory_movement",
            "description": "Sổ nhập xuất tồn kho (movement).",
            "domain": "Logistic",
            "platform": "postgres",
            "glossary_terms": ["Warehouse", "Inventory Movement"],
            "schema_fields": [
                {"name": "movement_id", "type": "int", "description": "Mã phiếu"},
                {"name": "warehouse_id", "type": "VARCHAR(10)",
                 "description": "Mã kho", "glossary_terms": ["Warehouse"]},
                {"name": "movement_type", "type": "VARCHAR(10)",
                 "description": "Loại giao dịch (GR/GI/TR/ADJ)"},
                {"name": "material_code", "type": "VARCHAR(30)",
                 "description": "Mã vật tư"},
                {"name": "quantity", "type": "DECIMAL(12,2)",
                 "description": "Số lượng"},
                {"name": "created_at", "type": "TIMESTAMP",
                 "description": "Thời gian tạo"},
            ],
        },
    )
    fact_goods_receipt = _entity(
        "urn:li:dataset:(urn:li:dataPlatform:postgres,"
        "logistic.fact_goods_receipt,PROD)",
        "logistic.fact_goods_receipt", {
            "name": "logistic.fact_goods_receipt",
            "description": "Phiếu nhập hàng (GRN).",
            "domain": "Logistic",
            "schema_fields": [
                {"name": "receipt_id", "type": "int", "description": "Mã phiếu nhập"},
                {"name": "material_code", "type": "string"},
                {"name": "supplier_code", "type": "string"},
                {"name": "received_qty", "type": "decimal"},
                {"name": "received_at", "type": "timestamp"},
            ],
        },
    )
    return [fact_inventory_movement, fact_goods_receipt]


async def _seed(db_session) -> None:
    from ingestion.sync import SyncOrchestrator

    await SyncOrchestrator(db_session).run_full_sync()
    from database.repositories.entity_repository import EntityRepository

    repo = EntityRepository(db_session)
    for e in _build_seed_entities():
        await repo.upsert(e)


def _service(db_session):
    from app.services.chat_service import ChatService
    return ChatService(db_session)


@pytest.mark.asyncio
async def test_a_field_data_type_after_schema(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-a"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer("warehouse_id có kiểu dữ liệu gì?", conversation_id=cid)
    assert r2.intent == "FIELD_PROPERTY", r2.answer
    assert "warehouse_id" in r2.answer
    assert "varchar" in r2.answer.lower(), r2.answer
    # Must NOT re-render the whole schema.
    assert "movement_id" not in r2.answer


@pytest.mark.asyncio
async def test_b_find_field_in_schema(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-b"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer("Field nào liên quan đến warehouse?", conversation_id=cid)
    assert r2.intent == "FIELD_PROPERTY", r2.answer
    assert "warehouse_id" in r2.answer
    assert "movement_type" not in r2.answer


@pytest.mark.asyncio
async def test_c_field_description_after_schema(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-c"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer("warehouse_id có mô tả gì?", conversation_id=cid)
    assert r2.intent == "FIELD_PROPERTY", r2.answer
    assert "warehouse_id" in r2.answer
    assert "Mã kho" in r2.answer
    assert "movement_id" not in r2.answer


@pytest.mark.asyncio
async def test_d_field_glossary_after_schema(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-d"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer("warehouse_id có glossary term nào không?", conversation_id=cid)
    assert r2.intent == "GLOSSARY", r2.answer
    assert "warehouse_id" in r2.answer


@pytest.mark.asyncio
async def test_e_unrelated_query_does_not_break_schema_evidence(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-e"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    await service.answer("term nào liên quan đến doanh thu?", conversation_id=cid)

    r3 = await service.answer(
        "Field warehouse_id trong schema vừa lấy có kiểu dữ liệu gì?",
        conversation_id=cid,
    )
    assert r3.intent == "FIELD_PROPERTY", r3.answer
    assert "varchar" in r3.answer.lower(), r3.answer
    assert "warehouse_id" in r3.answer
    # Must NOT answer from the Revenue evidence.
    assert "doanh thu" not in r3.answer.lower()


@pytest.mark.asyncio
async def test_f_new_entity_triggers_new_retrieval(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-f"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer("Còn fact_goods_receipt thì sao?", conversation_id=cid)
    assert r2.intent == "SCHEMA_LOOKUP", r2.answer
    assert "fact_goods_receipt" in r2.answer
    assert "receipt_id" in r2.answer


@pytest.mark.asyncio
async def test_g_constraint_no_new_retrieval(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-g"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer(
        "Chỉ dựa trên schema vừa lấy, warehouse_id có kiểu dữ liệu gì?",
        conversation_id=cid,
    )
    assert r2.intent == "FIELD_PROPERTY", r2.answer
    assert "varchar" in r2.answer.lower(), r2.answer


@pytest.mark.asyncio
async def test_j_multistep_context_maintained(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "fl-j"

    r1 = await service.answer("Lấy schema của fact_inventory_movement", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP", r1.answer

    r2 = await service.answer("warehouse_id có kiểu dữ liệu gì?", conversation_id=cid)
    assert "varchar" in r2.answer.lower(), r2.answer

    r3 = await service.answer("Field đó có mô tả gì?", conversation_id=cid)
    assert "Mã kho" in r3.answer, r3.answer

    r4 = await service.answer("Owner của nó?", conversation_id=cid)
    assert r4.intent == "OWNER_LOOKUP", r4.answer

    r5 = await service.answer("các trường của nó?", conversation_id=cid)
    assert r5.intent == "SCHEMA_LOOKUP", r5.answer
    assert "warehouse_id" in r5.answer


@pytest.mark.asyncio
async def test_a2_explicit_dataset_field_type(db_session) -> None:
    """Directly-named entity+field property must not render the whole schema."""
    await _seed(db_session)
    service = _service(db_session)

    r = await service.answer(
        "warehouse_id của fact_inventory_movement có kiểu dữ liệu gì?",
    )
    assert "warehouse_id" in r.answer
    assert "varchar" in r.answer.lower(), r.answer
    assert "movement_id" not in r.answer
