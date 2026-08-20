# DataAtlas — Failures hiện tại & hệ thống test

## 1. Tổng quan benchmark (số liệu qua các phiên bản)

`[VERIFIED]` — từ `audit/*`:

| Phiên bản | PASS | Tổng | Tỷ lệ | Ghi chú |
|---|---|---|---|---|
| BASELINE | 7 | 48 | 14.6% | pipeline verdict, first-incorrect-state |
| FINAL (pipeline) | 15 | 48 | 31.3% | sau các fix r2→r3→final |
| FINAL (rich semantic) | 24 | 48 | 50% | rich semantic verdict |
| FINAL lenient (`final_metrics.json`, Aug 19) | 31 | 48 | 64.58% | lenient scoring, accuracy metrics |
| Subset (12 tests, `final_metrics_subset.json`) | 6 | 12 | 50% | Aug 19 |
| Rolling `r26` (26-case harness) | 26 | 26 | 100% | harness `test_cases_26.jsonl` |
| Rolling golden regression (`rolling_fix_report.md`) | 36 | 48 | 75%* | "*" = strict-ish, xem báo cáo |
| **SYSTEM_CONTEXT 85-case semantic** | 38 | 85 | 44.7% | `docs/SYSTEM_CONTEXT.md` (semantic precision) |
| Regression 85-case HTTP-level | 85 | 85 | 100% | `docs/regression_report.md` — chỉ status/không crash |

> ⚠️ Hai "85" khác nhau: `regression_report.md` (Aug 12) là HTTP-level toàn PASS; `SYSTEM_CONTEXT.md` là semantic content review — 38/47 FAIL thực chất về chất lượng. `[VERIFIED]`

## 2. Root causes (audit/root_cause_map.md + SYSTEM_CONTEXT)

### 2.1 Root causes chính (baseline map) `[VERIFIED]`

| RC | Mô tả | Ảnh hưởng |
|---|---|---|
| RC1a | False-positive ambiguity gate — runner-up khác loại entity vượt threshold | nhiều test clarify sai |
| RC1b | Fuzzy name-matching resolve nhầm entity (db_rows=0 → fuzzy lệch) | 7 tests (B-001, CASE3-001, G-002, O-002, T-001, V-001, X-001) |
| RC2 | Intent keyword router misroutes NL discovery + đảo chiều linkage | 5 tests (B-002, B-003, F-001/2/3) |
| RC3 | Count tool không có entity/domain filter → trả global count | 3 tests (C-001/2/3) |
| RC4 | Glossary resolution thiếu domain scoping + duplicate-term surfacing | 4 tests (CASE1-001/2, E-001, L-001) |
| RC5 | Composite/multi-hop/comparison không decompose | 4 tests (CASE1-003, CASE5-001, R-001, S-001) |
| RC6 | Report/dashboard discovery fails (resolve nhầm dataset) | 5 tests (CASE2-001/2, H-001/2/3) |
| RC7 | Lineage queries resolve wrong entity trước khi lineage tool chạy | 5 tests (CASE4-001, CASE6-001, J-001, M-001, N-001) |
| RC8 | Field-property/formula evidence không injected vào context | 3 tests (G-001, G-003, K-001) |

### 2.2 Root causes từ SYSTEM_CONTEXT 85-case (RC-1..RC-8) `[VERIFIED]`

`docs/SYSTEM_CONTEXT.md` đưa 8 root causes khác (RC-1..RC-8) với 47 FAIL trong 85 case: 25 critical, 15 high, 7 medium (theo `semantic_context_precision_report.md`).

Failure distribution (from `semantic_context_precision_report.md`): context propagation, evidence usage, entity switching, tool selection, multi-subquestion, citation, Thinking Mode.

### 2.3 Failure severity (semantic report) `[VERIFIED]`

| Severity | FAIL count |
|---|---|
| Critical | 25 |
| High | 15 |
| Medium | 7 |
| Low | 0 |

### 2.4 Nhóm lỗi nổi bật

- **Field-level precision (Group A)**: 4/10 PASS — field-op detection yếu với field tên không snake_case ("quantity có kiểu dữ liệu gì?" → hybrid search nhầm entity), double-ask misroute, connective phrases misparse. `[VERIFIED]`
- **Thinking Mode**: 1/11 đúng (F04), 0/10 nhóm H — **under-trigger nghiêm trọng**; `_complex=true` chỉ phát khi intent phức tạp rõ ràng. `[VERIFIED]`
- **Over-answering**: 3/10 nhóm E + schema-dump trong A/B/F — đã có fix "focused field answers" (commit `a6dcb717`) nhưng vẫn còn case. `[VERIFIED]`
- **Citation**: answer có inline `[E-id]` đúng evidence; `citations[]` structured thường rỗng. `[VERIFIED]`

## 3. Trạng thái 12 tiêu chí mentor acceptance (FINAL) `[VERIFIED]`

Từ `audit/mentor_acceptance_report.md`:

| # | Tiêu chí | Trạng thái |
|---|---|---|
| 1 | Không còn critical root causes mở | **FAIL** (RC-A ambiguity clarify 13 tests + RC-B domain glossary 3 + RC-C multi-hop 3) |
| 2 | Không hard-code dataset-specific fixes | **PASS** |
| 3 | Complex queries decomposed | **FAIL** |
| 4 | LLM-first intent hoạt động | **PASS** (intent accuracy 93.8%) |
| 5 | Domain-scoped semantic resolution | **FAIL** (CASE1-001/2/3, W-001) |
| 6 | Report/document discovery | **FAIL** (B-002/3, CASE2-001/2 — 4/8 report tests) |
| 7 | Formula chỉ trả với evidence | **PASS** (hallucination 0) |
| 8 | Lineage/source tracing | **PARTIAL** (single-hop UNKNOWN đúng; multi-hop fail) |
| 9 | Context/evidence end-to-end | **PARTIAL** |
| 10 | Không regression suite drop | **PASS** (164 unit tests) |
| 11 | Mọi thay đổi được test bảo vệ | **PASS** |
| 12 | *(kết quả mentor)* | CASE1 PARTIAL · CASE2 FAIL · CASE3 PARTIAL · CASE4 PARTIAL · CASE5 FAIL · CASE6 FAIL |

## 4. Hệ thống test hiện tại

### 4.1 Unit tests `[VERIFIED]`

- 164 unit tests pass (mentor report). `[OBSERVED]`
- `tests/unit/`: auth, datahub, document_parsers, mappers, services, sync.
- Các test retrieval: `tests/retrieval/` (test_intent, test_entity_resolver, test_fuzzy, test_citation, test_context_builder, test_entity_extraction, ...).
- `tests/context/`: context_propagation, field_level_context.
- `tests/indexing/`, `tests/ingestion/`, `tests/evaluation/`, `tests/api/`, `tests/visual/`, `tests/thinking/`.

### 4.2 Integration tests `[VERIFIED]`

`tests/integration/`: test_acl_filters, test_chunk_repository, test_count_listing, test_entity_repository, test_full_sync, test_index_job_repository, test_lineage, test_quality_report, test_sql_generation, test_sync_repository. Cần Postgres+Redis+OpenSearch chạy.

### 4.3 E2E tests `[VERIFIED]`

`tests/e2e/`: test_chat_e2e, test_domain_rbac_e2e, test_impact_e2e.

### 4.4 Benchmark harness `[VERIFIED]`

- **`audit/harness26.py`** — 26-case harness (`test_cases_26.jsonl`), dùng cho rolling_fix_report.
- **Golden suite** — `audit/golden_benchmark.jsonl` (48 cases, categories A–Y + CASE1–6).
- **Metrics** — `audit/final_metrics.json`, `final_metrics_subset.json`.
- **Traces** — `audit/baseline_traces.jsonl`, `final_raw.jsonl`, `baseline_raw.jsonl`, verdicts files.

### 4.5 Lệnh chạy (từ AGENTS.md)

```bash
python -c "from app.main import app; print('OK')"
python -m pytest tests/unit -q --timeout=60
python -m pytest tests/integration -q --timeout=120
ruff check .
mypy app ingestion indexing retrieval llm sync workers database config infrastructure
```

## 5. Các metric quan trọng còn yếu (final_metrics.json, Aug 19) `[VERIFIED]`

Từ `audit/final_metrics.json` (31/48 = 64.58% lenient):

- `glossary_resolution_accuracy` = **0.2292** — rất thấp.
- `report_discovery_precision` = **0.0** — không tìm ra report.
- `raw_source_resolution` = **0/2 fail** — không resolve raw source.
- `multi_hop` = 3/7.
- `multi_turn` = 1/3.
- `abstention_rate` / hallucination: thấp (guard hoạt động). `[INFERRED]`

## 6. Nhóm lỗi còn mở theo rolling_fix_report

`[VERIFIED]` — r26 (26-case) đạt 26/26; golden regression 36/48* — còn ~10-12 case mở, tập trung ở: report discovery, domain glossary, multi-hop, ambiguity clarify (RC-A/B/C như mentor report).

## 7. Hạn chế của hệ thống đánh giá

1. Golden dataset sinh từ subset nhỏ (135 datasets ground truth) — không đại diện 8,542 datasets. `[INFERRED]`
2. Hai bộ benchmark (48-case pipeline verdict vs 85-case semantic) cho kết quả khác nhau — cần chuẩn hoá scoring. `[VERIFIED]`
3. `final_metrics.json` (lenient 64.58%) vs `final_benchmark_report.md` (strict 31.3%) — chênh lệch lớn do phương pháp chấm. `[VERIFIED]`