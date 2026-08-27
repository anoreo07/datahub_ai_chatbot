# Bảng Tra Cứu Các Intent Của Hệ Thống V-DataAtlas

Tài liệu này tổng hợp toàn bộ **42 Intent** (Ý định truy vấn) được hỗ trợ trong hệ thống V-DataAtlas (`retrieval/intent.py`), phân loại theo nhóm chức năng, mô tả nghiệp vụ và câu hỏi mẫu tương ứng.

---

| STT | Intent Code | Nhóm Chức Năng | Mô Tả Nghiệp Vụ | Ví Dụ Câu Hỏi Mẫu | Legacy Mapping |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `DATASET_LOOKUP` | Tra cứu Metadata | Tra cứu thông tin chi tiết của một bảng dữ liệu / dataset | *"Cho tôi xem thông tin dataset Dim_BaoCaoLayout"* | `FIND_ENTITY` |
| **2** | `FIELD_LOOKUP` | Tra cứu Metadata | Tra cứu danh sách các trường (cột) và kiểu dữ liệu của bảng | *"Bảng Dim_BaoCaoLayout gồm những cột nào?"* | `SCHEMA_LOOKUP` |
| **3** | `FIELD_PROPERTY` | Tra cứu Metadata | Tra cứu thuộc tính chi tiết của một cột (mô tả, kiểu dữ liệu, khóa) | *"Cột Ma_Layout trong bảng Dim_BaoCaoLayout là kiểu dữ liệu gì?"* | `SCHEMA_LOOKUP` |
| **4** | `TERM_DEFINITION` | Tra cứu Metadata | Tra cứu giải thích định nghĩa khái niệm / thuật ngữ Glossary Term | *"Giải thích khái niệm Nhu cầu linh kiện"* | - |
| **5** | `OWNER_LOOKUP` | Tra cứu Metadata | Tra cứu người/nhóm chịu trách nhiệm quản lý (Data Owner) | *"Ai là owner của bảng Fact_Sales?"* | - |
| **6** | `DOMAIN_LOOKUP` | Tra cứu Metadata | Tra cứu Domain (miền dữ liệu) quản lý của bảng/entity | *"Dataset Fact_Inventory thuộc domain nào?"* | `ENTITY_DOMAIN` |
| **7** | `ENTITY_EXISTS` | Tra cứu Metadata | Kiểm tra sự tồn tại của bảng / entity trong hệ thống | *"Bảng Temp_Customer_Log có tồn tại trên DataHub không?"* | - |
| **8** | `DATAHUB_URL` | Tra cứu Metadata | Lấy đường dẫn (URL) truy cập trực tiếp entity trên DataHub | *"Cho tôi xin link DataHub của dataset Dim_Product"* | - |
| **9** | `LINEAGE_UPSTREAM` | Dòng chảy dữ liệu | Tra cứu nguồn gốc dữ liệu đầu vào (Upstream lineage) | *"Dữ liệu bảng Dim_Customer được tổng hợp từ nguồn nào?"* | `LINEAGE` |
| **10** | `LINEAGE_DOWNSTREAM` | Dòng chảy dữ liệu | Tra cứu luồng dữ liệu đầu ra (Downstream lineage) | *"Bảng Dim_BaoCaoLayout cung cấp dữ liệu cho những báo cáo/bảng nào?"* | `LINEAGE` |
| **11** | `IMPACT_ANALYSIS` | Dòng chảy dữ liệu | Phân tích ảnh hưởng khi thay đổi hoặc có sự cố ở bảng dữ liệu | *"Nếu sửa cột Customer_ID ở bảng gốc thì ảnh hưởng đến những đâu?"* | `IMPACT` |
| **12** | `RECURSIVE_IMPACT` | Dòng chảy dữ liệu | Phân tích ảnh hưởng dây chuyền đệ quy đa tầng | *"Phân tích ảnh hưởng đa tầng khi dừng bảng Raw_Transactions"* | `IMPACT` |
| **13** | `GRAPH_QUERY` | Dòng chảy dữ liệu | Truy vấn quan hệ dạng đồ thị (Graph) giữa các entity | *"Hiển thị đồ thị quan hệ giữa bảng Customer và Order"* | `GENERAL` |
| **14** | `DOMAIN_QUERY` | Liệt kê & Thống kê | Liệt kê các dataset thuộc một Domain cụ thể | *"dataset nào thuộc domain CUNG ỨNG (NĐH)?"* | - |
| **15** | `TAG_QUERY` | Liệt kê & Thống kê | Lọc và liệt kê danh sách entity theo thẻ Tag | *"Danh sách các bảng được gắn tag PII hoặc Confidential"* | - |
| **16** | `PLATFORM_QUERY` | Liệt kê & Thống kê | Lọc entity theo Nền tảng / Hệ quản trị dữ liệu | *"Liệt kê các bảng dữ liệu nằm trên BigQuery"* | - |
| **17** | `ENTITIES_BY_OWNER` | Liệt kê & Thống kê | Liệt kê danh sách bảng thuộc sở hữu của một cá nhân/nhóm | *"Liệt kê các bảng do linhhv12 làm owner"* | - |
| **18** | `CERTIFIED_LIST` | Liệt kê & Thống kê | Liệt kê các bảng dữ liệu đã đạt chuẩn chứng nhận (Certified) | *"Cho tôi xem danh sách các dataset đã được Certified"* | - |
| **19** | `COUNT_ENTITIES` | Liệt kê & Thống kê | Thống kê, đếm số lượng entity theo tiêu chí | *"Hệ thống có tổng cộng bao nhiêu dataset trong domain Sản xuất?"* | - |
| **20** | `MISSING_DESCRIPTION` | Liệt kê & Thống kê | Liệt kê các dataset/entity chưa có mô tả (Metadata Hygiene) | *"Tìm các bảng chưa có description trong domain Cung ứng"* | - |
| **21** | `MISSING_OWNER` | Liệt kê & Thống kê | Liệt kê các dataset/entity chưa gán người sở hữu | *"Những dataset nào hiện tại chưa có Owner?"* | - |
| **22** | `MISSING_DOMAIN` | Liệt kê & Thống kê | Liệt kê các dataset/entity chưa gán vào Domain | *"Liệt kê các bảng chưa được phân loại vào Domain nào"* | - |
| **23** | `METADATA_LISTING` | Liệt kê & Thống kê | Liệt kê tổng hợp metadata theo các bộ lọc kết hợp | *"Liệt kê bảng có chứa từ khóa 'Doanh thu' và thuộc BigQuery"* | - |
| **24** | `LISTING` | Liệt kê & Thống kê | Ý định liệt kê tổng quát các đối tượng dữ liệu | *"Liệt kê tất cả các Glossary Term trong hệ thống"* | - |
| **25** | `TERM_TO_DATASETS` | RAG Phức hợp | Tìm các dataset liên quan/chứa thông tin của một Thuật ngữ | *"Khái niệm Nhu cầu linh kiện nằm trong những dataset nào?"* | - |
| **26** | `MULTI_HOP_CHAIN` | RAG Phức hợp | Xử lý chuỗi câu hỏi đa chặng từ báo cáo -> định nghĩa -> nguồn | *"Từ report Capacity -> định nghĩa -> các cột -> nguồn thô"* | `FIND_ENTITY` |
| **27** | `COMPARISON` | RAG Phức hợp | So sánh cấu trúc/schema giữa 2 hoặc nhiều bảng dữ liệu | *"So sánh cấu trúc giữa bảng Fact_Sales_V1 và Fact_Sales_V2"* | `GENERAL` |
| **28** | `COMPOSITE_QUERY` | RAG Phức hợp | Truy vấn tổng hợp chứa nhiều yêu cầu ghép nối trong một câu | *"Cho biết mô tả, các cột chính và owner của bảng Dim_User"* | `GENERAL` |
| **29** | `MULTI_ENTITY_QUERY` | RAG Phức hợp | Truy vấn thông tin đồng thời cho nhiều entity | *"Xem thông tin của cả 2 bảng Dim_Product và Dim_Store"* | `GENERAL` |
| **30** | `RELATED_DATASETS` | RAG Phức hợp | Tìm kiếm các dataset liên quan hoặc tương tự | *"Tìm các bảng dữ liệu có liên quan đến bảng Dim_BaoCaoLayout"* | `FIND_ENTITY` |
| **31** | `SEMANTIC_SEARCH` | RAG Phức hợp | Tìm kiếm ngữ nghĩa mở rộng trên toàn kho Metadata | *"Tìm kiếm các dữ liệu phục vụ báo cáo quản trị chi phí"* | `GENERAL` |
| **32** | `DOCUMENT_QA` | Công cụ Chuyên dụng | Hỏi đáp RAG dựa trên tài liệu kỹ thuật (PDF, DOCX, HTML) | *"Tài liệu Hướng dẫn vận hành quy định quy trình sync như thế nào?"* | - |
| **33** | `SQL_GENERATION` | Công cụ Chuyên dụng | Tự động sinh câu lệnh SQL từ yêu cầu câu hỏi | *"Viết SQL lấy top 10 khách hàng có doanh thu cao nhất"* | - |
| **34** | `QUALITY_CHECK` | Công cụ Chuyên dụng | Tra cứu báo cáo kiểm tra chất lượng dữ liệu (Data Quality) | *"Cho tôi xem kết quả kiểm tra chất lượng của bảng Fact_Orders"* | - |
| **35** | `METADATA_REPORT` | Công cụ Chuyên dụng | Trích xuất báo cáo tổng hợp tình trạng Metadata hệ thống | *"Xuất báo cáo tổng quan tình trạng Metadata theo Domain"* | - |
| **36** | `GREETING` | Giao tiếp hệ thống | Xử lý các câu chào hỏi ban đầu | *"Xin chào", "Hello bot"* | - |
| **37** | `CHITCHAT` | Giao tiếp hệ thống | Xử lý giao tiếp thông thường, hỏi thăm, cảm ơn | *"Bạn khỏe không?", "Cảm ơn bạn nhé"* | - |
| **38** | `GENERAL` | Giao tiếp hệ thống | Phân luồng cho các câu hỏi chung về Metadata cần RAG | *"DataHub là gì và dùng để làm gì?"* | - |
| **39** | `FIND_ENTITY` | Legacy Routing | Intent tra cứu entity chung (Legacy) | *"Tìm entity Dim_Customer"* | - |
| **40** | `SCHEMA_LOOKUP` | Legacy Routing | Intent tra cứu cấu trúc schema (Legacy) | *"Xem schema bảng Fact_Sales"* | - |
| **41** | `LINEAGE` | Legacy Routing | Intent tra cứu dòng chảy dữ liệu (Legacy) | *"Xem lineage bảng Fact_Sales"* | - |
| **42** | `IMPACT` | Legacy Routing | Intent phân tích tác động ảnh hưởng (Legacy) | *"Phân tích ảnh hưởng bảng Dim_Product"* | - |
