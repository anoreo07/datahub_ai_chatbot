import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.graph import MetadataGraph


def _entity(urn: str, name: str, entity_type: str = "dataset",
            upstreams=None, downstreams=None, domain: str = "") -> Entity:
    return Entity(
        urn=urn,
        entity_type=entity_type,
        name=name,
        display_name=name,
        platform="redshift",
        environment="PROD",
        domain=domain,
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload={
            "display_name": name,
            "description": f"desc {name}",
            "upstreams": upstreams or [],
            "downstreams": downstreams or [],
        },
    )


@pytest.mark.asyncio
async def test_impact_downstream_bfs(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "fact_sales", downstreams=["urn:b", "urn:c"]))
    await repo.upsert(_entity("urn:b", "dim_customer", downstreams=["urn:d"]))
    await repo.upsert(_entity("urn:c", "dim_product", downstreams=["urn:d"]))
    await repo.upsert(_entity("urn:d", "report_final"))

    graph = MetadataGraph(db_session)
    result = await graph.impact("urn:a", depth=2)

    assert result.count == 3
    names = {n.name for n in result.nodes}
    assert names == {"dim_customer", "dim_product", "report_final"}
    assert result.depth_reached == 2
    leaf_names = {n.name for n in result.leaf_nodes}
    assert leaf_names == {"report_final"}


@pytest.mark.asyncio
async def test_sources_upstream_bfs(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:s1", "raw_source_1", downstreams=["urn:a"]))
    await repo.upsert(_entity("urn:s2", "raw_source_2", upstreams=["urn:s0"]))
    await repo.upsert(_entity("urn:s0", "raw_source_0"))
    await repo.upsert(_entity("urn:a", "fact_sales", upstreams=["urn:s1", "urn:s2"]))

    graph = MetadataGraph(db_session)
    result = await graph.sources("urn:a", depth=2)

    names = {n.name for n in result.nodes}
    assert "raw_source_1" in names
    assert "raw_source_2" in names
    # s0 is 2 hops from a via s2.
    assert "raw_source_0" in names
    assert result.depth_reached == 2


@pytest.mark.asyncio
async def test_path_shortest(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:s", "src", downstreams=["urn:m1", "urn:m2"]))
    await repo.upsert(_entity("urn:m1", "mid1", downstreams=["urn:t"]))
    await repo.upsert(_entity("urn:m2", "mid2", downstreams=["urn:t"]))
    await repo.upsert(_entity("urn:t", "target"))

    graph = MetadataGraph(db_session)
    path = await graph.path("urn:s", "urn:t", direction="downstream", depth=3)
    assert path[0] == "urn:s"
    assert path[-1] == "urn:t"
    assert len(path) == 3  # s -> one mid -> t


@pytest.mark.asyncio
async def test_path_unreachable_returns_empty(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "a"))
    await repo.upsert(_entity("urn:b", "b"))
    graph = MetadataGraph(db_session)
    assert await graph.path("urn:a", "urn:b", direction="downstream", depth=2) == []


@pytest.mark.asyncio
async def test_impact_dedupes_diamond(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "a", downstreams=["urn:b", "urn:c"]))
    await repo.upsert(_entity("urn:b", "b", downstreams=["urn:d"]))
    await repo.upsert(_entity("urn:c", "c", downstreams=["urn:d"]))
    await repo.upsert(_entity("urn:d", "d"))
    graph = MetadataGraph(db_session)
    result = await graph.impact("urn:a", depth=3)
    assert result.count == 3
    assert len(result.urns) == len(set(result.urns))


@pytest.mark.asyncio
async def test_longest_path_reports_deepest_chain(db_session) -> None:
    repo = EntityRepository(db_session)
    # a -> b -> c -> d is the longest chain (3 hops); a -> e is shorter.
    await repo.upsert(_entity("urn:a", "a", downstreams=["urn:b", "urn:e"]))
    await repo.upsert(_entity("urn:b", "b", downstreams=["urn:c"]))
    await repo.upsert(_entity("urn:c", "c", downstreams=["urn:d"]))
    await repo.upsert(_entity("urn:d", "d"))
    await repo.upsert(_entity("urn:e", "e"))
    graph = MetadataGraph(db_session)
    path = await graph.longest_path("urn:a", direction="downstream", depth=3)
    assert path == ["urn:a", "urn:b", "urn:c", "urn:d"]


@pytest.mark.asyncio
async def test_detect_cycles_finds_loop(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "a", downstreams=["urn:b"]))
    await repo.upsert(_entity("urn:b", "b", downstreams=["urn:a"]))
    graph = MetadataGraph(db_session)
    cycles = await graph.detect_cycles("urn:a", direction="downstream", depth=3)
    assert any("urn:a" in c for c in cycles)


@pytest.mark.asyncio
async def test_impact_summary_immediate_and_indirect(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_entity("urn:a", "a", downstreams=["urn:b"], domain="sales"))
    await repo.upsert(_entity("urn:b", "b", downstreams=["urn:c"], domain="sales"))
    await repo.upsert(_entity("urn:c", "c", domain="ops"))
    graph = MetadataGraph(db_session)
    summary = await graph.impact_summary("urn:a", depth=2)
    assert summary["total"] == 2
    assert "urn:b" in summary["immediate"]
    assert "urn:c" in summary["indirect"]
    assert summary["immediate_count"] == 1
    assert summary["indirect_count"] == 1
    assert "sales" in summary["affected_domains"]
    assert summary["critical_length"] >= 3
