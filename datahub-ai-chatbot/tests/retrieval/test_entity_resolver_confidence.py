"""Confidence-framework tests for EntityResolver.

Covers the explicit ResolutionState model (RESOLVED / NEED_CLARIFICATION /
LOW_CONFIDENCE / NOT_FOUND), the RC1a rule: a runner-up of a DIFFERENT
entity type must never force a clarification, exact matches always outrank
fuzzy candidates, and the QueryScope tie-breaker (domain/platform scoping).
"""

from retrieval.entity_resolver import (
    EntityResolver,
    QueryScope,
    ResolutionState,
)

THRESHOLDS = {
    "exact": 1.0,
    "high": 0.9,
    "substring": 0.7,
    "ambiguity_margin": 0.2,
}


class FakeRepo:
    def __init__(self, entities):
        self.entities = entities
        self.by_urn = {e.urn: e for e in entities}

    async def get_by_urn(self, urn):
        return self.by_urn.get(urn)

    async def search_by_name(self, name, entity_type=None):
        nl = name.lower()
        out = []
        for e in self.entities:
            if entity_type and e.entity_type != entity_type:
                continue
            if nl in e.name.lower() or nl in (e.display_name or "").lower() or nl in e.urn.lower():
                out.append(e)
        return out

    async def list_all(self, entity_type=None, limit=500):
        if entity_type:
            return [e for e in self.entities if e.entity_type == entity_type][:limit]
        return self.entities[:limit]


class FakeEntity:
    def __init__(self, urn, name, entity_type="dataset", display_name=None,
                 domain=None, platform=None, payload=None):
        self.urn = urn
        self.name = name
        self.entity_type = entity_type
        self.display_name = display_name
        self.domain = domain
        self.platform = platform
        self.payload = payload or {}
        self.deleted = False
        self.datahub_url = None
        self.environment = "PROD"


def make_resolver(entities):
    resolver = EntityResolver.__new__(EntityResolver)
    resolver._repo = FakeRepo(entities)
    return resolver


def _run(resolver, name, entity_type=None, scope=None):
    import asyncio
    return asyncio.run(
        resolver.resolve(name, entity_type=entity_type, scope=scope))


class TestResolutionStates:
    def test_exact_urn_is_resolved(self):
        e = FakeEntity("urn:li:dataset:exact", "sales.orders", "dataset")
        r = _run(make_resolver([e]), "urn:li:dataset:exact")
        assert r.state == ResolutionState.RESOLVED
        assert r.exact_match and r.resolved is not None
        assert r.confidence == 1.0
        assert r.source == "exact_urn"

    def test_exact_name_is_resolved(self):
        e = FakeEntity("urn:li:dataset:orders", "sales.orders", "dataset")
        r = _run(make_resolver([e]), "sales.orders")
        assert r.state == ResolutionState.RESOLVED
        assert r.exact_match and r.resolved.urn == "urn:li:dataset:orders"

    def test_near_name_is_resolved_not_clarified(self):
        e = FakeEntity("urn:li:dataset:orders", "sales.orders", "dataset")
        r = _run(make_resolver([e]), "orders")
        assert r.state == ResolutionState.RESOLVED
        assert r.resolved.urn == "urn:li:dataset:orders"
        assert not r.ambiguous

    def test_same_type_tie_is_ambiguous(self):
        # Two distinct same-type entities matching the query by SUBSTRING (0.7),
        # with a gap below the ambiguity margin -> clarify.
        e1 = FakeEntity("urn:li:dataset:stock1", "current_stock_level", "dataset")
        e2 = FakeEntity("urn:li:dataset:stock2", "stock_reporting", "dataset")
        r = _run(make_resolver([e1, e2]), "stock")
        assert r.state == ResolutionState.NEED_CLARIFICATION
        assert r.ambiguous is True

    def test_cross_type_tie_is_not_ambiguous_rc1a(self):
        # Same query matching a dataset AND a dashboard at equal substring
        # strength: the different-type runner-up must NOT force a clarify.
        ds = FakeEntity("urn:li:dataset:stock_a", "current_stock_level", "dataset")
        dash = FakeEntity("urn:li:dashboard:stock_b", "stock_dashboard", "dashboard")
        r = _run(make_resolver([ds, dash]), "stock")
        assert not r.ambiguous
        assert r.state == ResolutionState.RESOLVED
        assert r.resolved is not None
        assert r.resolved.entity_type == "dataset"

    def test_same_name_different_platform_same_type_is_ambiguous(self):
        e1 = FakeEntity("urn:li:dataset:redshift", "stock_realtime", "dataset",
                        platform="redshift")
        e2 = FakeEntity("urn:li:dataset:powerbi", "stock_reporting", "dataset",
                        platform="powerbi")
        r = _run(make_resolver([e1, e2]), "stock")
        assert r.state == ResolutionState.NEED_CLARIFICATION
        assert r.ambiguous is True

    def test_same_name_different_domain_is_ambiguous(self):
        e1 = FakeEntity("urn:li:dataset:dom1", "current_stock_level", "dataset", domain="SX")
        e2 = FakeEntity("urn:li:dataset:dom2", "stock_reporting", "dataset", domain="KD")
        r = _run(make_resolver([e1, e2]), "stock")
        assert r.state == ResolutionState.NEED_CLARIFICATION

    def test_no_match_is_not_found(self):
        e = FakeEntity("urn:li:dataset:orders", "sales.orders", "dataset")
        r = _run(make_resolver([e]), "hoàn_toàn_khác_biệt")
        assert r.state == ResolutionState.NOT_FOUND
        assert r.resolved is None and not r.ambiguous

    def test_low_confidence_weak_fuzzy(self):
        # A fuzzy hit below the substring threshold but above the fuzzy floor
        # (0.6 <= score < 0.7) -> LOW_CONFIDENCE, never a fabricated resolve.
        e = FakeEntity("urn:li:dataset:abc", "abc_matching", "dataset")
        r = _run(make_resolver([e]), "abx")
        assert r.state == ResolutionState.LOW_CONFIDENCE
        assert not r.ambiguous
        assert r.resolved is None


class TestCandidateFeatures:
    def test_candidates_carry_domain_and_platform(self):
        e = FakeEntity("urn:li:dataset:rpt", "rpt_survey", "dataset",
                       domain="SẢN XUẤT", platform="redshift")
        r = _run(make_resolver([e]), "rpt_survey")
        assert r.resolved is not None
        assert r.resolved.domain == "SẢN XUẤT"
        assert r.resolved.platform == "redshift"

    def test_conflict_resolution_prefers_higher_score(self):
        e1 = FakeEntity("urn:li:dataset:stg", "stg_material", "dataset")
        e2 = FakeEntity("urn:li:dataset:mat", "material", "dataset")
        # "material" matches e2 exactly (1.0) and e1 by substring (0.7).
        r = _run(make_resolver([e1, e2]), "material")
        assert r.resolved is not None
        assert r.resolved.urn == "urn:li:dataset:mat"
        assert r.exact_match is True

    def test_fuzzy_never_overrides_exact(self):
        e1 = FakeEntity("urn:li:dataset:real", "real_entity_name", "dataset")
        e2 = FakeEntity("urn:li:dataset:typo", "other_entity", "dataset")
        r = _run(make_resolver([e1, e2]), "real_entity")
        assert r.resolved is not None
        assert r.resolved.urn == "urn:li:dataset:real"


class TestQueryScope:
    def test_domain_scope_breaks_same_name_tie(self):
        # Same-named term in two domains: the question-scoped domain wins.
        sx = FakeEntity("urn:li:glossary:sx", "Nhu cầu linh kiện", "glossary_term",
                        domain="SẢN XUẤT")
        kd = FakeEntity("urn:li:glossary:kd", "Nhu cầu linh kiện", "glossary_term",
                        domain="KINH DOANH")
        r = _run(make_resolver([sx, kd]), "Nhu cầu linh kiện",
                 entity_type="glossary_term", scope=QueryScope(domain="SẢN XUẤT"))
        assert r.resolved is not None
        assert r.resolved.urn == "urn:li:glossary:sx"
        assert not r.ambiguous

    def test_platform_scope_breaks_same_name_tie(self):
        rsh = FakeEntity("urn:li:dataset:rsh", "fact_demand", "dataset",
                         platform="redshift")
        pbi = FakeEntity("urn:li:dataset:pbi", "fact_demand", "dataset",
                         platform="powerbi")
        r = _run(make_resolver([rsh, pbi]), "fact_demand",
                 entity_type="dataset", scope=QueryScope(platform="powerbi"))
        assert r.resolved is not None
        assert r.resolved.urn == "urn:li:dataset:pbi"

    def test_scope_never_demotes_when_no_candidate_has_domain(self):
        # A clean exact match on a term that carries no domain metadata must
        # resolve normally even when a domain scope is passed (abstention >
        # fabrication: missing metadata never blocks a grounded exact answer).
        e = FakeEntity("urn:li:glossary:plain", "Coverage Date", "glossary_term",
                       domain=None)
        r = _run(make_resolver([e]), "Coverage Date",
                 entity_type="glossary_term", scope=QueryScope(domain="SẢN XUẤT"))
        assert r.state == ResolutionState.RESOLVED
        assert r.resolved is not None
        assert r.resolved.urn == "urn:li:glossary:plain"

    def test_scope_does_not_demote_when_no_domain_match_exists(self):
        # Two candidates, neither matching the scope domain: the scope is a
        # tie-breaker only and must NOT change the outcome (both tie at 0.7,
        # so the same ambiguity result as a no-scope resolve).
        a = FakeEntity("urn:li:dataset:a", "stock_realtime", "dataset", domain="KD")
        b = FakeEntity("urn:li:dataset:b", "stock_reporting", "dataset", domain="KD")
        r = _run(make_resolver([a, b]), "stock",
                 entity_type="dataset", scope=QueryScope(domain="SẢN XUẤT"))
        assert r.state == ResolutionState.NEED_CLARIFICATION
        assert r.ambiguous is True
        assert r.resolved is None
