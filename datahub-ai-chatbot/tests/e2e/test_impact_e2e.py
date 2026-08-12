import pytest as _pytest

pytest = _pytest


@pytest.mark.asyncio
async def test_impact_question_via_chat_service(db_session):
    """Recursive impact questions reach the metadata graph and return consumers."""
    from app.services.chat_service import ChatService
    from database.models import Entity
    from database.repositories.entity_repository import EntityRepository

    repo = EntityRepository(db_session)
    entities = [
        Entity(
            urn="urn:li:dataset:(urn:li:dataPlatform:redshift,fact_sales,PROD)",
            entity_type="dataset", name="fact_sales", display_name="fact_sales",
            platform="redshift", environment="PROD", domain="Sales",
            datahub_url="http://localhost:9002/dataset/x",
            payload={"display_name": "fact_sales", "upstreams": [], "downstreams": ["urn:b"]},
        ),
        Entity(
            urn="urn:b", entity_type="dataset", name="report_monthly",
            display_name="report_monthly", platform="mode", environment="PROD",
            datahub_url="http://localhost:9002/dataset/y",
            payload={
                "display_name": "report_monthly",
                "upstreams": ["urn:li:dataset:(urn:li:dataPlatform:redshift,fact_sales,PRODUCT)"],
                "downstreams": [],
            },
        ),
    ]
    for e in entities:
        await repo.upsert(e)

    service = ChatService(db_session)
    response = await service.answer(
        "Nếu thay đổi dataset fact_sales thì những ai bị ảnh hưởng?"
    )
    names = {item.name for item in response.entities}
    assert "fact_sales" in names
    assert "report_monthly" in names
