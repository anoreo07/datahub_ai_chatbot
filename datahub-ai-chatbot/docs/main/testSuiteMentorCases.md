# Bộ Câu Hỏi Kiểm Thử (Test Suite Benchmark) Cho Các Kịch Bản Phức Hợp & Đa Domain

Tài liệu này tổng hợp bộ câu hỏi kiểm thử chuẩn (**Benchmark Test Cases**) phục vụ kiểm thử các kịch bản phức hợp theo yêu cầu của Mentor, bao gồm:
1. **Xử lý Nhập nhằng Thuật ngữ Đa Domain (Domain-Scoped Term Disambiguation)**.
2. **Case A: Tìm Báo cáo Capacity & Tài liệu liên quan (Report Location & Document QA)**.
3. **Case B: Giải thích Thuật ngữ & Công thức tính toán của Cột (Term Definition & Calculation Formula)**.
4. **Case C: Dòng chảy dữ liệu của Báo cáo & Nguồn thô (Report Lineage & Raw Data Origin)**.
5. **Case D: Chuỗi Truy Vấn Đa Chặng Tổng Hợp (End-to-End Multi-Hop Chain)**.

---

## nhóm 1: Kiểm Thử Nhập Nhằng Thuật Ngữ Đa Domain (Domain Disambiguation)

> **Mục tiêu**: Kiểm tra khả năng phân định hoặc đưa ra lựa chọn phân vùng Domain khi một thuật ngữ/khái niệm (như *Demand*, *Capacity*, *Inventory*) xuất hiện ở nhiều miền nghiệp vụ khác nhau.

| Mã Test | Câu Hỏi Kiểm Thử | Intent Kỳ Vọng | Kết Quả Mẫu Kỳ Vọng |
| :---: | :--- | :--- | :--- |
| **DOM-01** | *"Giải thích khái niệm Nhu cầu linh kiện (Demand) trong domain CUNG ỨNG (NĐH)?"* | `TERM_DEFINITION` | Trả về định nghĩa Nhu cầu linh kiện chính xác của miền Cung ứng. |
| **DOM-02** | *"Định nghĩa Demand ở domain SẢN XUẤT khác gì với domain KINH DOANH?"* | `COMPARISON` | So sánh sự khác biệt về thuật ngữ Demand giữa 2 domain. |
| **DOM-03** | *"Nhu cầu linh kiện được định nghĩa như thế nào trong hệ thống?"* | `TERM_DEFINITION` | Hệ thống phát hiện thuật ngữ tồn tại ở nhiều Domain và liệt kê/gợi ý chọn Domain cụ thể. |
| **DOM-04** | *"Liệt kê tất cả các thuật ngữ Capacity thuộc miền Cung ứng NĐH"* | `DOMAIN_QUERY` | Lọc các Term thuộc Domain chỉ định. |

---

## nhóm 2: Case A — Tìm Báo Cáo Capacity & Tài Liệu Liên Quan (Report & Doc QA)

> **Mục tiêu**: Người dùng hỏi tìm báo cáo cụ thể -> Hệ thống chỉ ra vị trí báo cáo (Dashboard/Dataset URN) và các tài liệu kỹ thuật (PDF/DOCX/HTML) liên quan.

| Mã Test | Câu Hỏi Kiểm Thử | Intent Kỳ Vọng | Kết Quả Mẫu Kỳ Vọng |
| :---: | :--- | :--- | :--- |
| **REP-01** | *"Tôi cần tìm báo cáo capacity của vendor?"* | `DATASET_LOOKUP` + `DOCUMENT_QA` | Dẫn tới Dashboard/Dataset Capacity Vendor trên DataHub + Trích dẫn tài liệu HDSD liên quan. |
| **REP-02** | *"Báo cáo Capacity của Vendor nằm ở đâu và có tài liệu hướng dẫn nào đính kèm không?"* | `COMPOSITE_QUERY` | Trả về URN/Link DataHub của báo cáo và tóm tắt file tài liệu PDF/HTML liên quan. |
| **REP-03** | *"Tìm các báo cáo quản trị công suất nhà cung cấp thuộc domain Cung ứng"* | `DOMAIN_QUERY` | Liệt kê danh sách các Dashboard/Dataset Vendor Capacity trong Domain. |

---

## nhóm 3: Case B — Công Thức Tính Toán Của Cột & Glossary Term (Formula & Column Logic)

> **Mục tiêu**: Người dùng hỏi công thức tính của một cột -> Hệ thống dẫn tới Glossary Term tương ứng và giải thích công thức/quy tắc tính toán trước.

| Mã Test | Câu Hỏi Kiểm Thử | Intent Kỳ Vọng | Kết Quả Mẫu Kỳ Vọng |
| :---: | :--- | :--- | :--- |
| **FORM-01** | *"Tôi cần biết công thức tính của column coverage date này là như thế nào?"* | `FIELD_PROPERTY` + `TERM_DEFINITION` | Dẫn tới Glossary Term `Coverage Date`, giải thích logic/công thức tính toán trước, sau đó mô tả cột trong bảng. |
| **FORM-02** | *"Cột Inventory_Turnover_Rate trong bảng Fact_Inventory được tính bằng công thức gì?"* | `FIELD_PROPERTY` | Chỉ ra công thức nghiệp vụ (Ví dụ: `CoGS / Avg_Inventory`) và định nghĩa Term liên quan. |
| **FORM-03** | *"Giải thích ý nghĩa và công thức của trường Min_Safety_Stock"* | `FIELD_PROPERTY` | Nêu công thức kho an toàn tối thiểu và thuật ngữ quản lý tồn kho. |

---

## nhóm 4: Case C — Dòng Chảy Dữ Liệu Báo Cáo & Nguồn Dữ Liệu Thô (Report Lineage & Raw Data)

> **Mục tiêu**: Người dùng hỏi nguồn gốc báo cáo -> Hệ thống dẫn tới Lineage đồ thị, chỉ ra báo cáo lấy từ nguồn nào và bảng dữ liệu gốc (Raw Data) là gì.

| Mã Test | Câu Hỏi Kiểm Thử | Intent Kỳ Vọng | Kết Quả Mẫu Kỳ Vọng |
| :---: | :--- | :--- | :--- |
| **LIN-01** | *"Tôi cần biết report này đang lấy dữ liệu từ đâu?"* | `LINEAGE_UPSTREAM` | Trả về danh sách nguồn dữ liệu cấp trên (Upstream), bảng trung gian ETL và nguồn dữ liệu thô (Raw Data). |
| **LIN-02** | *"Báo cáo Capacity Vendor được tổng hợp từ những bảng dữ liệu thô (raw data) nào?"* | `LINEAGE_UPSTREAM` | Trích xuất chuỗi lineage từ Dashboard -> Fact Table -> Raw Staging Tables. |
| **LIN-03** | *"Nếu bảng dữ liệu thô Raw_Vendor_Shipment bị lỗi thì những báo cáo nào bị ảnh hưởng?"* | `IMPACT_ANALYSIS` | Phân tích ảnh hưởng hạ nguồn (Downstream impact) tới các báo cáo/dashboard. |

---

## nhóm 5: Case D — Chuỗi Truy Vấn Đa Chặng Tổng Hợp (End-to-End Multi-Hop Mentor Chain)

> **Mục tiêu**: Kết hợp trọn vẹn yêu cầu của Mentor trong một hoặc chuỗi câu hỏi liền mạch (Báo cáo -> Công thức -> Nguồn thô).

| Mã Test | Câu Hỏi Kiểm Thử | Intent Kỳ Vọng | Kết Quả Mẫu Kỳ Vọng |
| :---: | :--- | :--- | :--- |
| **MHOP-01** | *"Từ báo cáo Capacity Vendor, cho tôi biết công thức tính cột Coverage Date và nguồn dữ liệu thô ban đầu lấy từ đâu?"* | `MULTI_HOP_CHAIN` | 1. Tìm vị trí báo cáo.<br>2. Giải thích công thức cột Coverage Date.<br>3. Truy vết lineage về bảng dữ liệu thô (Raw Data). |
| **MHOP-02** | *"Tìm báo cáo Nhu cầu linh kiện domain Cung ứng, giải thích công thức tính tồn kho và liệt kê các bảng nguồn thô trên BigQuery"* | `MULTI_HOP_CHAIN` | Tổng hợp từ vị trí báo cáo, giải thích thuật ngữ, công thức và truy vết nguồn thô trên BigQuery. |
