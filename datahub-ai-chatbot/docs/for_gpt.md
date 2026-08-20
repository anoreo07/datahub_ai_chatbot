# BOM Report — Context dữ liệu cho GPT (Demo Document Processing)

> File này chứa **context dữ liệu cụ thể, chi tiết** của một báo cáo BOM (Bill of
> Materials — bảng kê nguyên vật liệu / linh kiện cấu thành sản phẩm) để GPT có
> thể bám vào đó mà sinh ra những câu hỏi cụ thể (và trả lời chính xác) khi demo.
>
> Dữ liệu bên dưới mô tả đúng nội dung sẽ được import vào chatbot qua luồng
> `POST /api/v1/documents/import` (`ingestion/document_ingestion.py`). Sau khi
> import, mọi câu hỏi ở mục 5 đều có thể trả lời được từ dữ liệu này (deterministic,
> không cần LLM bịa).

---

## 1. Báo cáo BOM là gì?

**BOM (Bill of Materials — bảng kê nguyên vật liệu)** là danh sách đầy đủ các
thành phần (linh kiện, nguyên vật liệu, bán thành phẩm, sub-assembly) cần thiết
để sản xuất / lắp ráp ra **1 đơn vị sản phẩm hoàn chỉnh**.

Một báo cáo BOM thường chứa:

| Thành phần | Mô tả |
|---|---|
| **Header BOM** | Số hiệu BOM, tên sản phẩm, revision, trạng thái, ngày hiệu lực, người sở hữu |
| **Level** | Bậc phân cấp: Level 0 (sản phẩm hoàn chỉnh) → Level 1 (sub-assembly) → Level 2 (linh kiện) → Level 3 (phụ kiện/phụ tùng) |
| **Part number** | Mã số vật tư duy nhất của từng dòng |
| **Mô tả** | Tên chi tiết của linh kiện |
| **Số lượng (Qty)** | Số lượng dùng cho 1 đơn vị parent |
| **UOM** | Đơn vị tính (pcs, bộ, cell, tấm, con, lít…) |
| **Nhà cung cấp** | Vendor cung cấp linh kiện |
| **Đơn giá / Standard cost** | Chi phí chuẩn của dòng |
| **Lead time** | Thời gian đặt hàng / nhận hàng (ngày) |
| **Vật liệu** | Chất liệu chính của linh kiện (nhôm, đồng, thép, silicon…) |

Trong demo này, BOM là của một **bộ pin xe điện (Battery Pack)** — mỗi chiếc xe
dùng đúng 1 bộ pin này.

---

## 2. Dữ liệu Document (sẽ được import)

### 2.1 Header BOM

| Field | Giá trị |
|---|---|
| Số hiệu BOM | `BOM-EV-BAT-001` |
| Tên sản phẩm | **Battery Pack VF8 — 72 kWh** |
| Revision | **Rev C** |
| Ngày phát hành | 2026-06-15 |
| Ngày hiệu lực | 2026-07-01 |
| Trạng thái | **Released** |
| Người sở hữu | Nguyễn Văn An — Bộ phận Battery Engineering |
| Nhà máy | VinFast Plant Hai Phong (in-house) |
| Định mức | 1 bộ pin / 1 xe VF8 |

### 2.2 Bảng line items

| STT | Level | Part Number | Mô tả | Qty | UOM | Nhà cung cấp | Đơn giá (USD) | Lead time (ngày) | Vật liệu |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | `PK-VF8-72` | Battery Pack VF8 72kWh (top assembly) | 1 | bộ | VinFast Plant Hai Phong | 6,200 | 5 | — |
| 2 | 1 | `MG-FR` | Module Group Front (24 cells) | 2 | bộ | VinFast Plant Hai Phong | 1,850 | 3 | — |
| 3 | 1 | `MG-RR` | Module Group Rear (24 cells) | 2 | bộ | VinFast Plant Hai Phong | 1,850 | 3 | — |
| 4 | 1 | `BMS-MAIN` | BMS Controller (main) | 1 | bộ | Continental | 540 | 45 | PCB + IC |
| 5 | 1 | `TMS-COOL` | Thermal Management System | 1 | bộ | Mahle | 620 | 30 | Nhôm + coolant |
| 6 | 1 | `ENC-HSG` | Enclosure & Housing | 1 | bộ | VinFast Plant Hai Phong | 380 | 7 | Nhôm 6061 |
| 7 | 1 | `HV-HARNESS` | HV Harness assembly | 1 | bộ | Leoni | 210 | 20 | Cáp đồng |
| 8 | 2 | `CELL-NCM-217` | Cell NMC 21700 5.0Ah | 96 | cell | CATL | 42 | 60 | NMC811 |
| 9 | 2 | `BMS-PCB` | BMS Main PCB | 1 | pcs | Continental | 120 | 45 | FR4 |
| 10 | 2 | `SNS-CUR` | Current Sensor (Hall) | 2 | pcs | Continental | 18 | 30 | — |
| 11 | 2 | `CTCT-HV` | HV Contactor 500A | 2 | pcs | TE Connectivity | 55 | 25 | Cu/Ag |
| 12 | 2 | `CP-COOL` | Cooling Plate (alu milled) | 2 | tấm | Mahle | 85 | 21 | Nhôm 6063 |
| 13 | 2 | `HOSE-COOL` | Coolant Hose + fitting | 4 | bộ | Mahle | 12 | 14 | EPDM |
| 14 | 2 | `PUMP-CL` | Coolant Pump 12V | 1 | cái | Bosch | 95 | 28 | — |
| 15 | 2 | `TANK-EXP` | Expansion Tank | 1 | cái | Kautex | 22 | 18 | HDPE |
| 16 | 2 | `COOLANT` | Coolant G48 (50%) | 8 | lít | BASF | 6 | 10 | Glycol |
| 17 | 2 | `BUSBAR` | Busbar Copper 3x40mm | 24 | thanh | APTIV | 8 | 15 | Cu ETP |
| 18 | 2 | `SEAL-GSK` | Sealing Gasket pack | 4 | bộ | Freudenberg | 16 | 12 | NBR |
| 19 | 3 | `FOAM-FR` | Fire-retardant foam (module) | 12 | tấm | 3M | 4 | 8 | PU foam |
| 20 | 3 | `SCR-M6` | Screw M6x20 (module) | 288 | con | Bossard | 0.05 | 5 | Thép 8.8 |
| 21 | 3 | `CONN-HV` | HV Connector (leakage) | 4 | cái | TE Connectivity | 14 | 16 | — |
| 22 | 3 | `FUSE-HV` | HV Fuse 500A | 1 | cái | Littelfuse | 30 | 22 | — |
| 23 | 3 | `IC-MON` | Cell Monitoring IC (BQ79616) | 24 | con | TI | 9 | 35 | Silicon |
| 24 | 3 | `MCU-BMS` | MCU STM32 (BMS) | 1 | con | ST | 12 | 30 | Silicon |
| 25 | 3 | `CTR-ISO` | Isolated DC/DC converter | 1 | cái | TDK | 28 | 26 | — |
| 26 | 3 | `RELAY-LV` | LV Relay 12V | 4 | cái | Panasonic | 3.5 | 15 | — |

> **Ghi chú:** "Đơn giá" của các dòng Level 1 là standard cost **đã cộng gộp**
> (rolled-up) các linh kiện cấp dưới. Tổng standard cost của cả BOM = đơn giá
> dòng Level 0 = **$6,200 / bộ pin**.

---

## 3. Tóm tắt dữ liệu (các số liệu để trả lời câu hỏi)

- Tổng số dòng BOM: **26 dòng** (STT 1 → 26).
- Số cấp (level): **4 cấp** — Level 0 (1 dòng), Level 1 (6 dòng), Level 2 (12 dòng), Level 3 (7 dòng).
- Tổng số cell trong 1 bộ pin: **96 cell** NMC 21700 (4 module × 24 cell). CATL là nhà cung cấp cell duy nhất.
- Tổng standard cost BOM: **$6,200 / bộ** (Level 0, lắp in-house tại VinFast Plant Hai Phong).
- Số nhà cung cấp khác nhau: **18** (bao gồm in-house VinFast).
- Linh kiện có **đơn giá cao nhất** (leaf): `BMS-PCB` — **$120/pcs** (Continental).
- Linh kiện có **lead time dài nhất**: `CELL-NCM-217` — **60 ngày** (CATL). Đây là **linh kiện critical** cho kế hoạch sản xuất.
- Linh kiện có **lead time ngắn nhất**: `SCR-M6` — **5 ngày** (Bossard).
- Nhóm chi phí theo hệ thống:
  - Module + cell (MG-FR + MG-RR + cell): chiếm phần lớn tổng cost.
  - BMS (gồm `BMS-MAIN`, `BMS-PCB`, `SNS-CUR`, `CTCT-HV`, `IC-MON`, `MCU-BMS`, `CTR-ISO`): ~ **$1,062**.
  - Thermal (`TMS-COOL`, `CP-COOL`, `HOSE-COOL`, `PUMP-CL`, `TANK-EXP`, `COOLANT`): ~ **$1,003**.
- Chỉ có **2 dòng dùng chung nhà cung cấp TE Connectivity** (`CTCT-HV`, `CONN-HV`); Continental cung cấp 3 dòng BMS (`BMS-MAIN`, `BMS-PCB`, `SNS-CUR`).
- Vật liệu phổ biến: nhôm (6061/6063), đồng (Cu ETP, cáp đồng), silicon (IC/MCU).

---

## 4. Sự kiện khóa (facts đặc biệt — để demo ấn tượng)

1. **Lead time cell 60 ngày** vượt xa mọi linh kiện khác → cell là nút thắt chuỗi cung ứng; mua trước, nhập theo JIT cho các dòng còn lại.
2. **Tổng 96 cell** được lắp thành 4 module (2 Front + 2 Rear), mỗi module 24 cell — cấu hình module là "bộ nhân" cơ bản của BOM.
3. **BOM chỉ có 1 nhà cung cấp duy nhất cho cell (CATL)** → rủi ro đơn nguồn (single-source risk).
4. **In-house (VinFast Plant Hai Phong)** gia công top assembly, enclosure, 4 module group — 7/26 dòng do in-house; 19 dòng còn lại từ 17 vendor bên ngoài.
5. **Standard cost $6,200/bộ pin** — đắt nhất theo đơn giá từng dòng là `BMS-MAIN` $540 (bộ), nhưng linh kiện leaf đắt nhất là `BMS-PCB` $120/pcs.

---

## 5. Mẫu câu hỏi demo (GPT có thể sinh ra / trả lời từ context trên)

### Nhóm 1 — Thống kê cơ bản
- Báo cáo BOM này là BOM của sản phẩm gì?
- BOM có bao nhiêu dòng (line item)?
- BOM này có bao nhiêu cấp? Kể tên các cấp đó.
- Có bao nhiêu nhà cung cấp khác nhau trong BOM?
- Tổng chi phí (standard cost) của cả BOM là bao nhiêu?

### Nhóm 2 — Chi tiết linh kiện
- Linh kiện nào có đơn giá cao nhất? Giá bao nhiêu?
- Linh kiện nào có lead time dài nhất? Bao lâu?
- Mỗi module group chứa bao nhiêu cell? Cả bộ pin tổng cộng bao nhiêu cell?
- Cell dùng công nghệ gì, của nhà cung cấp nào?
- `BMS-MAIN` nằm ở level mấy, do ai cung cấp, lead time bao lâu?

### Nhóm 3 — So sánh / phân tích
- So sánh lead time của cell so với linh kiện BMS? Cái nào rủi ro hơn cho sản xuất?
- Dòng nào do VinFast tự gia công (in-house) và dòng nào mua ngoài?
- Chi phí hệ thống BMS là bao nhiêu so với hệ thống thermal?
- Nhà cung cấp nào xuất hiện nhiều nhất trong BOM?

### Nhóm 4 — Dạng hội thoại follow-up (để test multi-turn)
- "BOM này của xe gì?" → "Nó có bao nhiêu cell?" → "Cell của ai cung cấp?" → "Lead time của cell bao lâu?"
- "Linh kiện nào đắt nhất?" → "Còn linh kiện nào lead time lâu nhất?"
