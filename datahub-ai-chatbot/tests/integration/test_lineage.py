import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository

_MATERIAL_URN = "urn:li:dataset:(urn:li:dataPlatform:redshift,dim_material,PROD)"


def _make_dataset(name: str, domain: str, upstreams: list[str] | None = None) -> Entity:
    return Entity(
        urn=f"urn:li:dataset:(urn:li:dataPlatform:redshift,{name},PROD)",
        entity_type="dataset",
        name=name,
        display_name=name,
        platform="redshift",
        environment="PROD",
        domain=domain,
        datahub_url=f"http://localhost:9002/dataset/urn:li:dataset:(urn:li:dataPlatform:redshift,{name},PROD)",
        payload={"domain": domain, "upstreams": upstreams or []},
        content_hash=f"hash-{name}",
    )


@pytest.mark.asyncio
async def test_lineage_with_long_phrasing(db_session) -> None:
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    await repo.upsert(_make_dataset("dim_inventory_category", "LOGISTIC", [_MATERIAL_URN]))
    await repo.upsert(_make_dataset("dim_material", "LOGISTIC"))

    service = ChatService(db_session)

    for question in (
        "thông tin về lineage của dataset dim_inventory_category",
        "thông tin về linage của dataset dim_inventory_category",
        "lineage của dim_inventory_category",
        "dim_inventory_category lấy dữ liệu từ đâu?",
    ):
        response = await service.answer(question)
        assert response.intent == "LINEAGE"
        assert response.confidence == "high"
        assert not response.insufficient_context
        names = {e.name for e in response.entities}
        assert "dim_inventory_category" in names
        assert "dim_material" in names


@pytest.mark.asyncio
async def test_lineage_no_upstream(db_session) -> None:
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    await repo.upsert(_make_dataset("dim_material", "LOGISTIC"))

    service = ChatService(db_session)
    response = await service.answer("dim_material lấy dữ liệu từ đâu?")

    assert response.intent == "LINEAGE"
    assert not response.insufficient_context
    assert len(response.entities) == 1
    assert response.entities[0].name == "dim_material"
    assert response.answer.strip() == (
        "Dataset dim_material hiện không có lineage (upstream/downstream) "
        "được ghi nhận."
    )


@pytest.mark.asyncio
async def test_owner_no_owner_short_answer(db_session) -> None:
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    await repo.upsert(_make_dataset("dim_inventory_category", "LOGISTIC", []))

    service = ChatService(db_session)
    response = await service.answer("Ai sở hữu dataset dim_inventory_category?")

    assert response.intent == "OWNER_LOOKUP"
    assert response.confidence == "high"
    assert not response.insufficient_context
    assert response.answer.strip() == (
        "Dataset dim_inventory_category hiện không có người sở hữu (owner)."
    )


@pytest.mark.asyncio
async def test_owner_with_owner_not_short(db_session) -> None:
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    entity = _make_dataset("fact_revenue", "TÀI CHÍNH", [])
    entity.payload = {"domain": "TÀI CHÍNH", "upstreams": [],
                      "owners": [{"name": "Finance Analytics", "type": "USER"}]}
    await repo.upsert(entity)

    service = ChatService(db_session)
    response = await service.answer("Ai sở hữu dataset fact_revenue?")

    assert response.intent == "OWNER_LOOKUP"
    assert response.answer.strip() != "Dataset fact_revenue hiện không có người sở hữu (owner)."
    assert not response.insufficient_context


@pytest.mark.asyncio
async def test_lineage_api_error(db_session, monkeypatch) -> None:
    from app.services.chat_service import ChatService
    from ingestion.mock_source import MockDataHubSource

    repo = EntityRepository(db_session)
    await repo.upsert(_make_dataset("dim_material", "LOGISTIC"))

    # Mock get_lineage to raise an exception
    async def mock_get_lineage_err(*args, **kwargs):
        raise Exception("Connection timeout")

    monkeypatch.setattr(MockDataHubSource, "get_lineage", mock_get_lineage_err)

    service = ChatService(db_session)
    response = await service.answer("dim_material lấy dữ liệu từ đâu?")

    assert response.intent == "LINEAGE"
    assert "Không thể lấy lineage cho Dataset dim_material" in response.answer


@pytest.mark.asyncio
async def test_lineage_baocaolayout_visualization(db_session) -> None:
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    layout_urn = "urn:li:dataset:(urn:li:dataPlatform:powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout,PROD)"

    mock_entity = Entity(
        urn=layout_urn,
        entity_type="dataset",
        name="Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout",
        display_name="Dim_BaoCaoLayout",
        platform="powerbi",
        environment="PROD",
        domain="Logistic",
        datahub_url="http://localhost:9002/dataset/layout",
        payload={
            "upstreams": [],
            "downstreams": [f"urn:li:dashboard:(powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Visual_{i})" for i in range(1, 13)]
        },
        content_hash="hash-baocao-layout"
    )
    await repo.upsert(mock_entity)

    service = ChatService(db_session)
    # Case 1: Without selected_action="lineage" -> TEXT ONLY, lineage payload is None
    response_text = await service.answer("Dataset Dim_BaoCaoLayout có lineage như nào?")
    assert response_text.intent == "LINEAGE"
    assert not response_text.insufficient_context
    assert response_text.lineage is None
    assert "Dim_BaoCaoLayout" in response_text.answer
    assert "downstream" in response_text.answer.lower()

    # Case 2: With selected_action="lineage" -> VISUAL GRAPH DATA IS POPULATED
    response_visual = await service.answer("Dataset Dim_BaoCaoLayout có lineage như nào?", selected_action="lineage")
    assert response_visual.intent == "LINEAGE"
    assert not response_visual.insufficient_context
    assert response_visual.selected_action == "lineage"
    assert response_visual.lineage is not None
    assert response_visual.lineage.entity_name == "Dim_BaoCaoLayout"
    assert len(response_visual.lineage.downstreams) == 12


