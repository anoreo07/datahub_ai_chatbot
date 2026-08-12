import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.planner_executor import PlannerExecutor
from retrieval.query_models import PlanStep, QueryFilter, QueryPlan


def _entity(urn: str, name: str, entity_type: str = "dataset",
            upstreams=None, downstreams=None, domain: str = "",
            owners=None, glossary_terms=None) -> Entity:
    return Entity(
        urn=urn, entity_type=entity_type, name=name, display_name=name,
        platform="redshift", environment="PROD", domain=domain,
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload={
            "display_name": name,
            "description": f"desc {name}",
            "upstreams": upstreams or [],
            "downstreams": downstreams or [],
            "owners": owners or [],
            "glossary_terms": glossary_terms or [],
        },
    )


@pytest.mark.asyncio
async def test_resolve_entity_tool(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:li:dataset:(urn:li:dataPlatform:redshift,sales.orders,PROD)",
        "sales.orders",
    ))
    executor = PlannerExecutor(db_session)
    plan = QueryPlan(intent="FIND_ENTITY", entity_refs=["sales.orders"],
                     source="classifier")
    results = await executor.execute(plan)
    assert len(results) == 1
    assert results[0].name == "sales.orders"


@pytest.mark.asyncio
async def test_recursive_impact_plan(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "fact_sales", downstreams=["urn:b"]))
    await repo.upsert(_entity("urn:b", "report_monthly"))
    executor = PlannerExecutor(db_session)
    plan = QueryPlan(intent="IMPACT", entity_refs=["fact_sales"],
                     direction="downstream", source="planner")
    results = await executor.execute(plan)
    names = {r.name for r in results}
    assert "fact_sales" in names
    assert "report_monthly" in names
    # Blast-radius summary must be attached to the root result.
    root = next(r for r in results if r.name == "fact_sales")
    summary = (root.payload or {}).get("impact_summary")
    assert summary is not None
    assert summary["immediate_count"] == 1
    assert summary["total"] == 1
    assert summary["critical_path"][-1] == "urn:b"
    # The chain must be surfaced in the root content so the generator can
    # answer longest-path / critical-chain questions.
    content = (root.payload or {}).get("content", "")
    assert "Critical (longest) dependency chain" in content
    assert "fact_sales -> report_monthly" in content


@pytest.mark.asyncio
async def test_dag_parallel_independent_steps(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "fact_sales"))
    await repo.upsert(_entity("urn:g", "gross_revenue"))
    executor = PlannerExecutor(db_session)
    # Two independent resolution steps -> both run concurrently, both results kept.
    plan = QueryPlan(
        intent="COMPOSITE_QUERY", source="planner",
        steps=[
            PlanStep(op="resolve_entity", params={"name": "fact_sales"}),
            PlanStep(op="resolve_entity", params={"name": "gross_revenue"}),
        ],
    )
    results = await executor.execute(plan)
    names = {r.name for r in results}
    assert "fact_sales" in names
    assert "gross_revenue" in names


@pytest.mark.asyncio
async def test_dag_respects_depends_on_ordering(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "fact_sales", downstreams=["urn:b"]))
    await repo.upsert(_entity("urn:b", "report_final"))
    executor = PlannerExecutor(db_session)
    # step 1 resolves the entity; step 2 (impact) depends on step 0's entity.
    plan = QueryPlan(
        intent="IMPACT", source="planner",
        steps=[
            PlanStep(op="resolve_entity", params={"name": "fact_sales"}),
            PlanStep(op="recursive_impact",
                     params={"name": "fact_sales", "depth": 2},
                     depends_on=[0]),
        ],
    )
    results = await executor.execute(plan)
    names = {r.name for r in results}
    assert "fact_sales" in names
    assert "report_final" in names


@pytest.mark.asyncio
async def test_list_by_dimension_plan(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:x", "x", domain="Finance"))
    await repo.upsert(_entity("urn:y", "y", domain="Sales"))
    executor = PlannerExecutor(db_session)
    plan = QueryPlan(intent="DOMAIN_QUERY",
                     filter=QueryFilter(dimension="domain", value="Finance"),
                     source="planner")
    results = await executor.execute(plan)
    assert {r.name for r in results} == {"x"}


@pytest.mark.asyncio
async def test_multi_step_composite(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "fact_sales", downstreams=["urn:b"]))
    await repo.upsert(_entity("urn:b", "report_final"))
    executor = PlannerExecutor(db_session)
    plan = QueryPlan(
        intent="IMPACT", entity_refs=["fact_sales"],
        steps=[
            PlanStep(op="resolve_entity", params={"name": "fact_sales"}),
            PlanStep(op="recursive_impact", params={"name": "fact_sales", "depth": 2}),
        ],
        source="planner",
    )
    results = await executor.execute(plan)
    names = {r.name for r in results}
    assert "fact_sales" in names
    assert "report_final" in names
