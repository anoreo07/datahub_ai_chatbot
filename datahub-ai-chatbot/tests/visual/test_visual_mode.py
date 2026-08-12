"""Regression tests for the Visual Understanding layer.

Covers: dashboard, ERD, SQL, SQL-error, metadata, data-dictionary, lineage,
requirement, table/excel screenshots; blurry / too-small / cropped images;
irrelevant (non-data) images; and multiple candidate entities.
"""

import json

import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.visual import MockVisionClient, VisionImageType, VisionQuality, VisionResult
from retrieval.visual.parser import build_result
from retrieval.visual.skill import VisualUnderstandingSkill

IMAGE_URL = "data:image/png;base64,aGVsbG8gd29ybGQ="


def _raw(**overrides):
    base = {
        "image_type": "dashboard",
        "quality": "clear",
        "ocr_text": "Doanh thu theo thang",
        "detected_entities": [
            {"name": "sales.orders", "type": "dataset", "confidence": 0.9}
        ],
        "detected_metrics": ["Doanh thu"],
        "detected_tables": ["sales.orders"],
        "detected_columns": ["order_id", "total_amount"],
        "detected_relationships": ["fact_sales --< dim_date"],
        "detected_errors": [],
        "detected_questions": ["dashboard nay dung dataset nao?"],
        "confidence": 0.9,
        "recommended_skills": ["search_dataset"],
        "notes": [],
        "irrelevant": False,
        "refusal_reason": "",
        "candidates": [],
    }
    base.update(overrides)
    return base


async def _seed(db_session) -> None:
    from ingestion.sync import SyncOrchestrator

    await SyncOrchestrator(db_session).run_full_sync()


def _skill(db_session, raw: dict) -> VisualUnderstandingSkill:
    return VisualUnderstandingSkill(
        db_session, client=MockVisionClient(raw)
    )


# --------------------------------------------------------------------------- #
# Parser / normalisation
# --------------------------------------------------------------------------- #
def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)


def _p(raw: str) -> VisionResult:
    import re

    text = raw.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return build_result(json.loads(text))


class TestParser:
    def test_parse_full_json(self) -> None:
        res = _p('{"image_type":"erd","ocr_text":"fact table","confidence":0.8}')
        assert res.image_type == VisionImageType.ERD
        assert res.ocr_text == "fact table"
        assert res.confidence == 0.8

    def test_parse_with_markdown_fence(self) -> None:
        res = _p('```json\n{"image_type":"sql","confidence":0.7}\n```')
        assert res.image_type == VisionImageType.SQL

    def test_parse_with_noise_around(self) -> None:
        res = _p('Here you go: {"image_type":"lineage"} tail')
        assert res.image_type == VisionImageType.LINEAGE

    def test_parse_empty(self) -> None:
        res = _p("{}")
        assert res.image_type == VisionImageType.UNKNOWN

    def test_type_alias_sql_screenshot(self) -> None:
        res = _p('{"image_type":"sql_screenshot"}')
        assert res.image_type == VisionImageType.SQL

    def test_type_alias_not_data(self) -> None:
        res = _p('{"image_type":"not_data","irrelevant":true}')
        assert res.image_type == VisionImageType.IRRELEVANT
        assert res.irrelevant


# --------------------------------------------------------------------------- #
# Skill scenarios
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_skill_dashboard_screenshot(db_session) -> None:
    await _seed(db_session)
    skill = _skill(db_session, _raw())
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.DASHBOARD
    assert "sales.orders" in result.all_mentioned()
    assert "search_dataset" in result.recommended_skills
    md = skill.render_evidence(result)
    assert "dashboard screenshot" in md


@pytest.mark.asyncio
async def test_skill_erd(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="erd", detected_tables=["dim_customer", "fact_sales"],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.ERD
    assert "schema_analysis" in result.recommended_skills


@pytest.mark.asyncio
async def test_skill_sql(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="sql",
        ocr_text="SELECT warehouse_id, COUNT(*) FROM sales.orders GROUP BY warehouse_id",
        detected_tables=["sales.orders"],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.SQL


@pytest.mark.asyncio
async def test_skill_sql_error(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="sql_error",
        detected_errors=[{
            "message": "column order_date not found",
            "code": "1054",
            "hint": "column missing in table",
        }],
        ocr_text="SELECT order_date FROM sales.orders",
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.SQL_ERROR
    assert result.detected_errors
    assert result.detected_errors[0]["message"].startswith("column")


@pytest.mark.asyncio
async def test_skill_metadata(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="metadata",
        detected_entities=[{
            "name": "finance.monthly_revenue", "type": "dataset", "confidence": 0.95,
        }],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.METADATA
    assert "metadata_summary" in result.recommended_skills


@pytest.mark.asyncio
async def test_skill_data_dictionary_requirement(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="requirement",
        detected_metrics=["OTIF"],
        detected_columns=["delivery_date"],
        ocr_text="OTIF = on-time + in-full",
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.REQUIREMENT
    assert "generate_sql" in result.recommended_skills
    assert "OTIF" in result.detected_metrics


@pytest.mark.asyncio
async def test_skill_table_excel(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="table",
        detected_columns=["warehouse_id", "vehicle_id", "delivery_date"],
        ocr_text="warehouse_id | vehicle_id | delivery_date",
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.TABLE
    assert "warehouse_id" in result.detected_columns


@pytest.mark.asyncio
async def test_skill_lineage(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="lineage",
        detected_relationships=[
            "fact_sales -> dashboard",
            "dim_customer -> fact_sales",
        ],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.LINEAGE
    assert "lineage" in result.recommended_skills


@pytest.mark.asyncio
async def test_skill_workflow(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="workflow",
        detected_relationships=["Ingest -> Transform -> Publish"],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.WORKFLOW
    assert "impact_analysis" in result.recommended_skills


@pytest.mark.asyncio
async def test_skill_access_permission(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="access_permission",
        ocr_text="Access denied: role viewer on sales.orders",
        detected_entities=[{"name": "sales.orders", "type": "dataset", "confidence": 0.8}],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.image_type == VisionImageType.ACCESS_PERMISSION


# --------------------------------------------------------------------------- #
# Low quality / refused
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_skill_blurry_low_confidence(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="dashboard", quality="blurry", confidence=0.2, ocr_text="",
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.quality == VisionQuality.BLURRY
    assert result.confidence <= 0.35
    md = skill.render_evidence(result)
    assert "chưa đọc rõ" in md


@pytest.mark.asyncio
async def test_skill_too_small(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="table", quality="too_small", confidence=0.1,
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.quality == VisionQuality.TOO_SMALL


@pytest.mark.asyncio
async def test_skill_irrelevant_refuses(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="irrelevant", irrelevant=True,
        refusal_reason="Ảnh chụp chân dung, không liên quan dữ liệu",
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.irrelevant
    assert result.refusal_reason
    md = skill.render_evidence(result)
    assert "không liên quan" in md


# --------------------------------------------------------------------------- #
# Candidates / ambiguous
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_skill_multiple_candidates_not_auto_selected(db_session) -> None:
    skill = _skill(db_session, _raw(
        image_type="table",
        candidates=[{
            "detected": "revenue",
            "candidates": [
                {"name": "finance.monthly_revenue", "type": "dataset", "confidence": 0.6},
                {"name": "fact_revenue", "type": "dataset", "confidence": 0.5},
            ],
        }],
    ))
    result = await skill.analyze(IMAGE_URL)
    assert result.candidates
    assert len(result.candidates[0].candidates) == 2
    md = skill.render_evidence(result)
    assert "Candidates" in md


# --------------------------------------------------------------------------- #
# Image input validation (data URL)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_invalid_data_url_rejected(db_session) -> None:
    skill = _skill(db_session, _raw())
    result = await skill.analyze("not-a-data-url")
    assert result.irrelevant
    assert result.refusal_reason


@pytest.mark.asyncio
async def test_non_image_mime_rejected(db_session) -> None:
    skill = _skill(db_session, _raw())
    result = await skill.analyze("data:text/plain;base64,aGVsbG8=")
    assert result.irrelevant


# --------------------------------------------------------------------------- #
# ChatService wiring
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_chat_service_vision_wiring(db_session) -> None:
    from app.schemas.chat import ChatResponse
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())

    response = await service.answer(
        question="Ảnh này là dashboard gì?",
        images=[IMAGE_URL],
    )
    assert isinstance(response, ChatResponse)
    assert response.intent == "VISION_ANALYSIS"
    assert response.vision is not None
    assert response.vision["image_type"] == "dashboard"


@pytest.mark.asyncio
async def test_chat_service_vision_refused(db_session) -> None:
    from app.schemas.chat import ChatResponse
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw(
        image_type="irrelevant", irrelevant=True, refusal_reason="không liên quan",
    ))

    response = await service.answer(question="xem ảnh", images=[IMAGE_URL])
    assert isinstance(response, ChatResponse)
    assert response.intent == "VISION_REFUSED"


@pytest.mark.asyncio
async def test_no_images_falls_through_to_normal_pipeline(db_session) -> None:
    from app.schemas.chat import ChatResponse
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)

    response = await service.answer(question="Term Revenue nghĩa là gì?")
    assert isinstance(response, ChatResponse)
    assert response.intent != "VISION_ANALYSIS"
    assert response.vision is None


# --------------------------------------------------------------------------- #
# IMAGE = CONTEXT, NOT INTENT — function routing takes precedence
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_image_entity_routed_to_real_lineage_flow(db_session) -> None:
    """A lineage follow-up after an upload runs the real lineage function against
    the image-derived dataset instead of an image-context dump."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())  # identifies "sales.orders"

    response = await service.answer(question="nó có lineage gì?", images=[IMAGE_URL])
    assert response.intent == "LINEAGE"
    assert "sales.orders" in response.answer


@pytest.mark.asyncio
async def test_self_contained_question_keeps_own_entity_over_image(db_session) -> None:
    """A self-contained question naming a catalog entity keeps that entity even
    when an image is active (explicit intent beats image-derived context)."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())  # image says "sales.orders"

    response = await service.answer(
        question="finance.monthly_revenue có lineage gì?", images=[IMAGE_URL],
    )
    assert response.intent == "LINEAGE"
    assert "finance.monthly_revenue" in response.answer


@pytest.mark.asyncio
async def test_image_entity_routed_to_real_sql_flow(db_session) -> None:
    """A SQL request referring back to the image ('nó') runs the SQL generator
    against the image-derived dataset, not image metadata or generic search."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())  # identifies "sales.orders"

    response = await service.answer(
        question="tạo SQL cho nó truy vấn order_id", images=[IMAGE_URL],
    )
    assert response.intent == "SQL_GENERATION"
    assert "sales.orders" in response.answer


@pytest.mark.asyncio
async def test_image_entity_routed_to_real_schema_flow(db_session) -> None:
    """A capability-ellipsis schema question with an image active routes to the
    schema function against the image-derived dataset."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())  # identifies "sales.orders"

    response = await service.answer(question="có những trường nào?", images=[IMAGE_URL])
    assert "sales.orders" in response.answer


@pytest.mark.asyncio
async def test_pure_image_content_answer_is_concise(db_session) -> None:
    """Purely image-content questions still answer directly from the Image
    Context, but concisely — never a full metadata dump."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())

    response = await service.answer(question="Ảnh này là gì?", images=[IMAGE_URL])
    assert response.intent == "VISION_ANALYSIS"
    assert "sales.orders" in response.answer
    assert "### Phân tích hình ảnh" not in response.answer


@pytest.mark.asyncio
async def test_listing_intent_exits_image_mode_not_anaphora(db_session) -> None:
    """A document/dataset listing after an image is an independent new intent:
    it must NEVER answer from the image or list the image-dataset, yet a later
    anaphoric follow-up ("Lineage của nó ?") must still target the image dataset."""
    from app.schemas.chat import ChatResponse
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())  # image identifies "sales.orders"

    for i in range(2):
        await EntityRepository(db_session).upsert(Entity(
            urn=f"urn:li:document:Doc{i}",
            entity_type="document",
            name=f"Doc {i}",
            display_name=f"Doc {i}",
            platform="confluence",
            environment="PROD",
            domain="Finance",
            datahub_url=f"http://localhost:9002/document/{i}",
            payload={"description": f"Doc {i}"},
            content_hash=f"hash-doc-{i}",
        ))

    cid = "context-switch-test"
    # Turn 1: establish the image context.
    r0 = await service.answer(
        question="Ảnh này là gì?", conversation_id=cid, images=[IMAGE_URL],
    )
    assert r0.intent == "VISION_ANALYSIS"
    assert "sales.orders" in r0.answer

    # Turn 2: independent listing intent — no image analysis, no image dataset.
    r1 = await service.answer(
        question="có những document nào trong hệ thống?", conversation_id=cid,
    )
    assert isinstance(r1, ChatResponse)
    assert r1.intent == "LISTING"
    assert "sales.orders" not in r1.answer
    assert "Doc 0, Doc 1" in r1.answer

    # Turn 3: anaphora after the topic switch still resolves the image dataset.
    r2 = await service.answer(
        question="Lineage của nó ?", conversation_id=cid,
    )
    assert r2.intent == "LINEAGE"
    assert "sales.orders" in r2.answer


@pytest.mark.asyncio
async def test_image_focus_yields_to_explicit_new_entity(db_session) -> None:
    """Once the user explicitly names a different catalog entity, "nó" follows
    that entity — the image-derived focus no longer owns the anaphora."""
    from app.services.chat_service import ChatService

    await _seed(db_session)
    service = ChatService(db_session)
    service._vision = _skill(db_session, _raw())  # image identifies "sales.orders"

    cid = "focus-yield-test"
    r0 = await service.answer(
        question="Ảnh này là gì?", conversation_id=cid, images=[IMAGE_URL],
    )
    assert r0.intent == "VISION_ANALYSIS"

    r1 = await service.answer(
        question="finance.monthly_revenue có lineage gì?", conversation_id=cid,
    )
    assert r1.intent == "LINEAGE"
    assert "finance.monthly_revenue" in r1.answer

    r2 = await service.answer(question="Lineage của nó ?", conversation_id=cid)
    assert r2.intent == "LINEAGE"
    assert "finance.monthly_revenue" in r2.answer
