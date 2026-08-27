import pytest
from fastapi import HTTPException

from app.api.search import get_entity_detail
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.models import Entity
from database.repositories.entity_repository import EntityRepository


@pytest.mark.asyncio
async def test_get_entity_detail_success(db_session) -> None:
    # 1. Insert a mock entity into test DB
    repo = EntityRepository(db_session)
    mock_entity = Entity(
        urn="urn:li:dataset:(urn:li:dataPlatform:powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout,PROD)",
        entity_type="dataset",
        name="Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout",
        display_name="Dim_BaoCaoLayout",
        description="Layout details",
        platform="powerbi",
        environment="PROD",
        domain="Logistic",
        datahub_url="http://localhost:9002/dataset/layout",
        payload={
            "schema_fields": [
                {"name": "ID", "type": "String", "description": "ID col", "nullable": False, "is_primary_key": True},
                {"name": "Name", "type": "String", "description": "Name col", "nullable": True, "is_primary_key": False}
            ],
            "upstreams": [],
            "downstreams": [
                "urn:li:dashboard:(powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Visual_1)"
            ]
        },
        content_hash="test-hash-baocao"
    )

    # Insert a downstream entity to verify lineage resolution
    mock_downstream = Entity(
        urn="urn:li:dashboard:(powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Visual_1)",
        entity_type="dashboard",
        name="Visual_1",
        display_name="Visual Title 1",
        description="Visual description",
        platform="powerbi",
        environment="PROD",
        domain="Logistic",
        datahub_url="http://localhost:9002/dashboard/visual1",
        payload={},
        content_hash="test-hash-visual1"
    )

    await repo.upsert(mock_entity)
    await repo.upsert(mock_downstream)

    # 2. Query endpoint directly
    auth_service = AuthorizationService()
    user = UserContext(user_id="test-user", roles=["admin"], is_admin=True)

    data = await get_entity_detail(
        urn="urn:li:dataset:(urn:li:dataPlatform:powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout,PROD)",
        session=db_session,
        current_user=user,
        auth_service=auth_service
    )

    # 3. Assertions
    assert data.urn == "urn:li:dataset:(urn:li:dataPlatform:powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout,PROD)"
    assert data.name == "Bc_Hàng_tồn_kho_theo_kỳ.Dim_BaoCaoLayout"
    assert data.display_name == "Dim_BaoCaoLayout"
    assert len(data.schema_fields) == 2
    assert data.schema_fields[0].name == "ID"
    assert data.schema_fields[0].is_primary_key is True

    assert len(data.downstreams) == 1
    assert data.downstreams[0].urn == "urn:li:dashboard:(powerbi,Bc_Hàng_tồn_kho_theo_kỳ.Visual_1)"
    assert data.downstreams[0].name == "Visual Title 1"  # Resolved display name!
    assert data.downstreams[0].entity_type == "dashboard"
    assert data.downstreams[0].platform == "powerbi"


@pytest.mark.asyncio
async def test_get_entity_detail_not_found(db_session) -> None:
    auth_service = AuthorizationService()
    user = UserContext(user_id="test-user", roles=["admin"], is_admin=True)
    with pytest.raises(HTTPException) as exc:
        await get_entity_detail(
            urn="urn:li:dataset:(urn:li:dataPlatform:powerbi,non_existent,PROD)",
            session=db_session,
            current_user=user,
            auth_service=auth_service
        )
    assert exc.value.status_code == 404
