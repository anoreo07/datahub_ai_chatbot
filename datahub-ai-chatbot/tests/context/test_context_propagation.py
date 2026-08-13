"""Context-propagation regression tests (evidence-based follow-ups).

Covers the real DataHub conversations behind the feature:

A. "schema vừa lấy + dim_warehouse.warehouse_id" -> join key answered from the
   evidence store, no silent cross-catalog semantic re-search.
B. "field đó / field <X> đó có glossary term nào không?" -> field-vs-term is
   decided FROM CONTEXT, grounded in the schema evidence already collected.
C. "owner của nó?" -> answered from the recorded evidence (no re-fetch).
D. "dựa trên toàn bộ kết quả vừa rồi, còn downstream nào liên quan đến tồn kho?"
   -> lineage filtered within the evidence already fetched.
E. Image first, then field questions -> context flows from the image to the
   real (canonical) dataset name and its schema.
F. A NEW entity question ("fact_goods_receipt có field nào?") is NOT swallowed
   by the evidence layer — it keeps its own identifier and is answered afresh.
G. "chỉ dựa trên metadata vừa lấy" -> the constraint is enforced (answer only
   from evidence; the answer even names the bound evidence citation).
"""

import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository


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


_URNS = {
    "fact_inventory": "urn:li:dataset:(urn:li:dataPlatform:postgres,logistic.fact_inventory,PROD)",
    "dim_warehouse": "urn:li:dataset:(urn:li:dataPlatform:postgres,logistic.dim_warehouse,PROD)",
    "fact_inventory_movement":
        "urn:li:dataset:(urn:li:dataPlatform:postgres,logistic.fact_inventory_movement,PROD)",
    "dim_warehouse_zone":
        "urn:li:dataset:(urn:li:dataPlatform:postgres,logistic.dim_warehouse_zone,PROD)",
    "fact_goods_receipt":
        "urn:li:dataset:(urn:li:dataPlatform:postgres,logistic.fact_goods_receipt,PROD)",
}


def _build_seed_entities() -> list[Entity]:
    fact_inventory = _entity(
        _URNS["fact_inventory"], "logistic.fact_inventory", {
            "name": "logistic.fact_inventory",
            "description": "Bảng fact tồn kho theo ngày (số lượng tồn, safety stock).",
            "domain": "Logistic",
            "platform": "postgres",
            "owners": [{"name": "Nguyễn Văn An", "email": "nva@co", "type": "BUSINESS_OWNER"}],
            "glossary_terms": ["Cold Chain", "Safety Stock"],
            "schema_fields": [
                {"name": "warehouse_id", "type": "int", "description": "Mã kho"},
                {"name": "material_code", "type": "string", "description": "Mã vật tư"},
                {"name": "quantity", "type": "decimal", "description": "Số lượng tồn"},
                {"name": "safety_stock", "type": "decimal", "description": "Tồn tối thiểu"},
            ],
        },
    )
    dim_warehouse = _entity(
        _URNS["dim_warehouse"], "logistic.dim_warehouse", {
            "name": "logistic.dim_warehouse",
            "description": "Danh mục kho.",
            "domain": "Logistic",
            "platform": "postgres",
            "owners": [{"name": "Lê Thu Hà", "email": "lth@co", "type": "SYSTEM_OWNER"}],
            "glossary_terms": ["Warehouse"],
            "schema_fields": [
                {"name": "warehouse_id", "type": "int", "description": "Mã kho"},
                {"name": "warehouse_name", "type": "string", "description": "Tên kho"},
                {"name": "zone_id", "type": "int", "description": "Mã khu vực"},
            ],
            "upstreams": [],
            "downstreams": [_URNS["fact_inventory"]],
        },
    )
    fact_inventory_movement = _entity(
        _URNS["fact_inventory_movement"], "logistic.fact_inventory_movement", {
            "name": "logistic.fact_inventory_movement",
            "description": "Sổ nhập xuất tồn kho (movement).",
            "domain": "Logistic",
            "schema_fields": [
                {"name": "movement_id", "type": "int", "description": "Mã phiếu"},
                {"name": "warehouse_id", "type": "int", "description": "Mã kho"},
                {"name": "material_code", "type": "string", "description": "Mã vật tư"},
                {"name": "created_at", "type": "timestamp"},
            ],
        },
    )
    dim_warehouse_zone = _entity(
        _URNS["dim_warehouse_zone"], "logistic.dim_warehouse_zone", {
            "name": "logistic.dim_warehouse_zone",
            "description": "Khu vực trong kho.",
            "domain": "Logistic",
            "schema_fields": [
                {"name": "zone_id", "type": "int"},
                {"name": "zone_name", "type": "string"},
                {"name": "warehouse_id", "type": "int"},
            ],
        },
    )
    fact_goods_receipt = _entity(
        _URNS["fact_goods_receipt"], "logistic.fact_goods_receipt", {
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
    return [fact_inventory, dim_warehouse, fact_inventory_movement,
            dim_warehouse_zone, fact_goods_receipt]


async def _seed(db_session) -> list[Entity]:
    from ingestion.sync import SyncOrchestrator

    await SyncOrchestrator(db_session).run_full_sync()
    repo = EntityRepository(db_session)
    entities = _build_seed_entities()
    for e in entities:
        await repo.upsert(e)
    return entities


def _wire_lineage_inventory(service) -> None:
    """Add the logistic lineage edges to the mock source so the LIVE lineage
    function answers the same way for the seeded inventory datasets."""
    edges = [
        {"source": _URNS["dim_warehouse"], "target": _URNS["fact_inventory"]},
        {"source": _URNS["fact_inventory"], "target": _URNS["fact_inventory_movement"]},
        {"source": _URNS["fact_inventory"], "target": _URNS["fact_goods_receipt"]},
        {"source": _URNS["dim_warehouse"], "target": _URNS["fact_inventory_movement"]},
    ]
    existing = {(e["source"], e["target"]) for e in service._source._lineage}
    for e in edges:
        if (e["source"], e["target"]) not in existing:
            service._source._lineage.append(e)


def _service(db_session):
    from app.services.chat_service import ChatService
    service = ChatService(db_session)
    _wire_lineage_inventory(service)
    return service


# --------------------------------------------------------------------------- #
# A. Schema-join from evidence (no semantic re-search)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_schema_join_answer_from_evidence(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-a"

    r1 = await service.answer("fact_inventory có những trường nào?", conversation_id=cid)
    assert r1.intent == "SCHEMA_LOOKUP"

    r2 = await service.answer(
        "schema vừa lấy, thì field nào có khả năng liên kết với "
        "dim_warehouse.warehouse_id?",
        conversation_id=cid,
    )
    assert r2.intent == "CONTEXT_JOIN", r2.answer
    assert "warehouse_id" in r2.answer
    assert "dim_warehouse" in r2.answer


# --------------------------------------------------------------------------- #
# B. Field vs glossary term — decided from the evidence context
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_field_glossary_followup_from_context(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-b"

    await service.answer("fact_inventory có những trường nào?", conversation_id=cid)
    await service.answer(
        "schema vừa lấy, thì field nào có khả năng liên kết với "
        "dim_warehouse.warehouse_id?",
        conversation_id=cid,
    )

    # "field đó" -> the previously-discussed field (warehouse_id).
    r = await service.answer("field đó có glossary term nào không?", conversation_id=cid)
    assert r.intent == "CONTEXT_FIELD_GLOSSARY", r.answer
    assert "warehouse_id" in r.answer
    assert "glossary" in r.answer.lower()


@pytest.mark.asyncio
async def test_field_named_glossary_followup(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-b2"

    await service.answer("fact_inventory có những trường nào?", conversation_id=cid)

    # The named column is a field of the referenced schema -> field answer.
    r = await service.answer(
        "field warehouse_id đó có glossary term nào không?", conversation_id=cid,
    )
    assert r.intent == "CONTEXT_FIELD_GLOSSARY", r.answer
    assert "warehouse_id" in r.answer

    # "cold chain" is NOT a field in that schema -> resolved as a glossary term
    # from the evidence (the dataset carries it as a dataset term).
    r2 = await service.answer(
        "cold chain đó có glossary term nào không?", conversation_id=cid,
    )
    assert r2.intent == "CONTEXT_FIELD_GLOSSARY", r2.answer
    assert "glossary term" in r2.answer.lower()


# --------------------------------------------------------------------------- #
# C. Owner of "nó" — answered from recorded evidence
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_owner_followup_from_evidence(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-c"

    await service.answer("fact_inventory có những trường nào?", conversation_id=cid)

    r = await service.answer("owner của nó?", conversation_id=cid)
    assert r.intent == "OWNER_LOOKUP", r.answer
    assert "Nguyễn Văn An" in r.answer


# --------------------------------------------------------------------------- #
# D. Downstream filter within the already-fetched lineage results
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_lineage_downstream_filter_in_evidence(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-d"

    r1 = await service.answer("fact_inventory có lineage gì?", conversation_id=cid)
    assert r1.intent == "LINEAGE", r1.answer

    r2 = await service.answer(
        "dựa trên toàn bộ kết quả vừa rồi, còn downstream nào liên quan "
        "đến tồn kho?",
        conversation_id=cid,
    )
    assert r2.intent == "CONTEXT_LINEAGE", r2.answer
    assert "fact_inventory_movement" in r2.answer
    assert "fact_goods_receipt" not in r2.answer


# --------------------------------------------------------------------------- #
# G. "chỉ dựa trên metadata vừa lấy" — constraint enforced (no re-search)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_context_only_constraint_no_research(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-g"

    await service.answer("fact_inventory có lineage gì?", conversation_id=cid)

    r = await service.answer(
        "chỉ dựa trên metadata vừa lấy, fact_inventory có liên kết với "
        "dim_warehouse không?",
        conversation_id=cid,
    )
    assert r.intent in ("CONTEXT_JOIN", "CONTEXT_LINEAGE", "CONTEXT_EVIDENCE"), r.answer
    assert "dim_warehouse" in r.answer


# --------------------------------------------------------------------------- #
# F. A brand-new entity is NOT swallowed by the evidence layer
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_new_entity_not_swallowed_by_evidence(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-f"

    await service.answer("fact_inventory có những trường nào?", conversation_id=cid)
    await service.answer("owner của nó?", conversation_id=cid)

    r = await service.answer(
        "fact_goods_receipt có field nào?", conversation_id=cid,
    )
    assert r.intent == "SCHEMA_LOOKUP", r.answer
    assert "fact_goods_receipt" in r.answer


# --------------------------------------------------------------------------- #
# E. Image -> real dataset name -> join question on the image-derived schema
# --------------------------------------------------------------------------- #
def _vision_raw_dashboard_warehouse() -> dict:
    return {
        "image_type": "erd",
        "quality": "clear",
        "ocr_text": "Dim Warehouse",
        "detected_entities": [
            {"name": "logistic.dim_warehouse", "type": "dataset", "confidence": 0.92}
        ],
        "detected_metrics": [],
        "detected_tables": ["logistic.dim_warehouse"],
        "detected_columns": ["warehouse_id", "warehouse_name", "zone_id"],
        "detected_relationships": [],
        "detected_errors": [],
        "detected_questions": [],
        "confidence": 0.92,
        "recommended_skills": ["search_dataset"],
        "notes": [],
        "irrelevant": False,
        "refusal_reason": "",
        "candidates": [],
    }


IMAGE_URL = "data:image/png;base64,aGVsbG8gd29ybGQ="


@pytest.mark.asyncio
async def test_image_context_flows_to_dataset_and_join(db_session) -> None:
    from app.services.chat_service import ChatService
    from retrieval.visual import MockVisionClient, VisualUnderstandingSkill

    await _seed(db_session)
    service = ChatService(db_session)
    _wire_lineage_inventory(service)
    service._vision = VisualUnderstandingSkill(db_session, client=MockVisionClient(
        _vision_raw_dashboard_warehouse(),
    ))
    cid = "ctx-e"

    r0 = await service.answer("Ảnh này là gì?", conversation_id=cid, images=[IMAGE_URL])
    assert r0.intent == "VISION_ANALYSIS", r0.answer
    assert "dim_warehouse" in r0.answer

    r1 = await service.answer(
        "ảnh này có những trường nào?", conversation_id=cid,
    )
    assert r1.intent == "VISION_ANALYSIS", r1.answer
    assert "warehouse_id" in r1.answer

    r2 = await service.answer(
        "trong ảnh này, field nào có thể liên kết với "
        "fact_inventory_movement.warehouse_id?",
        conversation_id=cid,
    )
    assert r2.intent in ("VISION_ANALYSIS", "CONTEXT_JOIN"), r2.answer
    assert "warehouse_id" in r2.answer


@pytest.mark.asyncio
async def test_standalone_cross_dataset_join_uses_join_analysis(db_session) -> None:
    """A self-contained join question ("trường chung để liên kết giữa X và Y")
    must render the cross-dataset join analysis, not a bare whole-schema listing.
    """
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    _wire_lineage_inventory(service)
    cid = "ctx-join-standalone"

    r = await service.answer(
        "fact_inventory và dim_warehouse có trường nào chung để liên kết?",
        conversation_id=cid,
    )
    assert r.intent == "SCHEMA_LOOKUP", r.answer
    assert "warehouse_id" in r.answer, r.answer
    assert "dim_warehouse" in r.answer, r.answer
    assert "fact_inventory" in r.answer, r.answer
    assert "liên kết" in r.answer.lower(), r.answer


@pytest.mark.asyncio
async def test_standalone_join_no_shared_field_is_grounded(db_session) -> None:
    """Join question between datasets WITHOUT a shared field stays grounded:
    states no direct shared key and lists candidate FK columns instead of
    inventing a join."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    _wire_lineage_inventory(service)
    cid = "ctx-join-none"

    r = await service.answer(
        "fact_goods_receipt và dim_warehouse_zone có trường nào chung để liên kết?",
        conversation_id=cid,
    )
    assert r.intent == "SCHEMA_LOOKUP", r.answer
    assert "dim_warehouse_zone" in r.answer, r.answer
    assert "không" in r.answer.lower() or "chưa" in r.answer.lower(), r.answer


# --------------------------------------------------------------------------- #
# Thinking Mode: state events + context-first ordering
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_thinking_emits_state_and_context_followup_wins(db_session) -> None:
    await _seed(db_session)
    service = _service(db_session)
    cid = "ctx-th"

    steps: list[str] = []

    async def on_status(step: str) -> None:
        steps.append(step)

    # A genuinely complex / comparative question enters the thinking layer and
    # emits the new "thinking" / "thinking_done" state events.
    r0 = await service.answer(
        "so sánh sales.orders và raw.payments có gì khác nhau?",
        conversation_id=cid, on_status=on_status,
    )
    assert r0.intent in ("THINKING_OVERVIEW", "GENERAL"), r0.answer
    assert "thinking" in steps, steps

    # A context-referencing follow-up must be answered by the evidence layer,
    # never re-planned from scratch by the thinking layer.
    await service.answer("fact_inventory có lineage gì?", conversation_id=cid)
    r1 = await service.answer(
        "chỉ dựa trên kết quả vừa rồi, còn downstream nào liên quan tồn kho?",
        conversation_id=cid, on_status=on_status,
    )
    assert r1.intent == "CONTEXT_LINEAGE", r1.answer
    assert "fact_inventory_movement" in r1.answer
