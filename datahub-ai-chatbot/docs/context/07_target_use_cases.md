# DataAtlas — Target Use Cases

> Trạng thái hỗ trợ được tổng hợp từ benchmark, mentor report, intent taxonomy. `[VERIFIED]` / `[INFERRED]`

## 1. Bảng use-case mục tiêu

| # | Use case | Câu hỏi mẫu | Trạng thái hỗ trợ | Bằng chứng |
|---|---|---|---|---|
| U1 | **Exact dataset lookup** | "Tìm dataset có tên chính xác 'Display Plant Stock Availability'" | 🟢 Tốt (A-002, A-003 PASS) | baseline report |
| U2 | **Schema/field lookup** | "fact_part_movement có trường warehouse_id nghĩa là gì?" | 🟡 Trung bình (Group A 4/10) | semantic report |
| U3 | **Field property** | "movement_id kiểu dữ liệu gì?" | 🟢 Tốt (A-02/A-05/A-06 PASS) | semantic report |
| U4 | **Glossary term definition** | "Demand là gì?" | 🟡 PARTIAL (single-term OK, domain-scoped fail) | mentor CASE1 |
| U5 | **Term → datasets** | "Term này áp dụng cho dataset nào?" | 🟡 Trung bình (RC2, F-series fail) | root_cause_map |
| U6 | **Owner lookup** | "Dataset này do ai sở hữu?" | 🟢 Tốt (deterministic, commit 8a87be5c) | code |
| U7 | **Domain lookup** | "Dataset thuộc domain nào?" | 🟢 Tốt (deterministic) | code |
| U8 | **Lineage (single-hop)** | "Report_Supply_Capacity lấy dữ liệu từ đâu?" | 🟢 Correct UNKNOWN abstention (CASE4 PASS) | mentor report |
| U9 | **Lineage (multi-hop)** | "từ report capacity → ... → nguồn dữ liệu thô" | 🔴 FAIL (CASE5, M/N) | mentor report |
| U10 | **Impact analysis** | "Nếu đổi field này ảnh hưởng gì?" | 🟡 Trung bình (planner-executor) | code + tests |
| U11 | **Report/dashboard discovery** | "báo cáo capacity của vendor" | 🔴 FAIL (CASE2, H-series, B-002/3) | mentor report |
| U12 | **Count/listing** | "Có bao nhiêu dataset domain SẢN XUẤT?" | 🟡 RC3 (count tool global) | root_cause_map |
| U13 | **Composite/multi-question** | 2 câu hỏi trong 1 turn | 🟡 PARTIAL (R-001, S-001) | root_cause_map |
| U14 | **Comparison across datasets** | "so sánh Demand SẢN XUẤT vs KINH DOANH" | 🔴 FAIL (CASE1-003, C1) | mentor report |
| U15 | **Multi-turn follow-up** | "nó" / "bảng này" (anaphora) | 🟡 PARTIAL (Q-001 fail, M1) | coreference + test |
| U16 | **Metric/formula** | "công thức tính Coverage Date" | 🟡 PARTIAL (abstain đúng, không surface formula) | mentor CASE3 |
| U17 | **SQL generation** | "Viết SQL cho..." | 🟡 Trung bình (SQL_GENERATION intent) | intent taxonomy |
| U18 | **Graph query / related datasets** | join fields, related datasets | 🟡 Trung bình (graph, graph_expander) | code |
| U19 | **Chat chung (GENERAL)** | chitchat, greeting | 🟢 Tốt (GENERAL path, refusal prompt) | code |
| U20 | **Vision** | ảnh/chart image trong câu hỏi | 🟡 Mới (vision, image_records=1) | code |
| U21 | **Document QA** | hỏi về tài liệu import | 🟡 Trung bình (DOCUMENT_QA intent) | intent taxonomy |

## 2. Use-case mentor đặc biệt nhấn mạnh (cần đạt)

Từ `mentor_acceptance_report.md` — 6 CASE chính là "hợp đồng" chất lượng:

1. **CASE1 — Domain-scoped term**: hỏi term theo domain phải ra đúng definition của domain đó; so sánh cross-domain.
2. **CASE2 — Report discovery**: câu hỏi về "báo cáo X" phải resolve đúng report/dashboard entity (VD Report_Supply_Capacity, fact_supplier_capacity).
3. **CASE3 — Metric/formula**: trả công thức chỉ khi có evidence; abstain khi không có (đã đạt phần abstain).
4. **CASE4 — Report lineage**: trace nguồn dữ liệu của report; trả UNKNOWN đúng khi không có lineage (đã đạt single-hop).
5. **CASE5 — Multi-hop chain**: report → term → column → formula → raw source, phải chạy hết chain.
6. **CASE6 — Domain report term lineage chain**: chain theo domain, resolve đúng entity trong scope domain.

## 3. Use-case đang chạy tốt (giữ nguyên)

- Exact dataset lookup (A-series). `[VERIFIED]`
- Field property với field rõ ràng (A-02, A-05, A-06). `[VERIFIED]`
- Owner/domain deterministic lookup. `[VERIFIED]`
- Abstention/no-fabrication (CASE3, CASE4). `[VERIFIED]`
- Multi-turn context giữ (85 regression passes, 1,168 conversation history). `[OBSERVED]`

## 4. Use-case theo domain nghiệp vụ

Dựa trên 9 domains trong DB `[VERIFIED]`:

| Domain | Dataset count | Câu hỏi tiêu biểu |
|---|---|---|
| SẢN XUẤT | 519 | capacity, BOM, production plan, plant stock |
| TÀI CHÍNH | 209 | doanh thu, chi phí, AR/AP |
| KINH DOANH | 93 | sales, target |
| CUNG ỨNG (TT) | 67 | vendor capacity, supplier |
| LOGISTIC | 67 | warehouse, delivery |
| HẬU MÃI | 43 | warranty, CSKH |
| CUNG ỨNG (NĐH) | 21 | component demand |
| PHÁT TRIỂN XE | 14 | development |
| VGreen | 1 | — |

## 5. Ưu tiên cải thiện (theo mức ảnh hưởng tới benchmark)

1. Report/dashboard discovery (U11) — ảnh hưởng nhiều case nhất. `[VERIFIED]`
2. Domain-scoped glossary resolution (U4) + cross-domain comparison (U14). `[VERIFIED]`
3. Multi-hop decomposition (U9, U13, U14). `[VERIFIED]`
4. Count tool scoping (U12). `[VERIFIED]`
5. Field-level precision với field phức tạp (U2, U3). `[VERIFIED]`