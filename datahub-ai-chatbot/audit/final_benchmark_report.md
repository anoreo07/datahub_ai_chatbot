# FINAL BENCHMARK REPORT

- **Corpus**: golden benchmark generated from 8,500+ dataset / asset metadata (`audit/golden_benchmark.jsonl`, 48 tests, categories A–Y + CASE1–6, schema v1.0.0)
- **Backend under test**: local FastAPI `localhost:8000` (local PostgreSQL + OpenSearch, no live corporate DataHub), JWT admin session
- **Run**: `final_raw.jsonl` captured 2026-08-18 (48 observations, conversation_history replayed per test)
- **Analyzers**:
  - *Pipeline analyzer* (`analyze_benchmark.py`, identical to the BASELINE report) — first-incorrect-state pipeline tracing.
  - *Rich semantic analyzer* (`analyze_final.py`) — per-test checks for intent, entity, forbidden exclusion, evidence grounding, domain, citation, retrieval P/R, abstention, hallucination.

---

## 1. HEADLINE RESULT

| Metric | BASELINE | FINAL | Δ |
|---|---|---|---|
| Pipeline PASS (same analyzer as baseline report) | **7 / 48** (14.6%) | **15 / 48** (31.3%) | **+8 fixed, 0 regressed** |
| Rich semantic PASS (response-level) | 24 / 48 (50.0%) | 24 / 48 (50.0%) | 0 net |
| Lenient intent+entity check | r3 = 34 / 48 | **35 / 48** | +1 |

**Regression check: 0 tests regressed.** Every test that passed in the baseline still passes; 8 additional tests were fixed:
`B-001, C-001, CASE2-001, CASE2-002, CASE3-001, I-001, O-002, V-001`.

---

## 2. FINAL METRICS (rich analyzer, response-level)

| Metric | Baseline | Final |
|---|---|---|
| Exact Entity Accuracy | 0.812 | 0.812 |
| Intent Accuracy | 1.000 | 0.938 |
| Evidence Grounding | 0.521 | 0.521 |
| Citation Accuracy | 0.854 | 0.854 |
| Abstention Accuracy | 0.875 | 0.875 |
| Hallucination Rate | 0.000 | 0.000 |
| Domain Resolution Accuracy | 0.917 | 0.917 |
| Forbidden Exclusion | 1.000 | 1.000 |
| Retrieval Precision | 0.695 | 0.677 |
| Retrieval Recall | 0.833 | 0.833 |
| Entity Recall (avg) | 0.833 | 0.833 |
| Entity Precision (avg) | 0.677 | 0.659 |
| Glossary Resolution (18 tests) | 6 pass | 6 pass |
| Report/Dashboard Discovery (8 tests) | 4 pass | 4 pass |
| Metric/Formula Resolution (3 tests) | 1 pass | 1 pass |
| Lineage Accuracy (5 tests) | 4 pass | 4 pass |
| Raw Source Resolution (2 tests) | 1 pass | 1 pass |
| Multi-Hop / Multi-Turn (7 tests) | 1 pass | 1 pass |
| Hard-Negative Retrieval (7 tests) | 5 pass | 5 pass |

Full JSON: `audit/final_metrics.json`.

---

## 3. REMAINING FAILURES (24 tests) BY ROOT-CAUSE CLUSTER

### RC-A: Ambiguity gate fires on every multi-candidate query → `AMBIGUOUS_CLARIFY` (13 tests)
`B-002, B-003, CASE2-001, CASE2-002, CASE3-001, E-001, G-002, G-003, L-001, O-001, R-001, W-001, X-001`

When entity resolution finds multiple candidates, the system returns
`"Có nhiều entity trùng khớp ... Bạn muốn hỏi về entity nào?"` instead of:
- choosing the best candidate when one is clearly correct (B-002 → RPT031-Plant WIP tracking_V2; CASE3-001 → Fact_Inventory_Coverage),
- applying the query's domain constraint as a filter (W-001 TÀI CHÍNH),
- treating a term definition query as a glossary lookup (G-002/G-003/E-001/L-001).

**Impact**: report discovery, metric/formula resolution, field-definition and domain-constrained discovery all degrade to clarification. Safe (never fabricates) but unhelpful. **This is the #1 blocker.**

### RC-B: Domain-scoped glossary & comparison not decomposed (3 tests)
`CASE1-001` (Demand không domain → trả 1 định nghĩa duy nhất thay vì hỏi domain), `CASE1-003` (so sánh SẢN XUẤT vs KINH DOANH → chỉ trả SẢN XUẤT), `CASE1-002` (thiếu linkage dataset mrp_stock_req).

**Impact**: same-term/different-domain disambiguation fails; complex comparison queries answered partially.

### RC-C: Composite / end-to-end queries answered with `insufficient_context` (3 tests)
`CASE5-001` (multi-hop capacity chain), `Q-001` (multi-turn PFEP follow-up), `T-001` (dataset+field+term end-to-end).

### RC-D: Evidence incomplete on otherwise-correct answers (4 tests)
`D-002` (thiếu linkage `v_fact_monthly_inventory_hsd_summarize`), `Y-001` (thiếu URN citation), `G-001` (liệt kê fields nhưng không giải thích `bu_short_name`), `CASE1-002` (thiếu mrp_stock_req).

### RC-E: Wrong entity before evidence (2 tests)
`CASE6-001` (domain LOGISTIC → resolve nhầm "Báo cáo tình trạng kiểm soát dữ liệu rác" thay vì report capacity), `S-001` (PFEP glossary term không resolve được → trả dashboard nhưng không có định nghĩa).

---

## 4. CRITICAL BLOCKERS

Per the mentor acceptance criteria, the following classes still have a high failure rate and are **NOT** yet resolved:

1. **Domain disambiguation** — `CASE1-001/002/003`, `W-001` all fail. Domain-scoped semantic resolution does not gate candidate filtering.
2. **Report/document discovery** — `B-002, B-003, CASE2-001, CASE2-002` fail (ambiguous clarify). 4/8 report-discovery tests fail.
3. **Metric/formula resolution** — `CASE3-001, E-001, L-001` fail (ambiguous clarify on same-name entities). 2/3 metric tests fail.
4. **Multi-hop lineage / raw-source chain** — `CASE5-001, CASE6-001, Q-001, T-001` fail (insufficient_context / wrong entity).

**Positives — non-blocking:**
- Hallucination rate = 0 (no fabricated formulas, lineages, owners, or domain labels).
- Forbidden-exclusion = 1.0 (W-001 does NOT surface SẢN XUẤT datasets even though it fails on domain scoping).
- Citation accuracy 0.854; no regression on any previously-passing test.

---

## 5. FINAL RECOMMENDATION

**Conditional ACCEPT with blockers.** Do **not** conclude "system is good" from overall accuracy: the dominant remaining failure — the ambiguity gate collapsing to a clarification question on any multi-candidate query — is a critical class blocking report discovery, metric/formula and domain-scoped resolution. Recommend:

1. **Next fix round (highest ROI)**: make the ambiguity gate *decision-aware* — when one candidate clearly dominates (score margin) or the query carries a domain/type constraint, resolve instead of clarify; only clarify when candidates are genuinely tied *within the same type*.
2. **Domain constraint propagation**: pass extracted domain into resolver/retrieval as a filter before the ambiguity decision (W-001, CASE1-series).
3. **Multi-hop planner**: keep per-hop UNKNOWN instead of `insufficient_context` (CASE5/6, Q, T).
4. After those, re-run this same benchmark and re-evaluate the 4 blocker clusters.

Full per-test traces: `audit/final_raw.jsonl`; verdicts: `audit/final_verdicts.jsonl`; pipeline verdicts: `audit/final_pipeline_verdicts.jsonl`.
