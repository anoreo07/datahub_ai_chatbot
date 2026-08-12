"""Regression tests for the SQL Generation pipeline.

Covers the four required scenarios:
1. SQL generated from a column/filter name ("truy vấn ... warehouse_id").
2. Business-description ranking when several datasets carry the field.
3. Ambiguous field names -> clarify which dataset, never entity-search fallback.
4. Permission-restricted datasets are excluded before SQL generation.
"""
import pytest

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.chat import ChatResponse
from app.services.action_service import ActionService
from database.models import Entity, EntityAclDB
from database.repositories.entity_repository import EntityRepository

_INVENTORY_URN = "urn:li:dataset:(urn:li:dataPlatform:snowflake,fact_inventory,PROD)"
_ISSUE_URN = "urn:li:dataset:(urn:li:dataPlatform:snowflake,fact_goods_issue,PROD)"
_SALES_URN = "urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)"


def _admin() -> UserContext:
    return UserContext(user_id="admin", roles=["admin"], is_admin=True)


def _restricted_user() -> UserContext:
    return UserContext(user_id="restricted", roles=["viewer"], is_admin=False)


def _dataset(urn: str, name: str, *, domain: str, description: str,
             fields: list[dict]) -> Entity:
    return Entity(
        urn=urn, entity_type="dataset", name=name, display_name=name,
        description=description, platform="snowflake", domain=domain,
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload={"schema_fields": fields, "domain": domain, "description": description},
    )


async def _seed(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_dataset(
        _INVENTORY_URN, "fact_inventory", domain="Logistics",
        description="Bảng tồn kho chi tiết theo từng kho (warehouse).",
        fields=[
            {"name": "warehouse_id", "type": "string", "description": "Mã kho"},
            {"name": "item_id", "type": "string", "description": "Mã sản phẩm"},
            {"name": "quantity", "type": "decimal", "description": "Số lượng tồn"},
        ],
    ))
    await repo.upsert(_dataset(
        _ISSUE_URN, "fact_goods_issue", domain="Logistics",
        description="Bảng xuất kho (goods issue) theo từng kho.",
        fields=[
            {"name": "warehouse_id", "type": "string", "description": "Mã kho"},
            {"name": "issue_date", "type": "timestamp", "description": "Ngày xuất"},
        ],
    ))
    await repo.upsert(_dataset(
        _SALES_URN, "sales.orders", domain="Sales",
        description="Bảng đơn hàng đã xác nhận.",
        fields=[
            {"name": "order_id", "type": "string", "description": "Mã đơn hàng"},
            {"name": "customer_id", "type": "string", "description": "Mã khách hàng"},
            {"name": "gross_revenue", "type": "decimal", "description": "Doanh thu gộp"},
        ],
    ))


@pytest.mark.asyncio
async def test_sql_discovery_by_column_name(db_session) -> None:
    """A field token (warehouse_id) finds the dataset carrying it, no entity search."""
    await _seed(db_session)
    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    candidates = await svc.discover_sql_candidates(
        "truy vấn đối tượng có warehouse_id", user=_admin()
    )
    assert candidates, "expected at least one candidate for warehouse_id"
    urns = [c.entity.urn for c in candidates]
    assert _INVENTORY_URN in urns and _ISSUE_URN in urns
    assert _SALES_URN not in urns, "sales.orders has no warehouse_id and must not appear"
    assert "warehouse_id" in candidates[0].matched_fields


@pytest.mark.asyncio
async def test_sql_generated_for_single_dataset(db_session) -> None:
    """A clear single-field match produces a grounded SQL statement."""
    await _seed(db_session)
    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    resp = await svc.generate_sql("fact_inventory", requested_columns=["warehouse_id"])
    assert resp.valid is True
    assert "FROM fact_inventory" in resp.sql
    assert "warehouse_id" in resp.sql


@pytest.mark.asyncio
async def test_sql_ranks_by_business_relevance(db_session) -> None:
    """Two datasets carry the field; the one whose description matches the question wins."""
    await _seed(db_session)
    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    candidates = await svc.discover_sql_candidates(
        "truy vấn số lượng tồn kho theo warehouse_id", user=_admin()
    )
    assert candidates, "expected candidates"
    assert candidates[0].entity.urn == _INVENTORY_URN, (
        "fact_inventory (hàng tồn kho) should outrank fact_goods_issue for an "
        f"inventory question; got {candidates[0].entity.urn}"
    )
    assert candidates[0].score > candidates[1].score


@pytest.mark.asyncio
async def test_sql_ambiguous_fields_ask_clarification(db_session) -> None:
    """Two datasets with equal field relevance -> clarification, never an entity list."""
    await _seed(db_session)
    from app.services.chat_service import ChatService

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "truy vấn đối tượng có warehouse_id là '123'",
        user=_admin(),
        selected_action="sql",
    )
    assert response.intent == "SQL_GENERATION"
    assert response.ambiguous is True
    assert "fact_inventory" in response.answer and "fact_goods_issue" in response.answer
    assert "trùng khớp với yêu cầu" not in response.answer


@pytest.mark.asyncio
async def test_sql_action_no_entity_search_fallback(db_session) -> None:
    """The reported bug: SQL request must not return FIND_ENTITY / empty entities."""
    await _seed(db_session)
    from app.services.chat_service import ChatService

    # Drop the second warehouse_id dataset so exactly one candidate remains.
    repo = EntityRepository(db_session)
    await repo.delete_by_urn(_ISSUE_URN)

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "truy vấn đối tượng có warehouse_id là '123'",
        user=_admin(),
        selected_action="sql",
    )
    assert response.intent == "SQL_GENERATION"
    assert response.ambiguous is False
    assert "SQL cho dataset" in response.answer
    assert "FROM fact_inventory" in response.answer


@pytest.mark.asyncio
async def test_sql_record_query_without_action(db_session) -> None:
    """A natural-language record query with NO selected action routes to SQL.

    The reported bug: "cho tôi các bản ghi warehouse_id 123" fell to GENERAL /
    hybrid search instead of the SQL generator when no menu action was picked.
    Without a stated filter field these fall back to SQL discovery over the
    schema, producing SQL for the single dataset that carries the column.
    """
    await _seed(db_session)
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    await repo.delete_by_urn(_ISSUE_URN)  # leave exactly one warehouse_id dataset

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "cho tôi các bản ghi có warehouse_id bằng 123",
        user=_admin(),
    )
    assert response.intent == "SQL_GENERATION"
    assert response.ambiguous is False
    assert "SQL cho dataset" in response.answer
    assert "fact_inventory" in response.answer


@pytest.mark.asyncio
async def test_sql_record_query_explicit_field_no_action(db_session) -> None:
    """A column named in a no-action record query still asks which dataset when
    several carry the field (never a generic entity list)."""
    await _seed(db_session)
    from app.services.chat_service import ChatService

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    response: ChatResponse = await service.answer(
        "cho tôi các bản ghi có warehouse_id bằng 123",
        user=_admin(),
    )
    assert response.intent == "SQL_GENERATION"
    assert response.ambiguous is True
    assert "fact_inventory" in response.answer and "fact_goods_issue" in response.answer


@pytest.mark.asyncio
async def test_sql_followup_owner_from_evidence(db_session) -> None:
    """After a SQL turn, "owner của nó" resolves to the SQL dataset's owner
    from the recorded evidence, without a new entity search."""
    await _seed(db_session)
    from app.services.chat_service import ChatService

    repo = EntityRepository(db_session)
    await repo.delete_by_urn(_ISSUE_URN)  # exactly one warehouse_id dataset

    inv = await repo.get_by_urn(_INVENTORY_URN)
    inv.payload = {
        **(inv.payload or {}),
        "owners": [{"name": "Kho Vận Analytics", "type": "USER"}],
    }
    await repo.upsert(inv)

    service = ChatService(db_session, auth_service=AuthorizationService(session=db_session))
    cid = "sql-owner"

    r1 = await service.answer(
        "cho tôi các bản ghi có warehouse_id bằng 123",
        user=_admin(), conversation_id=cid,
    )
    assert r1.intent == "SQL_GENERATION", r1.answer
    assert "fact_inventory" in r1.answer

    r2 = await service.answer("owner của nó?", user=_admin(), conversation_id=cid)
    assert r2.intent == "OWNER_LOOKUP", r2.answer
    assert "Kho Vận Analytics" in r2.answer


@pytest.mark.asyncio
async def test_permission_restricted_dataset_excluded(db_session) -> None:
    """A dataset the user is denied from must be invisible to SQL discovery."""
    await _seed(db_session)
    db_session.add(EntityAclDB(
        entity_urn=_INVENTORY_URN,
        is_public=False,
        allowed_user_ids=[],
        allowed_groups=[],
        denied_user_ids=["restricted"],
        denied_groups=[],
        classification="confidential",
    ))
    await db_session.commit()

    svc = ActionService(db_session, auth_service=AuthorizationService(session=db_session))
    candidates = await svc.discover_sql_candidates(
        "truy vấn đối tượng có warehouse_id", user=_restricted_user()
    )
    assert candidates, "expected at least one accessible candidate"
    urns = [c.entity.urn for c in candidates]
    assert _INVENTORY_URN not in urns, "denied dataset must be filtered out"
    assert _ISSUE_URN in urns
