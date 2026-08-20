# DataAtlas — Yêu cầu của Mentor (Acceptance Criteria)

> Nguồn: `audit/mentor_acceptance_report.md`, `audit/root_cause_map.md`, `docs/SYSTEM_CONTEXT.md`, `docs/semantic_context_precision_report.md`. `[VERIFIED]`

## 1. 7 yêu cầu cốt lõi của mentor

Tổng hợp từ các báo cáo đánh giá của mentor (acceptance criteria của hệ thống):

| # | Yêu cầu | Trạng thái hiện tại | Bằng chứng |
|---|---|---|---|
| **M1** | **Không còn unresolved critical root causes** | ❌ FAIL | RC-A (ambiguity clarify, 13 tests), RC-B (domain glossary, 3), RC-C (multi-hop, 3) vẫn mở |
| **M2** | **Không hard-code dataset-specific fixes** — mọi fix phải generic, không bám tên dataset cụ thể | ✅ PASS | Các fix đều generic (intent classifier, evidence focus, formula guard, domain filter) |
| **M3** | **Complex queries phải được decompose** (multi-hop, comparison, composite) | ❌ FAIL | CASE5-001, CASE6-001, Q-001, T-001 → insufficient_context / partial |
| **M4** | **LLM-first intent classification** hoạt động (thay thế hard keyword rules) | ✅ PASS | Intent accuracy 93.8%; r3→FINAL lenient 35/48 |
| **M5** | **Domain-scoped semantic resolution** — glossary term theo domain phải phân biệt được | ❌ FAIL | CASE1-001/002/003, W-001 fail; "Demand SẢN XUẤT vs KINH DOANH" không so sánh được |
| **M6** | **Report/document discovery** — tìm đúng entity loại report/dashboard | ❌ FAIL | B-002, B-003, CASE2-001/002 fail (4/8 report tests) |
| **M7** | **Formula/field chi tiết chỉ trả khi có evidence** (no fabrication / abstain đúng) | ✅ PASS | Hallucination rate 0; CASE3 live probe abstain đúng |

**Các tiêu chí phụ (mentor acceptance #8-#11):**

| # | Yêu cầu phụ | Trạng thái | Ghi chú |
|---|---|---|---|
| M8 | Lineage/source tracing chính xác | 🟡 PARTIAL | Single-hop UNKNOWN đúng (CASE4, J, M, N); multi-hop/domain chain fail |
| M9 | Context/evidence end-to-end nhất quán | 🟡 PARTIAL | P-001 pass; Q-001 multi-turn fail; T-001 end-to-end fail |
| M10 | Không regression suite drop | ✅ PASS | 164 unit tests pass; 0 chat regression so baseline |
| M11 | Mọi thay đổi phải được test bảo vệ | ✅ PASS | field-specialisation, context, client, entity-resolution tests added |

## 2. Điểm mấu chốt mentor chấm (live probes)

`[VERIFIED]` — `audit/mentor_acceptance_report.md`:

- **CASE 1** (Domain-scoped term "Demand"): single-definition lookup ✓, nhưng **same-term-different-domain disambiguation ✗** và **cross-domain comparison ✗**. → **PARTIAL**.
- **CASE 2** (Report discovery "báo cáo capacity của vendor"): ra `ambiguous=True` clarify, **không tìm ra Report_Supply_Capacity** → **FAIL**.
- **CASE 3** (Metric/formula "Coverage Date"): abstain đúng, **không fabrication** ✓, nhưng không surface mechanism (tồn kho + Git, LOB < 0) → **PARTIAL**.
- **CASE 4** (Report lineage "lấy dữ liệu từ đâu"): trả "không có lineage được ghi nhận" — **correct UNKNOWN abstention** ✓ → **PARTIAL**.
- **CASE 5** (Multi-hop chain report→term→column→formula→raw source): `insufficient_context=True`, trả "không tìm thấy" — **safe nhưng chain không chạy** → **FAIL**.
- **CASE 6** (Domain report term lineage chain): resolve **wrong entity** → **FAIL**.

## 3. Điều mentor đặc biệt nhấn mạnh

1. **Abstention > fabrication**: Trả "không tìm thấy" đúng là TỐT hơn bịa thông tin. Guardrail formula/evidence đang hoạt động đúng hướng. `[VERIFIED]`
2. **Entity resolution đúng là nền tảng**: Hầu hết các fail (RC1b, RC4, RC6, RC7) đều bắt nguồn từ resolve nhầm entity trước khi tool chạy. Fix phải ưu tiên exact-matching + type-preference + domain-scope. `[VERIFIED]`
3. **Ambiguity gate là con dao hai lưỡi**: False-positive clarify (RC1a) chặn cả những case mà top candidate rõ ràng. Cần phân biệt "ambiguity thật" vs "runner-up khác loại không liên quan". `[VERIFIED]`
4. **Domain context phải được giữ và truyền xuyên pipeline**: Query "Demand domain SẢN XUẤT" phải giữ domain trong intent → entity resolution → evidence → answer. `[VERIFIED]`
5. **Multi-hop phải được planner decompose thành chuỗi hops** với kết quả trung gian, không collapse thành single schema lookup. `[VERIFIED]`

## 4. Mục tiêu số mentor hướng tới

- Nâng tỷ lệ pass trên golden suite từ 15/48 (31.3%) lên ≥ 75%+ (rolling đã chạm 36/48 = 75%* strict-ish). `[VERIFIED]`
- Khắc phục 3 nhóm RC còn mở: **RC-A ambiguity clarify, RC-B domain glossary, RC-C multi-hop**. `[VERIFIED]`
- Giữ nguyên thành quả đạt được: intent 93.8%, hallucination 0, regression 0, unit 164 pass. `[VERIFIED]`

## 5. Lưu ý ngữ cảnh

- Mentor chấm dựa trên golden suite 48-case + live probes + unit tests — KHÔNG dựa trên số liệu lenient (64.58%) trong `final_metrics.json`. Scoring chuẩn là **first-incorrect-state pipeline verdict**. `[VERIFIED]`
- Các yêu cầu trên là đích đến cho các phiên làm việc tiếp theo; bộ tài liệu này ghi nhận **trạng thái tại 2026-08-20**.