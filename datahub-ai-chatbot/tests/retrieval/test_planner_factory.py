import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from database.models import Base, Entity
from database.repositories.entity_repository import EntityRepository
from retrieval import classifier as clf
from retrieval.planner_executor import PlannerExecutor
from retrieval.query_models import PlanStep, QueryPlan


def _entity(urn: str, name: str) -> Entity:
    return Entity(
        urn=urn, entity_type="dataset", name=name, display_name=name,
        platform="redshift", environment="PROD",
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload={"display_name": name, "description": f"desc {name}"},
    )


@pytest.mark.asyncio
async def test_parse_llm_composite_plan() -> None:
    plan = clf._parse_llm_plan(
        '{"intent": "COMPOSITE_QUERY", "entity_refs":'
        ' ["fact_sales","gross_revenue"], "confidence": "medium"}'
    )
    assert plan is not None
    assert plan.is_composite or plan.intent == "COMPOSITE_QUERY"


@pytest.mark.asyncio
async def test_dag_with_factory_runs_concurrently_safely() -> None:
    """Parallel DAG execution must not raise the SQLAlchemy ISCE race."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with factory() as seed:
            repo = EntityRepository(seed)
            await repo.upsert(_entity("urn:a", "fact_sales"))
            await repo.upsert(_entity("urn:g", "gross_revenue"))

        executor = PlannerExecutor(None, session_factory=factory)  # type: ignore[arg-type]
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
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
