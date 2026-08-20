# MENTOR ACCEPTANCE REPORT

Mentor-style acceptance review of the FINAL state (2026-08-18) against the golden suite
(`audit/golden_benchmark.jsonl`, CASE1–6 + categories A–Y) and live mentor probes.

Sources: `audit/final_raw.jsonl`, `audit/final_verdicts.jsonl`, `audit/final_pipeline_verdicts.jsonl`,
`/tmp/opencode/mentor_suite_run.log` (live probes), unit suite (164 passed).

---

## 1. MENTOR CASE REVIEW (live probes + golden equivalents)

### CASE 1 — Domain-scoped term (Demand)
| Probe | Result |
|---|---|
| "Demand là gì?" | Trả đúng term **Nhu cầu linh kiện** (MRP-based). ✓ definition |
| "Demand trong domain SẢN XUẤT là gì?" | Cùng định nghĩa SẢN XUẤT ✓ |
| "Demand trong domain KINH DOANH là gì?" | Cùng 1 định nghĩa duy nhất — **không phân biệt domain KINH DOANH** ✗ |
| "so sánh Demand SẢN XUẤT vs KINH DOANH" | Chỉ trả SẢN XUẤT, **không so sánh / không nêu KINH DOANH → UNKNOWN** ✗ |

**Verdict: PARTIAL.** Single-definition lookup works; same-term-different-domain disambiguation and
cross-domain comparison do not. Golden `CASE1-001/002/003` all fail (evidence/abstention).

### CASE 2 — Report discovery (capacity of vendor)
| Probe | Result |
|---|---|
| "báo cáo capacity của vendor" | `ambiguous=True` clarify — **không tìm ra Report_Supply_Capacity** ✗ |

**Verdict: FAIL.** Golden `CASE2-001` (expected 4 assets incl. Report_Supply_Capacity, VFVN2_DG_R
Supplier Capacity, fact_supplier_capacity) and `CASE2-002` (rpt_survey_weekly_supply_capacity) fail.

### CASE 3 — Metric/formula (Coverage Date)
| Probe | Result |
|---|---|
| "công thức tính của column Coverage Date" | Trả lời rõ "không tìm thấy công thức ... chỉ có mô tả mục đích" — **no fabrication** ✓ (formula-of-column guard active) |

**Verdict: PARTIAL.** Abstention correct (0 hallucination), but golden `CASE3-001` expects the
mechanism (tồn kho + Git, LOB < 0) to be surfaced; currently the resolve step collapses to
ambiguous clarify in the golden form. In the live probe it abstains cleanly. **Formula returned only
with evidence ✓ (the guard works); resolution incomplete ✗.**

### CASE 4 — Report lineage / raw source
| Probe | Result |
|---|---|
| "Report_Supply_Capacity lấy dữ liệu từ đâu?" | Trả "không có lineage được ghi nhận" — **correct UNKNOWN abstention** ✓ |

**Verdict: PARTIAL.** No fabricated lineage ✓; golden `CASE4-001` passes abstention but fails on
suggesting the matching-name dataset per golden. `CASE6-001` (domain-scoped chain) resolves the
**wrong entity** (data-quality report instead of capacity report) ✗.

### CASE 5 — Multi-hop chain (report → term → column → formula → raw source)
| Probe | Result |
|---|---|
| "từ report capacity → ... → nguồn dữ liệu thô" | `insufficient_context=True`, trả "không tìm thấy" — safe but **chain not executed** ✗ |

**Verdict: FAIL.** Golden `CASE5-001` fails (entity + evidence). No fabrication, but multi-hop
planning/decomposition is not operational.

### CASE 6 — Domain report term lineage chain
- Golden `CASE6-001` fails: resolves wrong entity (no capacity report in LOGISTIC scope).
- **Verdict: FAIL.**

---

## 2. ACCEPTANCE CRITERIA ASSESSMENT (FINAL)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | No unresolved critical root causes | **FAIL** | RC-A ambiguity clarify (13 tests) + RC-B domain glossary (3) + RC-C multi-hop (3) still open |
| 2 | No hard-coded dataset-specific fixes | **PASS** | Fixes are generic (intent classifier, evidence focus, formula guard, domain filter) |
| 3 | Complex queries decomposed | **FAIL** | CASE5-001, CASE6-001, Q-001, T-001 → insufficient_context / partial |
| 4 | LLM-first intent works | **PASS** | Intent accuracy 93.8%; r3→FINAL lenient 35/48 |
| 5 | Domain-scoped semantic resolution works | **FAIL** | CASE1-001/002/003, W-001 all fail |
| 6 | Report/document discovery works | **FAIL** | B-002, B-003, CASE2-001/002 fail (4/8 report tests) |
| 7 | Formula returned only with evidence | **PASS** | Hallucination rate 0; CASE3 live probe abstains correctly |
| 8 | Lineage/source tracing works | **PARTIAL** | Single-hop UNKNOWN correct (CASE4, J, M, N pass); multi-hop/domain chain fails |
| 9 | Context/evidence end-to-end | **PARTIAL** | P-001 passes; Q-001 multi-turn fails; T-001 end-to-end fails |
| 10 | No regression suite drop | **PASS** | 164 unit tests pass; 0 chat regression vs baseline |
| 11 | All changes test-protected | **PASS** | Field-specialisation, context, client, entity-resolution tests added |

**Blockers: criteria 1, 3, 5, 6.** A high failure rate remains in the exact critical classes the mentor
called out: domain disambiguation, report discovery, and multi-hop lineage.

---

## 3. FINAL RECOMMENDATION

**CONDITIONAL ACCEPT** — do NOT sign off on the blocking classes yet.

- Accept the **safety posture**: zero hallucination, correct abstention on formulas/lineage/owners,
  no forbidden leaks, no regressions, 164/164 unit tests.
- Do **NOT** accept "system is good" from overall accuracy. The ambiguity-gate behavior
  (RC-A) is the single highest-leverage fix: when candidates share the query's type/domain and one
  dominates, resolve instead of clarifying. Next round must re-run this benchmark and clear
  clusters RC-A, RC-B, RC-C before sign-off.
