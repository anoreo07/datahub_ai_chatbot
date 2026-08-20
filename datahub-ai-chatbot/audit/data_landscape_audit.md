# DATA LANDSCAPE AUDIT — DataHub → DataAtlas Chatbot

**Generated from real data only** — PostgreSQL `entities`/`entity_chunks` (DB `chatbot`) + OpenSearch `datahub-rag-chunks-v1` + pulled JSONL `datahub_pull/*.txt`.

**Ground rule**: Không dùng LLM để tạo factual metadata. Không coi embedding/search result là ground-truth. Mọi `UNKNOWN` = không có bằng chứng trong dữ liệu nguồn.

---

## 1. DATASET LANDSCAPE

### 1.1 Entity counts
| Entity type | Count |
|---|---|
| dataset | 8,542 |
| dashboard | 327 |
| glossary_term | 177 |
| glossary_node | 21 |
| **TOTAL** | **9,067** |

Nguồn đã pull nhưng **chưa load vào DB** (có file JSONL trong `datahub_pull/` nhưng không có row trong `entities`):
chart (1,487), container (347), data_flow (221), data_job (0), corp_user (32), corp_group (5), data_platform (86), tag (5), domain (9).

### 1.2 Platform phân bố (dataset)
| platform | count | has description |
|---|---|---|
| powerbi | 3,396 | 0% |
| redshift | 3,089 | 0% |
| glue | 1,336 | 0% |
| SAP | 430 | 100% |
| MES | 141 | 100% |
| Excel | 24 | 100% |
| DMS | 23 | 100% |
| s3 | 17 | 0% |
| Ignition | 13 | 100% |
| Salesforce | 12 | 100% |
| ECUS | 11 | 100% |
| SQ | 9 | 100% |
| JIRA | 7 | 100% |
| EMSP | 6 | 100% |
| TFS | 4 | 100% |
| Saleforce | 3 | 100% |
| Cisco | 3 | 100% |
| PLM | 2 | 100% |
| EXCEL | 2 | 100% |
| Qualrics | 2 | 100% |
| Qualtrics | 1 | 100% |
| …(10 single-item platforms: DCR, GSM, Just, PHC, Portal, IMS, PLAN, TMS, LMS, Hệ) | 10 | 100% |

> **⚠ Platform dirty data**: cùng nền tảng bị ghi nhiều tên khác nhau — `Salesforce`/`Saleforce`, `Excel`/`EXCEL`, `Qualtrics`/`Qualrics`, `JIRA`/`Jira`. Gộp đúng được: **Salesforce ≈ 15**, **Excel ≈ 26**, **Qualtrics ≈ 3**, **JIRA ≈ 8**.

### 1.3 Environment
100% dataset = `PROD`. Không có DEV/QA/UAT/ELM trong dữ liệu hiện tại.

### 1.4 Domain phân bố (dataset)
| domain | count |
|---|---|
| *(none/UNDEFINED)* | 7,581 (88.8%) |
| SẢN XUẤT | 489 |
| TÀI CHÍNH | 201 |
| KINH DOANH | 92 |
| CUNG ỨNG (TT) | 65 |
| LOGISTIC | 47 |
| HẬU MÃI | 34 |
| CUNG ỨNG (NĐH) | 21 |
| PHÁT TRIỂN XE | 12 |

Domain list theo `datahub_pull/domain.txt` (9 domains): SẢN XUẤT, TÀI CHÍNH, KINH DOANH, CUNG ỨNG (TT), LOGISTIC, HẬU MÃI, CUNG ỨNG (NĐH), PHÁT TRIỂN XE, VGreen.

### 1.5 Description
- **704/8,542 (8.2%)** dataset có description.
- **Toàn bộ powerbi (3,396) + redshift (3,089) + glue (1,336) + s3 (17) = 7,838 dataset KHÔNG có description** (0%).
- SAP/MES/Excel/DMS/… (các platform ngoài big-4) có description 100% (ngắn, ~117–417 ký tự, thường là tên report SAP).
- Kết luận: **75%+ dữ liệu không có mô tả** → RAG phụ thuộc nặng vào tên + schema field.

### 1.6 Schema / field metadata
- **7,810/8,542 dataset có schema_fields** (91.4%); 732 dataset không có schema nào.
- Tổng **233,345** field entries. Trung bình ~27 fields/dataset; max **4,561** fields (dataset `.Measure` powerbi).
- Field thường có: `field_path`, `name`, `type` (nativeDataType), `description` (thường null), `nullable`, `is_primary_key`. **Không có** glossary terms gắn field-level, không có tags gắn field-level (cả 2 luôn rỗng).
- Top field types: không lấy được chi tiết kiểu phổ biến từ payload, nhưng quan sát mẫu: `String`, `BIGINT`, `CHARACTER VARYING`, `measure`, `Int64`.

### 1.7 Owner
- **0/8,542 dataset có owner** (0%). Fragment pull DATASET không kéo ownership thành công (introspect OwnerType fail → bỏ owner). Dashboard cũng 0 owner.
- `corp_user.txt` có 32 users / `corp_group.txt` có 5 groups nhưng chưa liên kết vào entity.

### 1.8 Glossary association (dataset ↔ term)
- **Chỉ 20/8,542 dataset có glossary terms** (0.2%). Map:
  - 17 dataset powerbi (ea15_2023, ex1s_2024, eb15_2020/2023, ec15_2023, pd1u_2023, pe1u_2023, v_*…) → term `BOM (Bill of Materials)`.
  - `mrp_stock_req`, `mrp_stock_req_checking` → `MRP`, `Nhu cầu linh kiện`.
  - `v_fact_monthly_inventory_hsd_summarize` → `Số lượng linh kiện hết hạn`.
  - `stg_contact`, `stg_pbed` → `PII`, `AES-256`.
- Kết luận: **quan hệ dataset↔glossary gần như không tồn tại** trong dữ liệu hiện tại.

### 1.9 Upstream / Downstream (lineage)
- **0 dataset có upstream/downstream** (0%). Fragment pull không query `upstreamLineage`/`downstreamLineage`.
- **0 dashboard có input dataset** (0%).
- `data_flow.txt` (221 glue jobs) + `data_job` có thể chứa lineage nếu pull đúng fragment, nhưng **không được load** vào DB và fragment hiện không kéo lineage.

### 1.10 Custom / structured properties
- **0 dataset có raw_properties/customProperties** (0%). `properties.customProperties` rỗng trong JSONL pull.

### 1.11 Report / dashboard liên kết
- Không có document/report entity nào trong DB (0 document, 0 report).
- Dashboard 327 → **0 có upstream link tới dataset**, 0 owners, 0 glossary.
- Chỉ 4/327 dashboard có description; 73/327 có domain.

---

## 2. DOMAIN MAP

9 domains khai báo trong DataHub; dữ liệu hiện có assets thuộc 8 domain (VGreen chỉ có 1 dashboard `VGREEN_MIS_FINANCE`, 0 dataset, 0 term).

| Domain | dataset | dashboard | glossary term | glossary node liên quan |
|---|---|---|---|---|
| **SẢN XUẤT** | 489 | 30 | — | `SẢN XUẤT`, `KPI Logic Production Costing`, `KPI Logic Tồn kho theo BOM` |
| **TÀI CHÍNH** | 201 | 8 | — | `TÀI CHÍNH` |
| **KINH DOANH** | 92 | 1 | — | `KINH DOANH`, `Business Terms`, `[VN] KPIs Logic Sales Car`, `KPIs Logic Sales US` |
| **CUNG ỨNG (TT)** | 65 | 2 | — | `CUNG ỨNG`, `KPI Logic Supply Chain` |
| **LOGISTIC** | 47 | 20 | — | `LOGISTICS` |
| **HẬU MÃI** | 34 | 9 | — | `HẬU MÃI` |
| **CUNG ỨNG (NĐH)** | 21 | 0 | — | `CUNG ỨNG` |
| **PHÁT TRIỂN XE** | 12 | 2 | — | `PHÁT TRIỂN XE` |
| VGreen | 0 | 1 | — | — |
| *(UNDEFINED)* | 7,581 | 254 | 177 | — |

> **Vấn đề lớn nhất**: **88.8% dataset KHÔNG có domain**. Glossary term cũng không có domain (0/177). Nghĩa là **domain-scoping theo query gần như vô dụng với phần lớn dữ liệu** — chỉ dùng được cho ~11% dataset có domain.

**Domain có vocabulary riêng (bằng chứng từ tên dataset/field)**:
- **SẢN XUẤT**: MES, OEE/JPH (OKTS JPH), GA, WIP, MBOM, EBOM, backflush, production order, variant.
- **TÀI CHÍNH**: COGS, CAPEX, OPEX, SG&A, EBITDA, PBT, giá thành, postings, GL, PR/PO.
- **KINH DOANH / HẬU MÃI**: Sell In/Sell Out, Dealer IN/OUT, O2O, Lead, Reservation, DO (Delivery Order), IPTV, CPV, MIS.
- **LOGISTIC / CUNG ỨNG**: coverage date, MRD, MRP, schedule agreement, shipment, PFEP, inbound/outbound.
- **PHÁT TRIỂN XE**: Gate, BCO, ECR, sunk cost, tooling cost, prototype.

---

## 3. DOMAIN-SCOPED GLOSSARY

**Bằng chứng domain-scoping**: Glossary term KHÔNG có trường domain trong dữ liệu (0/177 có domain). Nên không thể tự động gán domain cho term từ metadata. Tuy nhiên **glossary node** đóng vai trò phân nhóm:

| Node (glossary_node) | Nội dung | Domain suy đoán (từ node) |
|---|---|---|
| `Business Terms` | "định nghĩa và KPI logic cho domain báo cáo Kinh doanh" | KINH DOANH |
| `[VN] KPIs Logic Sales Car` | (rỗng) | KINH DOANH |
| `KPIs Logic Sales US` | (rỗng) | KINH DOANH (US) |
| `CUNG ỨNG` | "định nghĩa và KPI logic cho hoạt động cung ứng" | CUNG ỨNG |
| `KPI Logic Supply Chain` | **chứa HTML bảng KPI formula** (KPI#01…KPI#06) | CUNG ỨNG |
| `KPI Logic Production Costing` | (rỗng) | SẢN XUẤT |
| `KPI Logic Tồn kho theo BOM` | (rỗng) | SẢN XUẤT |
| `KPI Logic PFEP` | (rỗng) | CUNG ỨNG/LOGISTIC |
| `SẢN XUẤT`, `TÀI CHÍNH`, `KINH DOANH`, `HẬU MÃI`, `PHÁT TRIỂN XE`, `LOGISTICS` | domain node | theo tên |
| `**DATA SECURITY**`, `Encrytion`, `Data Sensitivity`, `PII`, `AES-256`, `Hashing (SHA-256)` | bảo mật data | GENERAL/DATA SECURITY |
| `Terms`, `KPIs`, `KPIs `, `GENERAL` | nhóm chung | GENERAL |

> **⚠ KHÔNG có liên kết term→node** (glossary_term không có parent/upstream; node không có children). **Nghĩa là không có bằng chứng term nào thuộc node nào** — không thể gộp term vào domain từ metadata. Suy đoán domain cho term phải dựa vào nội dung description, ghi rõ `UNKNOWN`.

### 3.1 Term trùng tên nhưng definition khác nhau (bằng chứng rõ ràng)

**`Coverage Date` — 2 URN, 2 definition khác nhau:**
- `urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b`: *"Coverage Date (Coverage Days) – Số ngày tồn kho đáp ứng nhu cầu"* — định nghĩa theo **inventory coverage**.
- `urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a`: *"KPI: Coverage Date - Số ngày cover nhu cầu từ tồn kho. Số ngày làm việc (theo lịch nhà máy)…"* — định nghĩa theo **working-day coverage của nhà máy**.
- → **KHÔNG được gộp làm một concept**. Đây là case mẫu cho `semantic ambiguity`.

### 3.2 Term gần trùng tên (khác cách viết / thêm mô tả)
- `LOB` vs `LOB - Line of Balance` (2 URN, cùng khái niệm "Line of Balance" nhưng nội dung khác nhau — LOB≈đường cân bằng tồn kho vs LOB≈phương pháp lập kế hoạch tiến độ).
- `PFEP` vs `PFEP (Plan for Every Part)` (2 URN).
- `PPAP` vs `PPAP (Production Part Approval Process)` (2 URN).
- `[Tồn kho] Aging` vs `Aging` (2 URN, cùng khái niệm aging nhưng khác cấu trúc).
- `CPU (Chi phí sản xuất/xe)` vs `CP sản xuất bình quân/xe SOP` (cùng khái niệm Cost Per Unit, tên khác).

### 3.3 Cặp term "global" vs "[VN]" (cùng business concept, khác nguồn gốc định nghĩa)
- `Dealer IN - VF bán buôn cho ĐL/NPP` vs `[VN] Dealer IN - VFT bán buôn cho ĐL/NPP`
- `Dealer OUT - ĐL/NPP bán ra cho Khách hàng` vs `[VN] Dealer OUT - NPP/ĐL bán cho khách hàng cuối`
- `Sell In - Wholesales` vs `[VN] Sell In - Wholesales`
- `Sell Out - Retail` vs `[VN] Sell Out - Retail`
- `New Order - Đơn hàng ký mới` vs `[VN] Đơn hàng ký mới`
- `Pending Order - Đơn hàng tồn` vs `[VN] Đơn hàng tồn`
- → Cặp [VN] là định nghĩa chi tiết (kèm business rule SAP/DMS), cặp global là định nghĩa tổng quát. Nên xem là **2 biểu diễn của cùng concept** nhưng nội dung khác độ chi tiết — không tự gộp.

### 3.4 Heuristic domain-scope cho term (sinh từ audit script, KHÔNG phải metadata)

Vì term không có field domain, script `generate_audit.py` đã thử gán domain bằng keyword match trên name/description (kết quả ghi trong `domain_semantic_map.json["_domain_scoped_glossary_heuristic"]`):

| Kết quả gán | Số term | Ghi chú |
|---|---|---|
| KINH DOANH | 45 | keyword "sales/order/lead/kpi/đơn hàng…" |
| SẢN XUẤT | 11 | "bom/ebom/mbom/jph/wip…" |
| TÀI CHÍNH | 2 | |
| HẬU MÃI | 3 | |
| LOGISTIC | 1 | |
| PHÁT TRIỂN XE | 2 | |
| **MULTI-domain** | ~96 | keyword match trùng nhiều domain (vd `EBITDA`, `COGS`, `WIP`, `SOH`, `Safety Stock`, `Doanh thu`) |
| **UNKNOWN** | 16 | không có keyword khớp |

> **Kết luận quan trọng**: 96/176 term bị keyword-match vào nhiều domain → **không thể tự tin gán domain cho term từ metadata**. Đây là bằng chứng độc lập khẳng định: **domain-scoped glossary KHÔNG xây được từ dữ liệu hiện tại**; cần pull đúng `parentNodes`/domain của glossary hoặc xác nhận tay. Các term như `EBITDA`, `COGS`, `WIP` đúng là cross-domain về mặt ngữ nghĩa kinh doanh, nhưng **cũng có khả năng là term dùng 1 definition chung** — chưa có bằng chứng phân tách.

### 3.5 Nhóm term cần ưu tiên review tay (cross-domain + trùng tên)
`Coverage Date` (2 def), `LOB`/`LOB - Line of Balance`, `PFEP`/`PFEP (Plan for Every Part)`, `PPAP`/`PPAP (Production Part Approval Process)`, `EBITDA`, `COGS`, `WIP`, `Safety Stock`, `SOH`, `Doanh thu`, `Dealer IN/OUT` ×2, `Sell In/Out` ×2.

---

## 4. SEMANTIC AMBIGUITY MAP

### 4.1 Same term, different domain
- Không xác định được từ metadata (term không có domain). **UNKNOWN**.

### 4.2 Same term, different definition (bằng chứng)
- `Coverage Date` (2 URN, def khác nhau) — xem §3.1.

### 4.3 Same dataset name → nhiều URN (1899 nhóm trùng tên)
- **1,899 nhóm tên dataset trùng** (4614 distinct names / 8542 entities).
- Điển hình: `stas` (glue `sap_external.stas` + redshift `sap.external.stas`), `stko`, `super_bom_copt` — **cùng tên, khác platform**.
- `DIM_PACKED` ×21, `Dim_BaoCaoLayout` ×12, `#Measurements` ×7, `.Measure` ×11, `DIM_DATE` ×7, `Buyer_Minstock_EMail` ×8, `Calendar` ×3, `DIM_VARIANT` ×3…
- Đây là **nguồn ambiguity lớn nhất cho entity resolver** — resolver trả 1 entity bằng exact name sẽ có nhiều candidate.

### 4.4 Similar dataset names (prefix family)
- **`dim_` ×1,958**, `da_` ×1,108, `fact_` ×794, `stg_` ×400, `v_` ×347, `xts_` ×188, `ff_` ×167, `tc_` ×148, `ztb_` ×85, `denorm_` ×62, `mrp_` ×56…
- Family `fact_inventory*` ×129 (Fact_Inventory_Coverage, _Coverage_Daily, _Global, _India_Report, _Indonesia_Report…), `fact_sales*` ×26, `mrp*` ×164, `*BOM*` ×498, `*EBOM*` ×86, `*MBOM*` ×69, `dim_date` ×157.
- → `fact_inventory` **không phải một concept duy nhất**; cần phân biệt coverage/forecast/movement/global/regional.

### 4.5 Same field name across datasets
- `plant_id` ×892 dataset, `material_id` ×808, `createdon` ×937, `modifiedon` ×890, `statuscode` ×845, `statecode` ×844, `versionnumber` ×821, `_createdby_value` ×807…
- Field-name ambiguity cực phổ biến: **một field name không định danh được semantic** khi thiếu tên dataset.

### 4.6 Same business concept, biểu diễn khác nhau
- Coverage: `Coverage Date` (2 defs), `Last Date Cover`, `Coverage Days`, `DIM_CURRENT_STOCK_DEMAND`, `Fact_Inventory_Coverage*`.
- Demand: `Nhu cầu linh kiện`, `Fact_Mrp_Demand`, `demand`, `DIM_CURRENT_STOCK_DEMAND`, `Tính toán "Required Demand"`, `Demand Backlog`.
- Tồn kho: `Inventory - Tồn kho xe`, `SOH - Stock On Hand`, `[Tồn kho] Quantity`, `Bc Hàng tồn kho theo kỳ`, `DIM_CURRENT_STOCK_DEMAND`.
- Cost per unit: `CPU (Chi phí sản xuất/xe)` vs `CP sản xuất bình quân/xe SOP`.

### 4.7 Term có nhiều candidate definitions
- Từ phân tích §3.1–3.3: `Coverage Date`, `LOB`, `PFEP`, `PPAP`, `Dealer IN/OUT`, `Sell In/Out`, `New Order`, `Pending Order`, `CPU` đều có ≥2 candidate definitions trong glossary.

---

## 5. ASSET MAP

Ngoài dataset (8,542), dữ liệu hiện có:

| Asset type | Trong DB | Trong datahub_pull (chưa load) | Canonical id | Có description |
|---|---|---|---|---|
| dashboard | 327 | 327 | `urn:li:dashboard:(powerbi,…)` | 4 (1.2%) |
| glossary_term | 177 | 177 | `urn:li:glossaryTerm:<uuid>` | 174 (98%) |
| glossary_node | 21 | 21 | `urn:li:glossaryNode:<uuid>` | 3 (14%) |
| chart | 0 | 1,487 | `urn:li:chart:(powerbi,…)` | ~một số |
| container | 0 | 347 | `urn:li:container:<hash>` | 0 |
| data_flow (glue job) | 0 | 221 | `urn:li:dataFlow:(glue,…)` | ~0 |
| data_platform | 0 | 86 | `urn:li:dataPlatform:*` | — |
| corp_user | 0 | 32 | `urn:li:corpuser:*` | — |
| corp_group | 0 | 5 | `urn:li:corpgroup:*` | — |
| tag | 0 | 5 | `urn:li:tag:*` | — |
| document / report / metric | 0 | 0 | — | — |

> **Kết luận**: hệ thống hiện chỉ có **dataset + dashboard + glossary_term + glossary_node**. Không có document, không có metric entity, không có chart/container/data_flow trong DB (dù đã pull file). Với `metric/formula`, nguồn duy nhất là **description của glossary term/node** (chứa KPI logic + business rule).

---

## 6. REPORT MAP

- **Dashboard (327) là "report" duy nhất**. Tên là nguồn ngữ nghĩa chính (vd `Báo cáo giá thành`, `Bc Hàng tồn kho theo kỳ`, `O2O Performance Dashboard v2`).
- **0 dashboard có link tới dataset nguồn** (upstream rỗng) → **không thể trả lời "dashboard này lấy data từ dataset nào"** → `UNKNOWN`.
- Dashboard với domain (73): chủ yếu SẢN XUẤT (30), LOGISTIC (20), HẬU MÃI (9), TÀI CHÍNH (8).
- **Document/report entity: không tồn tại** trong DB.

---

## 7. METRIC / FORMULA MAP

**Bằng chứng formula thật** tồn tại trong description của glossary term/node:

1. **Node `KPI Logic Supply Chain`** — chứa HTML bảng KPI với formula đầy đủ:
   - `KPI#01 Giá trị tối ưu chi phí BOM`: Actual = tổng chi phí Reduce cost của ý tưởng state "Done/Approved/Implemented"; Tỷ lệ Actual%Target = Actual/(Target/20%)…
   - `KPI#02/03 Số lượng ý tưởng`, `KPI#04 Ý tưởng hoàn thành`, `KPI#05 Premium Shipment Car Actual/Plan`, `KPI#06 Số lượng linh kiện rủi ro (coverage thresholds: local <5/5-12/12-30 ngày, sea <7/7-12/12-30 ngày, Purchasing group PUR1/PUR3/PUR5/PUR7)`.
2. **Term `KPI Logic Production Costing`** (node, rỗng), **`KPI Logic PFEP`** (node, rỗng).
3. **Term `Premium Shipment Car- Actual` / `Premium Shipment Car- Plan`**: formula premium shipment cost, luồng SAP `ZMME525`, trạng thái `Confirmed/Updated`, tính theo `Actual Pickup Date`.
4. **Term `Tính hạn sử dụng (Exp Date)`**: "Tồn kho hạn sử dụng theo Batch (Expiration Inventory by Batch - ZM…)".
5. **Term `Tính toán "Demand of all build phases per variant"`**, `Tính toán "Required Demand"` (Total Demand per Variant), `Tính toán "Quantity per variant"`, `Tính toán "MRD FORECAST DATE"`, `Tính toán "FINAL MRD STATUS"`, `Tính toán "FINAL MRQ"`, `Tính toán "Production Orders"`, `Tính toán "In Transit Material"`, `Tính toán "$Deliver Lead time" từ ZMME147B`, `Tính toán "H part MRD date"`.
6. **Term business rules**: `Xử lý dữ liệu EBOM` (từ PLM), `Xử lý dữ liệu MBOM` (từ SAP), `Merge EBOM và MBOM - Join by Part ID`, `Xác định In BOM/Not In BOM`, `Logic SBOM`, `Lấy thông tin cột vận chuyển`, `Tính toán "FINAL MRD STATUS"`.

> ⚠ **CẢNH BÁO**: các formula trên nằm trong `description` text của glossary term/node. **Node glossary không được chunk/index** (build_chunks_for_entity không xử lý glossary_node) → **formula trong node KHÔNG searchable**. Term có formula thì được index trong `term_definition` chunk.

> Không có field `formula`/`metric` riêng trong schema. Formula chỉ tồn tại dạng text. Nếu không tìm thấy formula → `UNKNOWN`.

---

## 8. LINEAGE MAP

- **Không có lineage nào** trong dữ liệu hiện tại:
  - 0 dataset có upstream/downstream.
  - 0 dashboard có input dataset.
  - 0 term có parent.
  - `data_flow`/`data_job`/`chart`/`container` chưa load và fragment hiện không query lineage field.
- → **Direct lineage: UNKNOWN. Transitive lineage: UNKNOWN. Semantic association**: chỉ có dataset→glossary_term (23 links) và name-prefix/same-family inference (không phải lineage thật, chỉ là heuristic).

---

## 9. DOMAIN → ASSET GRAPH (logical, chỉ ghi relationship có evidence)

```
Domain (8 + VGreen)
 ├─ dataset  (961 có domain / 7581 không)
 ├─ dashboard (73 có domain / 254 không)
 └─ glossary_node (SẢN XUẤT, TÀI CHÍNH, KINH DOANH, HẬU MÃI, PHÁT TRIỂN XE, LOGISTICS, CUNG ỨNG)
      └─ (không link tới term/dataset — UNKNOWN)
dataset ──(glossaryTerms, 23 links)──> glossary_term
dataset ──(upstream/downstream, 0)──> dataset            [UNKNOWN]
dashboard ──(upstream, 0)──> dataset                      [UNKNOWN]
glossary_term ──(parent, 0)──> glossary_node              [UNKNOWN]
```

Các cạnh **có bằng chứng**:
1. dataset → glossary_term: 23 cạnh (20 dataset → BOM/MRP/PII/AES-256/hết hạn).
2. glossary_node → domain (suy đoán từ tên, không phải metadata).
3. dataset → domain: 961 dataset có domain.
4. dashboard → domain: 73.

Mọi cạnh khác (lineage, dashboard-input, term-parent, term-node) = **UNKNOWN / không có bằng chứng**.

---

## 10. DATA QUALITY MAP

| Metric | dataset | dashboard | glossary_term | glossary_node |
|---|---|---|---|---|
| total | 8,542 | 327 | 177 | 21 |
| thiếu description | 7,838 (91.8%) | 323 (98.8%) | 3 (1.7%) | 18 (85.7%) |
| thiếu owner | 8,542 (100%) | 327 (100%) | 177 (100%) | 21 (100%) |
| thiếu domain | 7,581 (88.8%) | 254 (77.7%) | 177 (100%) | 20 (95%) |
| thiếu schema/type | 732 (8.6%) | n/a | n/a | n/a |
| thiếu glossary assoc | 8,522 (99.8%) | 327 (100%) | n/a | n/a |
| thiếu lineage | 8,542 (100%) | 327 (100%) | 177 (100%) | 21 (100%) |
| thiếu report/doc link | 8,542 (100%) | 327 (100%) | n/a | n/a |
| thiếu formula | chỉ trong term/node text | n/a | ~1/3 có | hầu hết |

**Gaps ưu tiên (theo mức ảnh hưởng chatbot)**:
1. **Owner 0%** → mọi câu hỏi về owner trả "không có" (cần pull ownership đúng fragment khi vào mạng công ty).
2. **Lineage 0%** → mọi câu hỏi lineage/impact trả không có (cần pull upstreamLineage/downstreamLineage).
3. **Description 92% thiếu** → RAG không có context mô tả cho powerbi/redshift/glue/s3.
4. **Domain 89% thiếu** → domain-filter/domain-question hạn chế.
5. **Chưa load chart/container/data_flow/tag/corp_user** → mất nguồn lineage + owner + report-chart.
6. **Custom properties 0%**.

---

## 11. SEARCH INDEX AUDIT

### 11.1 PostgreSQL
- Bảng `entities` (generic): columns `urn, entity_type, name, display_name, description, platform, environment, domain, datahub_url, payload(JSON), content_hash, created_at, updated_at`.
- Bảng `entity_chunks`: `entity_id, entity_urn, chunk_type, chunk_index, content, chunk_metadata, content_hash, embedding_model, indexed_at`.
- Entity resolver chạy trên PG (`search_by_name`: ILIKE trên name/display_name/urn; fuzzy fallback top 2000 rows) — **không phải trên OpenSearch**.

### 11.2 OpenSearch index `datahub-rag-chunks-v1`
- **20,616 docs**: `entity_summary` 8,542 + `schema_fields` 11,459 + `dashboard_summary` 327 + `term_definition` 288. (Node glossary: 0 docs.)
- Mapping: `embedding` knn_vector dim **768** (nomic-embed-text), `content` text, keyword fields: `entity_urn, entity_type, chunk_type, domain, platform, environment, owner_names, term_urns, datahub_url, content_hash, page, entity_name.keyword, source_title.keyword`, `updated_at` date.
- **Searchable full-text**: chỉ `content`. **Filterable (term)**: entity_type, chunk_type, domain, platform, environment, owner_names, term_urns.
- **Không index trong OS**: structured owners list, tags, schema_fields, description riêng, certified, custom properties. (Chúng nằm trong PG payload, được dùng post-hoc bằng Python.)

### 11.3 Chunking & embedding
- Chunker: target 600 tokens (ước lượng `len/4`), overlap 75 tokens (~300 từ) — **không có Vietnamese tokenizer**, split theo dấu câu ASCII `.?!`.
- Embedder: Ollama `nomic-embed-text` dim 768; toàn bộ chunk của entity gửi 1 lần (không batch control).
- `MAX_CHUNKS_PER_ENTITY = 64` (hard cap).
- OS `_id` = `{entity_urn}_{chunk_type}_{chunk_index}`.

### 11.4 Metadata filter sử dụng được
- OS: `entity_type`, `domain`, `platform`, `environment`, `owner_names`, `term_urns`, `chunk_type` (term filter).
- PG (post-hoc Python): owners list, tags, schema_fields/columns, certified, description.
- **Domain ACL**: `build_opensearch_acl_filter` là **dead code** — không được gọi trong search path; ACL áp dụng post-hoc bằng Python (fail-open: entity không có row `entity_acls` = truy cập được).

---

## 12. RETRIEVAL RISK

### 12.1 Nhầm lẫn embedding/semantic (dựa trên tên/field thật)
1. **`Coverage Date` (2 defs)**: query "coverage date" → 2 term chunk khác nhau, cùng score gần nhau → LLM có thể gộp/trộn definition. **Risk HIGH**.
2. **`fact_inventory*` family (129)**: "fact_inventory" → nhiều candidate (coverage/global/India/Indonesia/…). **Risk HIGH**.
3. **`dim_vehicle_model` ×2** (powerbi `1_Báo cáo Doanh thu hợp nhất - Car.dim_vehicle_model` vs SAP/DMS variant) + `DIM_MODEL` ×3, `DIM_DATE` ×7. **Risk HIGH**.
4. **`Báo cáo giá thành` ×2**, `Báo cáo tồn kho` ×2, `Báo cáo BOM Assembly` ×2 — trùng tên dashboard/dataset. **Risk MEDIUM**.
5. **`stas`/`stko` glue vs redshift**: cùng tên, khác platform, schema SAP giống nhau (field `stlnr`, `bukrs`, …) → không phân biệt được bằng semantic. **Risk MEDIUM**.
6. **Term vs field cùng tên**: field `material_id` (808 dataset) vs term `MRP`/`BOM`/`material` — field name chung cực phổ biến. **Risk MEDIUM**.
7. **Node `KPI Logic Supply Chain` không index** → formula KPI không retrieve được dù là ground-truth duy nhất. **Risk HIGH (missing evidence)**.
8. **Đồng tên prefix `[LOG]_`/`[CSKH]_`/`[PTX]`** — domain hints trong tên, không trong metadata.

### 12.2 Điều kiện nhạy cảm của resolver
- Entity resolver trả exact-match score 1.0 ngay khi tên khớp → **một tên trùng (1,899 nhóm) sẽ resolve sai entity** nếu không disambiguate (ambiguous khi runner-up ≥0.7 trong khoảng 0.2).
- Deterministic path (count/list) hoạt động tốt; nhưng với tên trùng, answer sẽ dùng entity đầu tiên.

### 12.3 Khuyến nghị mitigation (chưa implement)
- Disambiguation bằng platform+domain trong câu hỏi.
- Label cluster cho `fact_inventory*`, `Coverage Date`, `stas/stko`, `DIM_*` cùng tên.
- Index glossary_node (chứa formula) để không mất ground-truth.

---

## 13. TESTABLE GROUND TRUTH (canonical snapshot)

Đã sinh `data_ground_truth.json` (~8 MB) chứa **mọi dataset (8,542) + dashboard (327) + glossary term (177) + node (21)** với:
- `urn`, `name`, `display_name`, `description`, `platform`, `environment`, `domain`, `datahub_url`, `schema_field_count`, `owners[]`, `glossary_term_urns[]`, `tags[]`, `upstream[]`, `downstream[]`, `custom_properties`, `certified`.
- **Provenance**: mỗi record khớp trực tiếp với row `entities` (nguồn `datahub_pull/*.txt`). `UNKNOWN` = field rỗng trong dữ liệu.

`benchmark_source_inventory.json`: 406 item curated (152 dataset có domain + 177 glossary term + 77 dashboard có domain/desc) — dùng làm candidate cho golden dataset.

**Cách dùng làm benchmark**:
- Mỗi câu hỏi test nên có field `expected` trỏ vào URN + domain; đối chiếu với `data_ground_truth.json`.
- Trường hợp ambiguity (Coverage Date, fact_inventory, stas/stko) nên được **đánh dấu expected = "ambiguous / cần clarify"** chứ không kỳ vọng 1 câu trả lời duy nhất.

---

## 14. KHÔNG SUY ĐOÁN — danh sách UNKNOWN

| Chủ đề | Trạng thái |
|---|---|
| Lineage dataset↔dataset | UNKNOWN (0 data) |
| Dashboard → dataset nguồn | UNKNOWN (0 data) |
| Term → glossary node | UNKNOWN (0 link) |
| Term → domain | UNKNOWN (term không có domain) |
| Report/document/metric entity | UNKNOWN (không tồn tại) |
| Custom properties | UNKNOWN (0 data) |
| Owner | UNKNOWN (0 data — chỉ có 32 corp_user chưa link) |
| Formula/metric riêng | chỉ có trong term/node description text |
| Chart/container/data_flow liên kết | UNKNOWN (chưa load) |
| Field-level glossary/tags | UNKNOWN (luôn rỗng) |

---

## PHỤ LỤC — cách sinh lại (idempotent)

```
.venv/bin/python audit/generate_audit.py
```
Đọc trực tiếp PG (`entities`, `entity_chunks`) và ghi 5 file JSON. Không sửa chatbot. Không gọi LLM.
