"""Discovery merge scoring: full-token matches must outrank weak vector hits.

Regression for the type-aware discovery case: "dataset nào phục vụ kiểm tra
WIP giữa MES và SAP?" must surface the dashboard "Báo cáo check WIP MES_SAP"
(a full 4/4 token match) instead of burying it under unrelated vector datasets.
"""
import pytest

from retrieval.discovery import expand_query_tokens, score_entity


class _Entity:
    def __init__(self, name: str, urn: str) -> None:
        self.name = name
        self.display_name = name
        self.urn = urn
        self.deleted = False
        self.entity_type = "dataset"
        self.platform = "redshift"
        self.domain = None
        self.payload = {}


@pytest.mark.asyncio
async def test_full_token_match_scores_above_flat_floor() -> None:
    tokens = expand_query_tokens("dataset nào phục vụ kiểm tra WIP giữa MES và SAP")
    assert {"check", "wip", "mes", "sap"} <= tokens
    dashboard = _Entity("Báo cáo check WIP MES_SAP",
                        "urn:li:dashboard:(powerbi,reports.abc)")
    hits = score_entity(tokens, dashboard)
    assert hits == 8.0
    max_hits = max(1.0, len(tokens) * 2.0)
    merged_score = min(1.0, 0.9 + 0.1 * hits / max_hits)
    assert merged_score == 1.0


@pytest.mark.asyncio
async def test_partial_match_keeps_flat_floor() -> None:
    tokens = expand_query_tokens("dataset nào phục vụ kiểm tra WIP giữa MES và SAP")
    weak = _Entity("fact_bf_mes", "urn:li:dataset:(redshift,fact_bf_mes,PROD)")
    hits = score_entity(tokens, weak)
    assert hits < 8.0
    max_hits = max(1.0, len(tokens) * 2.0)
    merged_score = min(1.0, 0.9 + 0.1 * hits / max_hits)
    assert merged_score >= 0.9


@pytest.mark.asyncio
async def test_expand_tokens_covers_acronyms_and_english() -> None:
    tokens = expand_query_tokens("có báo cáo nào về WIP giữa MES và SAP?")
    assert "wip" in tokens and "mes" in tokens and "sap" in tokens
