from retrieval.entity_resolver import EntityResolver


class TestEntityResolverUnit:
    def test_candidate_scoring_exact(self) -> None:
        resolver = EntityResolver.__new__(EntityResolver)
        score = resolver._score("sales.orders", "sales.orders")
        assert score == 1.0

    def test_candidate_scoring_similar(self) -> None:
        resolver = EntityResolver.__new__(EntityResolver)
        score = resolver._score("orders", "sales.orders")
        assert score == 0.9

    def test_candidate_scoring_partial(self) -> None:
        resolver = EntityResolver.__new__(EntityResolver)
        score = resolver._score("test", "something else")
        assert score == 0.1

    def test_candidate_scoring_case_insensitive(self) -> None:
        resolver = EntityResolver.__new__(EntityResolver)
        score = resolver._score("SALES.ORDERS", "sales.orders")
        assert score == 1.0

    def test_candidate_scoring_substring(self) -> None:
        resolver = EntityResolver.__new__(EntityResolver)
        score = resolver._score("revenue", "finance.monthly_revenue")
        assert score == 0.7
