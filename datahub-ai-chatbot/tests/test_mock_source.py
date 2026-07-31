

class TestMockDataHubSource:
    async def test_healthcheck(self, mock_source) -> None:
        assert await mock_source.healthcheck() is True

    async def test_list_datasets(self, mock_source) -> None:
        datasets = await mock_source.list_entity_type("dataset")
        assert len(datasets) >= 2
        urns = [d.urn for d in datasets]
        assert any("sales.orders" in u for u in urns)
        assert any("finance.monthly_revenue" in u for u in urns)

    async def test_list_glossary_terms(self, mock_source) -> None:
        terms = await mock_source.list_entity_type("glossary_term")
        assert len(terms) >= 5
        names = [t.display_name or t.name for t in terms]
        assert "Revenue" in names
        assert "Net Revenue" in names
        assert "Customer" in names
        assert "Order" in names
        assert "Gross Revenue" in names

    async def test_list_dashboards(self, mock_source) -> None:
        dashboards = await mock_source.list_entity_type("dashboard")
        assert len(dashboards) == 1
        assert dashboards[0].name == "Monthly Revenue"

    async def test_list_documents(self, mock_source) -> None:
        docs = await mock_source.list_entity_type("document")
        assert len(docs) == 1
        assert "Methodology" in docs[0].name

    async def test_get_entity_by_urn(self, mock_source) -> None:
        entity = await mock_source.get_entity(
            "urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)"
        )
        assert entity is not None
        assert entity.name == "sales.orders"
        assert entity.domain == "Sales"

    async def test_get_entity_not_found(self, mock_source) -> None:
        entity = await mock_source.get_entity("urn:li:dataset:unknown")
        assert entity is None

    async def test_search_entities(self, mock_source) -> None:
        results = await mock_source.search_entities("dataset", "orders")
        assert len(results) >= 1
        assert results[0].name == "sales.orders"

    async def test_search_entities_all(self, mock_source) -> None:
        results = await mock_source.search_entities("dataset", "*")
        assert len(results) >= 2

    async def test_dataset_schema_fields(self, mock_source) -> None:
        entity = await mock_source.get_entity(
            "urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)"
        )
        assert entity is not None
        assert len(entity.schema_fields) == 5
        field_names = [f.name for f in entity.schema_fields]
        assert "order_id" in field_names
        assert "net_revenue" in field_names

    async def test_dataset_lineage(self, mock_source) -> None:
        entity = await mock_source.get_entity(
            "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.monthly_revenue,PROD)"
        )
        assert entity is not None
        assert len(entity.upstreams) == 2
        assert any("sales.orders" in u for u in entity.upstreams)
        assert len(entity.downstreams) == 1
        assert any("MonthlyRevenue" in d for d in entity.downstreams)

    async def test_glossary_term_definition(self, mock_source) -> None:
        term = await mock_source.get_entity("urn:li:glossaryTerm:NetRevenue")
        assert term is not None
        assert "Doanh thu còn lại" in (term.description or "")

    async def test_list_all(self, mock_source) -> None:
        all_entities = mock_source.list_all()
        assert len(all_entities) >= 10
