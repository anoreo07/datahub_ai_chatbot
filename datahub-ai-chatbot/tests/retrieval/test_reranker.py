import pytest

from retrieval.hybrid_search import SearchResult
from retrieval.reranker import Reranker


def _result(urn: str, name: str, score: float, payload=None) -> SearchResult:
    return SearchResult(urn=urn, entity_type="dataset", name=name,
                        score=score, payload=payload or {})


@pytest.mark.asyncio
async def test_rerank_sorts_by_score_and_annotates_signals() -> None:
    rr = Reranker()
    results = [
        _result("urn:b", "b", 0.8),
        _result("urn:a", "a", 0.9),
    ]
    out = await rr.rerank("a", results)
    assert out[0].urn == "urn:a"
    assert "rerank_scores" in (out[0].payload or {})
    signals = out[0].payload["rerank_scores"]
    assert {"semantic", "graph", "metadata", "citation"} <= set(signals)


@pytest.mark.asyncio
async def test_rerank_nearby_entities_kept_in_order() -> None:
    rr = Reranker()
    results = [
        _result("urn:uhan", "fact_sales", 0.5),
        _result("urn:warehouse", "dim_warehouse", 0.5),
    ]
    out = await rr.rerank("fact_sales", results)
    assert out[0].urn == "urn:uhan"  # semantic match on "fact_sales"


@pytest.mark.asyncio
async def test_rerank_metadata_richness_raises_score() -> None:
    rr = Reranker()
    rich = _result("urn:rich", "dim_x", 0.5, payload={
        "description": "d", "owners": [{"name": "o"}], "domain": "sales",
        "platform": "redshift", "schema_fields": [{"name": "f", "type": "int"}],
    })
    poor = _result("urn:poor", "dim_x", 0.5, payload={})
    out = await rr.rerank("dim_x", [poor, rich])
    assert out[0].urn == "urn:rich"
