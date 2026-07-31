from retrieval.graph_expander import GraphExpander


async def test_graph_expander_returns_empty() -> None:
    expander = GraphExpander()
    result = await expander.expand("urn:test")
    assert result == []
