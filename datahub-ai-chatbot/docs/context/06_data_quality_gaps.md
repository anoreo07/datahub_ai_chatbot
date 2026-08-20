# DataAtlas — Data Quality Gaps

> Nguồn: `audit/data_landscape_audit.md`, read-only DB queries 2026-08-20, code review. `[VERIFIED]` / `[OBSERVED]`

## 1. Khoảng trống dữ liệu lớn nhất

### 1.1 Nhiều loại entity đã pull nhưng chưa load vào DB/index `[VERIFIED]`

| Loại | Pull (datahub_pull) | Trong DB entities | Khoảng trống |
|---|---|---|---|
| dataset | 8,542 | 8,542 | ✅ đủ |
| dashboard | 327 | 327 | ✅ đủ |
| glossary_term | 177 | 177 | ✅ đủ |
| glossary_node | 21 | 21 | ✅ đủ |
| **chart** | **1,487** | **0** | ❌ **không index** |
| **container** | **347** | **0** | ❌ |
| **data_flow** | **221** | **0** | ❌ |
| **data_platform** | **86** | **0** | ❌ |
| **corp_user** | **32** | **0** | ❌ |
| **domain** | **9** | **0** | ❌ |
| **tag** | **5** | **0** | ❌ |
| **corp_group** | **5** | **0** | ❌ |

> Hệ quả: câu hỏi về chart/flow/tag/domain/người dùng hiện không có dữ liệu để trả lời. Report discovery (RC6) một phần do dashboards có nhưng "report" không được model hoá rõ. `[INFERRED]`

### 1.2 Mô tả (description) thiếu trầm trọng ở big-4 platforms `[VERIFIED]`

Từ `data_landscape_audit.md`:

| platform | count | has description |
|---|---|---|
| powerbi | 3,396 | **0%** |
| redshift | 3,089 | **0%** |
| glue | 1,336 | **0%** |
| SAP | 430 | 100% |
| MES | 141 | 100% |
| Excel | 24 | 100% |
| DMS | 23 | 100% |
| s3 | 17 | **0%** |

> **7,838 datasets** (powerbi 3,396 + redshift 3,089 + glue 1,336 + s3 17) **không có description** — RAG không có nội dung để truy vấn semantic. `[INFERRED]`

### 1.3 Domain thiếu `[VERIFIED]`

- 7,581/8,542 datasets (88.8%) **không có domain** (NULL/UNDEFINED). Chỉ ~961 datasets có domain. `[OBSERVED]`
- Domain counts (dataset-only, theo `data_landscape_audit.md`): SẢN XUẤT=489, TÀI CHÍNH=201, KINH DOANH=92... (khác số all-entities ở `00/03` vì glossary terms cũng mang domain).
- Domain-scoped queries (mentor M5) chỉ khả thi với subset có domain.

### 1.4 Platform dirty data `[VERIFIED]`

- `Salesforce`/`Saleforce`, `Excel`/`EXCEL`, `Qualtrics`/`Qualrics`, `JIRA`/`Jira` — cùng platform ghi nhiều tên.
- Gộp đúng: Salesforce ≈ 15, Excel ≈ 26, Qualtrics ≈ 3, JIRA ≈ 8.
- Ngoài ra 10 platform single-item (DCR, GSM, Just, PHC, Portal, IMS, PLAN, TMS, LMS, "Hệ").

## 2. Vấn đề đồng nhất dữ liệu (ambiguity) `[VERIFIED]`

- **Cùng tên dataset, khác platform**: `stas` (glue `sap_external.stas` + redshift `sap.external.stas`), `stko`, `super_bom_copt` — schema SAP giống nhau (field `stlnr`, `bukrs`...), không phân biệt được bằng semantic → **Risk MEDIUM**. `[VERIFIED]`
- **Tên dataset có khoảng trắng thừa**: `"List of Vendor Master Data "` (có space cuối) — benchmark A-001 fail vì exact-match không khớp. `[VERIFIED]`
- **Glossary term trùng tên nhiều URN**: "Coverage Date" có 2 URNs nhưng chỉ surface 1 definition (RC4). `[VERIFIED]`
- **Name không chuẩn hoá**: tên có `[CSKH]`, `_`, dấu cách, chữ hoa/thường trộn lẫn. `[OBSERVED]`

## 3. Khoảng trống về ACL / RBAC / audit `[OBSERVED]`

- **ACL**: chỉ 884/9,067 entities có ACL; toàn bộ `is_public=false`, `classification='internal'`. 8,183 entities không có ACL → default allow. `[OBSERVED]`
- **RBAC users**: 0 user, 0 user_role — RBAC domain model tồn tại nhưng chưa có người dùng thật. `[OBSERVED]`
- **Audit logs**: 0 rows — không trace được quyết định deny. `[OBSERVED]`

## 4. Khoảng trống về metadata mở rộng `[UNKNOWN]` / `[INFERRED]`

- **Owner**: nhiều dataset thiếu owner (ground truth `for_gpt.txt` ghi nhiều "(khong co owner)"). `[OBSERVED]`
- **Lineage**: nhiều entity không có lineage record (CASE4 trả "không có lineage"). `[OBSERVED]`
- **Schema**: `entity_chunks` lưu schema chunks, nhưng field description/formula thiếu ở nhiều field (RC8). `[INFERRED]`
- **Certified/tags**: tag chỉ có 5 records pull, chưa load. `[OBSERVED]`

## 5. Khoảng trống về ground-truth test `[VERIFIED]`

- `context_data.txt`/`for_gpt.txt` chỉ là subset **135 datasets** (không phải 8,542) — benchmark sinh từ subset có thể không đại diện corpus thật. `[VERIFIED]`
- Golden suite 48-case + 26-case harness sinh từ snapshot có domain mẫu; có thể thiếu coverage các platform ít dữ liệu. `[INFERRED]`

## 6. Rủi ro về chất lượng nếu không xử lý

1. Semantic search trên big-4 (7,838 datasets không description) sẽ dựa vào tên + field names, dễ nhầm. `[INFERRED]`
2. Domain-scoped answer không đáng tin khi 88.8% entities không có domain. `[INFERRED]`
3. Dirty platform names làm hỏng filter `platform` query. `[VERIFIED]`
4. Report/chart không index → report discovery (M6) không bao giờ chạm đích. `[VERIFIED]`
5. ACL thưa + không có user → không thể kiểm thử RBAC thật. `[OBSERVED]`

## 7. Khuyến nghị ưu tiên (đề xuất — không phải hiện trạng) `[INFERRED]`

1. Load nốt chart/container/data_flow/tag/domain/corp_user vào DB + index. 
2. Chuẩn hoá platform names (normalize map).
3. Tách domain cho datasets còn thiếu (hoặc xử lý NULL domain đúng cách trong query).
4. Chuẩn hoá tên (trim whitespace, chuẩn hoá hoa/thường).
5. Seed RBAC users + kích hoạt audit ghi log.