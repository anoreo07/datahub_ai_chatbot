# BÁO CÁO KỸ THUẬT SẢN PHẨM: HỆ THỐNG V-DATAATLAS (DATAHUB AI CHATBOT)
**Technical Architecture & Product Validation Report**

---

| Thông Tin Dự Án | Chi Tiết |
|---|---|
| **Tên Sản Phẩm** | V-DataAtlas (DataHub AI Chatbot & Semantic Search Platform) |
| **Phiên Bản Hệ Thống** | v1.2.0-prod-rc |
| **Đối Tượng Báo Cáo** | Mentor / Hội Đồng Thẩm Định Kỹ Thuật / Technical Stakeholders |
| **Ngày Hoàn Thành** | 26/08/2026 |
| **Phạm Vi Đánh Giá** | Kiến trúc hệ thống, Query Pipeline, 6 Core Actions, RAG/RAGAS, RBAC, Data thực tế và Failure Analysis |
| **Cơ Sở Dữ Liệu Thực Tế** | PostgreSQL Catalog (9,067 entities, 21,196 chunks), OpenSearch Vector Store, DataHub GraphQL, 459 Automated Tests |

---

## MỤC LỤC TỔNG QUAN

- [1. TỔNG QUAN DỰ ÁN & MỤC TIÊU SẢN PHẨM](#1-tổng-quan-dự-án--mục-tiêu-sản-phẩm)
  - [1.1. Tóm tắt điều hành (Executive Summary)](#11-tóm-tắt-điều-hành-executive-summary)
  - [1.2. Bối cảnh & Thách thức quản trị dữ liệu doanh nghiệp](#12-bối-cảnh--thách-thức-quản-trị-dữ-liệu-doanh-nghiệp)
  - [1.3. Mục tiêu kỹ thuật & Phạm vi triển khai](#13-mục-tiêu-kỹ-thuật--phạm-vi-triển-khai)
  - [1.4. Quy mô dữ liệu thực tế được quản trị](#14-quy-mô-dữ-liệu-thực-tế-được-quản-trị)
- [2. KIẾN TRÚC TỔNG THỂ HỆ THỐNG (SYSTEM ARCHITECTURE)](#2-kiến-trúc-tổng-thể-hệ-thống-system-architecture)
  - [2.1. Sơ đồ Kiến trúc Cấp cao (Diagram 1)](#21-sơ-đồ-kiến-trúc-cấp-cao-diagram-1)
  - [2.2. Phân rã các tầng kiến trúc kỹ thuật](#22-phân-rã-các-tầng-kiến-trúc-kỹ-thuật)
  - [2.3. Bảng thành phần công nghệ (Technology Stack)](#23-bảng-thành-phần-công-nghệ-technology-stack)
- [3. QUY TRÌNH XỬ LÝ TRUY VẤN (QUERY PROCESSING PIPELINE)](#3-quy-trình-xử-lý-truy-vấn-query-processing-pipeline)
  - [3.1. Sơ đồ tuần tự xử lý truy vấn (Diagram 2)](#31-sơ-đồ-tuần-tự-xử-lý-truy-vấn-diagram-2)
  - [3.2. Luồng xử lý truy vấn tổng quan](#32-luồng-xử-lý-truy-vấn-tổng-quan)
- [4. QUERY UNDERSTANDING & ENTITY RESOLUTION](#4-query-understanding--entity-resolution)
  - [4.1. Cấu trúc mô hình QuerySpec](#41-cấu-trúc-mô-hình-queryspec)
  - [4.2. Sơ đồ Entity Resolution & QuerySpec Construction (Diagram 3)](#42-sơ-đồ-entity-resolution--queryspec-construction-diagram-3)
  - [4.3. Thuật toán phân giải URN đa tầng (Multi-Tier Resolver)](#43-thuật-toán-phân-giải-urn-đa-tầng-multi-tier-resolver)
  - [4.4. Nhận diện 10 phân lớp Catalog Entities](#44-nhận-diện-10-phân-lớp-catalog-entities)
  - [4.5. Xử lý câu hỏi phức hợp & Query Planner DAG (Diagram 4)](#45-xử-lý-câu-hỏi-phức-hợp--query-planner-dag-diagram-4)
  - [4.6. Chế độ suy luận Thinking Mode (Diagram 5)](#46-chế-độ-suy-luận-thinking-mode-diagram-5)
- [5. BẢNG NĂNG LỰC & CHI TIẾT 6 ACTIONS CỐT LÕI](#5-bảng-năng-lực--chi-tiết-6-actions-cốt-lõi)
  - [5.1. Ma trận năng lực hệ thống (Capability Matrix)](#51-ma-trận-năng-lực-hệ-thống-capability-matrix)
  - [5.2. Chi tiết 6 Actions Cốt Lõi](#52-chi-tiết-6-actions-cốt-lõi)
- [6. KIẾN TRÚC TRI THỨC, RAG & TÍCH HỢP DATAHUB](#6-kiến-trúc-tri-thức-rag--tích-hợp-datahub)
  - [6.1. Sơ đồ tích hợp DataHub Enterprise (Diagram 7)](#61-sơ-đồ-tích-hợp-datahub-enterprise-diagram-7)
  - [6.2. Sơ đồ Hybrid RAG & Vector Store (Diagram 8)](#62-sơ-đồ-hybrid-rag--vector-store-diagram-8)
  - [6.3. Phân định Structured Metadata Retrieval vs Semantic Vector RAG](#63-phân-định-structured-metadata-retrieval-vs-semantic-vector-rag)
  - [6.4. Tổng quan xử lý đa phương thức (Vision & Document Ingestion)](#64-tổng-quan-xử-lý-đa-phương-thức-vision--document-ingestion)
- [7. DATA LINEAGE, IMPACT ANALYSIS & DATA QUALITY ENGINE](#7-data-lineage-impact-analysis--data-quality-engine)
  - [7.1. Sơ đồ duyệt đồ thị Lineage & Impact (Diagram 9)](#71-sơ-đồ-duyệt-đồ-thị-lineage--impact-diagram-9)
  - [7.2. Quy tắc phân biệt Visualization Mode vs Text Mode](#72-quy-tắc-phân-biệt-visualization-mode-vs-text-mode)
  - [7.3. Thuật toán duyệt BFS đa cấp](#73-thuật-toán-duyệt-bfs-đa-cấp)
  - [7.4. Bộ chỉ số & 6 trạng thái Data Quality](#74-bộ-chỉ-số--6-trạng-thái-data-quality)
- [8. BUSINESS GLOSSARY & QUẢN TRỊ SEMANTICS ĐA MIỀN](#8-business-glossary--quản-trị-semantics-đa-miền)
  - [8.1. Quản lý danh mục thuật ngữ nghiệp vụ](#81-quản-lý-danh-mục-thuật-ngữ-nghiệp-vụ)
  - [8.2. Phân định thuật ngữ đồng âm khác miền](#82-phân-định-thuật-ngữ-đồng-âm-khác-miền)
  - [8.3. Truy vết từ bài toán nghiệp vụ tới nguồn dữ liệu thô](#83-truy-vết-từ-bài-toán-nghiệp-vụ-tới-nguồn-dữ-liệu-thô)
- [9. CONTEXT STATE & QUẢN TRỊ HỘI THOẠI ĐA LƯỢT](#9-context-state--quản-trị-hội-thoại-đa-lượt)
  - [9.1. Quản lý Active Entity và Session State (Diagram 6)](#91-quản-lý-active-entity-và-session-state-diagram-6)
  - [9.2. Phân giải đại từ và câu hỏi nối tiếp](#92-phân-giải-đại-từ-và-câu-hỏi-nối-tiếp)
  - [9.3. Thực tế phiên hội thoại 4 lượt](#93-thực-tế-phiên-hội-thoại-4-lượt)
- [10. BẢO MẬT, GUARDRAILS & PHÂN QUYỀN RBAC/ACL](#10-bảo-mật-guardrails--phân-quyền-rbacacl)
  - [10.1. Sơ đồ kiến trúc phân quyền RBAC & ACL (Diagram 13)](#101-sơ-đồ-kiến-trúc-phân-quyền-rbac--acl-diagram-13)
  - [10.2. Mô hình phân quyền theo miền và Entity ACLs](#102-mô-hình-phân-quyền-theo-miền-và-entity-acls)
  - [10.3. Cơ chế phòng thủ Guardrails và kiểm soát dữ liệu nhạy cảm](#103-cơ-chế-phòng-thủ-guardrails-và-kiểm-soát-dữ-liệu-nhạy-cảm)
- [11. ĐÁNH GIÁ CHẤT LƯỢNG RAGAS & HUMAN REVIEW FEEDBACK LOOP](#11-đánh-giá-chất-lượng-ragas--human-review-feedback-loop)
  - [11.1. Sơ đồ pipeline đánh giá RAGAS tự động (Diagram 14)](#111-sơ-đồ-pipeline-đánh-giá-ragas-tự-động-diagram-14)
  - [11.2. Điểm số RAGAS ban đầu và phân tích](#112-điểm-số-ragas-ban-đầu-và-phân-tích)
  - [11.3. Sơ đồ vòng lặp Human Review & Regression Testing (Diagram 15)](#113-sơ-đồ-vòng-lặp-human-review--regression-testing-diagram-15)
  - [11.4. Phân tích kết quả Human Review và Regression Candidates](#114-phân-tích-kết-quả-human-review-và-regression-candidates)
- [12. KẾT QUẢ KIỂM THỬ THỰC TẾ & BÀI HỌC KIẾN TRÚC](#12-kết-quả-kiểm-thử-thực-tế--bài-học-kiến-trúc)
  - [12.1. Tổng hợp kết quả kiểm thử tự động](#121-tổng-hợp-kết-quả-kiểm-thử-tự-động)
  - [12.2. Phân tích 3 bài học kiến trúc tiêu biểu](#122-phân-tích-3-bài-học-kiến-trúc-tiêu-biểu)
  - [12.3. Ma trận chuyển biến hệ thống (Before / After Matrix)](#123-ma-trận-chuyển-biến-hệ-thống-before--after-matrix)
- [13. KIẾN TRÚC FRONTEND UX & TRẢI NGHIỆM NGƯỜI DÙNG](#13-kiến-trúc-frontend-ux--trải-nghiệm-người-dùng)
  - [13.1. Các thành phần giao diện chính](#131-các-thành-phần-giao-diện-chính)
  - [13.2. Lưu trữ và tái hiện trạng thái (State Hydration)](#132-lưu-trữ-và-tái-hiện-trạng-thái-state-hydration)
- [14. HIỆU NĂNG, HẠN CHẾ & LỘ TRÌNH PHÁT TRIỂN](#14-hiệu-năng-hạn-chế--lộ-trình-phát-triển)
  - [14.1. Báo cáo độ trễ thực tế đo lường](#141-báo-cáo-độ-trễ-thực-tế-đo-lường)
  - [14.2. Các hạn chế kỹ thuật hiện tại (Known Limitations)](#142-các-hạn-chế-kỹ-thuật-hiện-tại-known-limitations)
  - [14.3. Các bước phát triển tiếp theo (Future Next Steps)](#143-các-bước-phát-triển-tiếp-theo-future-next-steps)
- [15. KẾT LUẬN & BẢNG TRUY VẾT NGUỒN GỐC](#15-kết-luận--bảng-truy-vết-nguồn-gốc)
  - [15.1. Kết luận](#151-kết-luận)
  - [15.2. Bảng truy vết nguồn gốc kỹ thuật](#152-bảng-truy-vết-nguồn-gốc-kỹ-thuật)
- [PHỤ LỤC A: TECHNICAL POSTMORTEM LOG (LỖI ĐÃ XỬ LÝ)](#phụ-lục-a-technical-postmortem-log-lỗi-đã-xử-lý)
- [PHỤ LỤC B: DANH MỤC API HỆ THỐNG](#phụ-lục-b-danh-mục-api-hệ-thống)
- [PHỤ LỤC C: MÔ HÌNH DỮ LIỆU CƠ SỞ DỮ LIỆU (DATABASE ERD)](#phụ-lục-c-mô-hình-dữ-liệu-cơ-sở-dữ-liệu-database-erd)

---

## <a id="1-tổng-quan-dự-án--mục-tiêu-sản-phẩm"></a>1. TỔNG QUAN DỰ ÁN & MỤC TIÊU SẢN PHẨM

### <a id="11-tóm-tắt-điều-hành-executive-summary"></a>1.1. Tóm tắt điều hành (Executive Summary)

**V-DataAtlas** là hệ thống trợ lý AI phục vụ tra cứu và quản trị siêu dữ liệu doanh nghiệp (Metadata Assistant), được phát triển để tích hợp với nền tảng **DataHub**. Hệ thống kết hợp các kỹ thuật xử lý ngôn ngữ tự nhiên (NLP), đồ thị siêu dữ liệu nội bộ (Metadata Graph), tìm kiếm lai (Hybrid Search: BM25 + Dense Vector OpenSearch) và mô hình ngôn ngữ lớn (LLM) nhằm hỗ trợ người dùng khám phá danh mục dữ liệu, phân tích dòng chảy (Lineage), đánh giá tác động thay đổi (Impact Analysis), kiểm tra chất lượng siêu dữ liệu và hỗ trợ sinh câu lệnh SQL.

Kiến trúc hệ thống được phân định rõ ràng giữa hai cơ chế xử lý:
1. **Truy xuất Siêu dữ liệu Cấu trúc (Structured Metadata Retrieval)**: Đọc trực tiếp schema, danh sách cột, kiểu dữ liệu, quan hệ bảng từ cơ sở dữ liệu PostgreSQL đã đồng bộ từ DataHub Catalog. Nhánh xử lý này có tính xác định cao (deterministic) và không phụ thuộc vào suy đoán của LLM.
2. **Tổng hợp Ngữ nghĩa & RAG (Semantic Synthesis & Retrieval)**: Sử dụng OpenSearch và LLM để tìm kiếm tài liệu, giải thích ngữ nghĩa và định dạng câu trả lời Markdown.

| Hạng Mục Quy Mô | Giá Trị Thực Tế |
|---|---|
| **Tổng số thực thể catalog trong DB** | **9,067 entities** (8,542 Datasets, 327 Dashboards, 177 Glossary Terms, 21 Glossary Nodes) |
| **Khối lượng vector chunks** | **21,196 chunks** được đánh chỉ mục trong OpenSearch |
| **Nền tảng dữ liệu kết nối** | **33 nền tảng** (Redshift, PowerBI, Glue, SAP, MES, DMS...) |
| **Bộ kiểm thử tự động** | **459 Unit & Thinking Tests** (Pass rate: 100%) |
| **Kiểm soát phân quyền** | **884 Entity ACLs, 5 RBAC Domain Roles** |
| **Lịch sử tương tác ghi nhận** | **1,037 Interaction Logs** (kèm vết RAGAS & Human Review) |

---

### <a id="12-bối-cảnh--thách-thức-quản-trị-dữ-liệu-doanh-nghiệp"></a>1.2. Bối cảnh & Thách thức quản trị dữ liệu doanh nghiệp

Tại các doanh nghiệp có hạ tầng dữ liệu lớn, danh mục siêu dữ liệu thường trải rộng trên nhiều hệ thống phân tán (Data Warehouse, Data Lake, hệ thống BI, ERP, cơ sở dữ liệu giao dịch). Thực tế vận hành đặt ra một số thách thức kỹ thuật:
- **Khó khăn trong định vị dữ liệu**: Người dùng kinh doanh khó nhớ chính xác tên kỹ thuật hoặc đường dẫn URN của bảng (ví dụ: `dms.external.account_use_vehicle` hay `stg.sourcing_tracker`).
- **Thiếu tầm nhìn về dòng chảy dữ liệu (Lineage)**: Khó xác định nhanh các báo cáo BI hạ nguồn chịu ảnh hưởng khi schema bảng nguồn thay đổi.
- **Nhập nhằng thuật ngữ giữa các phòng ban**: Thuật ngữ như *"Coverage Date"* hoặc *"Demand"* có công thức và định nghĩa khác nhau giữa khối **Logistics**, **Sản Xuất** và **Tài Chính**.
- **Rủi ro suy diễn sai khi dùng LLM thuần túy**: Khi không được neo ngữ cảnh vào schema catalog thật, LLM có thể tự tạo ra các tên cột không tồn tại khi sinh SQL hoặc giải thích cấu trúc bảng.

---

### <a id="13-mục-tiêu-kỹ-thuật--phạm-vi-triển-khai"></a>1.3. Mục tiêu kỹ thuật & Phạm vi triển khai

V-DataAtlas tập trung giải quyết các mục tiêu cụ thể sau:
1. **Neo dữ liệu cấu trúc vào Catalog thực**: Toàn bộ thông tin về schema, tên cột, kiểu dữ liệu, chủ sở hữu và quan hệ lineage được truy xuất từ dữ liệu thật đã lưu trữ trong PostgreSQL và DataHub.
2. **Khử nhập nhằng theo Domain**: Sử dụng vai trò người dùng (User Role) và ngữ cảnh miền dữ liệu để ưu tiên thuật ngữ và bảng tương ứng.
3. **Phân định rõ ràng chế độ hiển thị Lineage**: Chỉ kích hoạt component đồ thị trực quan (React Flow) khi người dùng yêu cầu rõ ràng; mặc định phản hồi dưới dạng văn bản.
4. **Kiểm soát truy cập theo Domain (RBAC/ACL)**: Áp dụng bộ lọc ở mức cơ sở dữ liệu và OpenSearch để ngăn người dùng xem siêu dữ liệu thuộc miền chưa được cấp phép.
5. **Theo dõi chất lượng qua RAGAS & Human Review**: Ghi nhận log tương tác, tính điểm định lượng và cho phép chuyên gia gắn nhãn các ca lỗi để chuyển vào bộ kiểm thử hồi quy.

---

### <a id="14-quy-mô-dữ-liệu-thực-tế-được-quản-trị"></a>1.4. Quy mô dữ liệu thực tế được quản trị

Các số liệu dưới đây được trích xuất trực tiếp từ cơ sở dữ liệu PostgreSQL của hệ thống:

| Phân Loại Thực Thể | Số Lượng Thực Tế | Tỷ Trọng (%) | Ghi Chú Kỹ Thuật |
|---|---|---|---|
| **Datasets (Bảng / View / File)** | **8,542** | 94.21% | Lưu cấu trúc schema, kiểu dữ liệu, danh sách cột, quan hệ lineage |
| **Dashboards (Báo Cáo / BI)** | **327** | 3.61% | Báo cáo PowerBI, DMS, SAP Layouts, người phụ trách và link DataHub |
| **Glossary Terms (Thuật Ngữ)** | **177** | 1.95% | Định nghĩa nghiệp vụ, công thức tính và liên kết domain |
| **Glossary Nodes (Nhóm Thuật Ngữ)** | **21** | 0.23% | Nhóm phân cấp danh mục thuật ngữ |
| **TỔNG CỘNG THỰC THỂ CATALOG** | **9,067** | **100%** | Lưu tại bảng `entities` |
| **Vector Chunks (OpenSearch)** | **21,196** | — | Đánh chỉ mục Dense Vector + BM25 tại bảng `entity_chunks` |
| **Entity ACLs Được Áp Dụng** | **884** | — | Phân quyền truy cập chi tiết tại bảng `entity_acls` |
| **RBAC Roles Phân Quyền Miền** | **5 Roles** | — | Logistics, Sản Xuất, Tài Chính, Sales, VGreen tại bảng `rbac_roles` |
| **Lịch Sử Tương Tác Được Ghi Log** | **1,037 Logs** | — | Lưu câu hỏi, intent, tool sử dụng, điểm RAGAS tại `interaction_logs` |

Phân bố thực thể theo nền tảng dữ liệu chính:
- **PowerBI**: 3,723 thực thể (41.06%)
- **Redshift**: 3,089 thực thể (34.07%)
- **AWS Glue**: 1,336 thực thể (14.73%)
- **SAP**: 430 thực thể (4.74%)
- **MES (Sản xuất)**: 141 thực thể (1.55%)
- **Excel / DMS / S3**: 64 thực thể (0.71%)
- **Các nền tảng khác (27 platforms)**: 284 thực thể (3.14%)

---

## <a id="2-kiến-trúc-tổng-thể-hệ-thống-system-architecture"></a>2. KIẾN TRÚC TỔNG THỂ HỆ THỐNG (SYSTEM ARCHITECTURE)

### <a id="21-sơ-đồ-kiến-trúc-cấp-cao-diagram-1"></a>2.1. Sơ đồ Kiến trúc Cấp cao (Diagram 1)

Kiến trúc V-DataAtlas được tổ chức thành 4 khối chức năng chính:

```mermaid
flowchart LR
    subgraph Frontend["1. Frontend Layer (Next.js 16.3)"]
        L["Chat UI & SSE Stream"]
        A["Admin / Storage / Search / Glossary"]
    end

    subgraph Backend["2. Application & API Layer (FastAPI)"]
        API["REST Endpoints & SSE Handler"]
        CS["ChatService (Orchestrator)"]
        subgraph AI["AI & Query Intelligence"]
            INT["IntentResolver + Classifier"]
            TH["Thinking Mode (Deterministic Planner)"]
            QP["Query Planner (DAG Execution)"]
            TR["ToolRegistry (13 Tools)"]
            GEN["AnswerGenerator & LLM Engine"]
            VIS["VisionService (Image Analysis)"]
        end
    end

    subgraph Security["3. Security & Governance"]
        AUTH["JWT HS256 Authentication"]
        RBAC_SVC["RBAC Domain Engine (5 Roles)"]
        ACL_SVC["Entity ACL Filter (884 Rules)"]
    end

    subgraph Data["4. Data & Persistence Layer"]
        PG["PostgreSQL 16 (Catalog: 9,067 Entities)"]
        OS["OpenSearch 2.15 (21,196 Chunks)"]
        RD["Redis 7 (Rate Limit, Cache, Queue)"]
        DH["DataHub GMS (GraphQL API)"]
        FW["Fireworks API (LLM & Vision)"]
        OLL["Ollama (Embedding nomic-embed-text)"]
    end

    L -->|"/api rewrites"| API
    A -->|"fetch / apiFetch"| API
    API --> CS
    CS --> AUTH
    AUTH --> RBAC_SVC
    RBAC_SVC --> ACL_SVC
    CS --> INT
    CS --> TH
    CS --> QP
    CS --> VIS
    QP --> TR
    TR --> PG
    TR --> OS
    CS --> GEN
    GEN --> FW
    VIS --> FW
    CS -->|"sync / live lineage"| DH
    DH --> PG
    OLL --> OS
```

---

### <a id="22-phân-rã-các-tầng-kiến-trúc-kỹ-thuật"></a>2.2. Phân rã các tầng kiến trúc kỹ thuật

1. **Presentation Layer (`frontend/`)**: Xây dựng bằng Next.js 16.3 (App Router), React 19, Tailwind CSS. Hỗ trợ Server-Sent Events (SSE) streaming, hiển thị đồ thị tương tác bằng React Flow, ngăn bằng chứng (Evidence Drawer) và các chip gợi ý (Suggestion Chips).
2. **API & Application Layer (`app/api/`, `app/services/`)**: FastAPI xử lý các endpoint: `/api/v1/chat`, `/api/v1/search`, `/api/v1/actions`, `/api/v1/admin`, `/api/v1/reviews`, `/api/v1/sync`. Middleware đảm nhiệm xử lý lỗi, logging metrics và giới hạn tần suất (Rate Limit).
3. **Query Intelligence Layer (`retrieval/classifier.py`, `retrieval/query_parser.py`)**: Chuẩn hóa câu hỏi, phân loại intent theo 2 cấp (Regex Fast-path kết hợp LLM Semantic Classifier), trích xuất thực thể và đóng gói thành QuerySpec.
4. **Entity Resolution Layer (`retrieval/entity_resolver.py`)**: Phân giải tên bảng và URN qua các bước: Exact Match → Levenshtein Fuzzy → OpenSearch Vector → URN Lookup.
5. **Action Execution Engines (`app/services/chat_service.py`, `app/services/action_service.py`)**: Điều phối luồng xử lý riêng cho 6 Actions chính và luồng so sánh đa thực thể.
6. **Persistence & Vector Layer (`database/`, `indexing/`)**: PostgreSQL lưu trữ toàn bộ thực thể catalog, ACLs, lịch sử tương tác và đánh giá. OpenSearch lưu trữ vector chunks phục vụ tìm kiếm kết hợp (BM25 + KNN).

---

### <a id="23-bảng-thành-phần-công-nghệ-technology-stack"></a>2.3. Bảng thành phần công nghệ (Technology Stack)

| Thành Phần Kỹ Thuật | Công Nghệ / Thư Viện | Phiên Bản | Vai Trò Kỹ Thuật |
|---|---|---|---|
| **Backend Framework** | Python / FastAPI | 0.115+ | Xử lý API bất đồng bộ (Asynchronous ASGI) |
| **Database ORM** | SQLAlchemy / Asyncpg | 2.0+ | Truy vấn PostgreSQL bất đồng bộ |
| **Relational Database** | PostgreSQL | 16-alpine | Lưu trữ catalog 9,067 thực thể, ACLs, Interaction Logs |
| **Vector Search Engine** | OpenSearch | 2.15.0 | Lưu trữ 21,196 chunks, tìm kiếm lai (BM25 + KNN) |
| **Cache & Queue** | Redis | 7-alpine | Quản lý phiên hội thoại, rate limiting, task queue |
| **Mô hình LLM chính** | Fireworks AI API | Qwen2.5 / Llama 3.3 | Tổng hợp câu trả lời, phân loại intent ngữ nghĩa |
| **Mô hình Vision** | Fireworks AI API | Qwen3.7-Plus | Phân tích ảnh chụp bảng, ERD, dashboard |
| **Mô hình Embedding** | Ollama / nomic-embed-text | 768 chiều | Vector hóa các chunk siêu dữ liệu và tài liệu |
| **Frontend Framework** | Next.js / TypeScript | 16.3.0 | Giao diện người dùng thời gian thực, Server-Side Rendering |
| **Đồ thị Lineage** | React Flow (@xyflow/react) | 12.0+ | Render đồ thị quan hệ bảng và lineage tương tác |
| **Framework Đánh Giá** | RAGAS | 0.1.20+ | Đánh giá tự động Faithfulness, Relevancy |

---

## <a id="3-quy-trình-xử-lý-truy-vấn-query-processing-pipeline"></a>3. QUY TRÌNH XỬ LÝ TRUY VẤN (QUERY PROCESSING PIPELINE)

### <a id="31-sơ-đồ-tuần-tự-xử-lý-truy-vấn-diagram-2"></a>3.1. Sơ đồ tuần tự xử lý truy vấn (Diagram 2)

```mermaid
sequenceDiagram
    autonumber
    actor User as Người Dùng
    participant UI as Chat UI (Next.js)
    participant API as FastAPI Router (/api/v1/chat/stream)
    participant CS as ChatService (Orchestrator)
    participant IR as IntentResolver & Classifier
    participant Gate as Guardrails / RBAC Scope
    participant TR as Planner / ToolRegistry
    participant DB as Postgres & OpenSearch
    participant LLM as AnswerGenerator (Fireworks)
    participant Eval as Interaction Logger & RAGAS

    User->>UI: Nhập câu hỏi (+ Action / Ảnh nếu có)
    UI->>API: POST /api/v1/chat/stream (SSE)
    API->>CS: answer(question, user_context, ...)
    CS->>IR: resolve(question, action, history)
    IR-->>CS: intent, target_urns, query_spec
    CS->>Gate: Kiểm tra Guardrail scope, Injection, Domain RBAC
    alt Bị từ chối quyền (Domain Denied)
        Gate-->>UI: Phản hồi thông báo từ chối truy cập (HTTP 403)
    else Hợp lệ
        CS->>TR: Thực thi Tool / Plan tương ứng
        TR->>DB: Truy vấn Metadata cấu trúc & Vector chunks
        DB-->>TR: Dữ liệu schema, lineage, findings
        TR-->>CS: Context kết quả
        CS->>CS: Lọc ACL, Rerank, đóng gói Context XML
        CS->>LLM: generate(query, context, history)
        LLM-->>CS: Answer JSON / Stream tokens + Citations
        CS->>CS: Validate citations & loại bỏ URN không có căn cứ
        CS-->>API: Gửi SSE events: status -> token -> done
        API-->>UI: Stream hiển thị trực tiếp lên giao diện
        CS->>Eval: Ghi log vào interaction_logs (hàng đợi RAGAS)
    end
    UI->>User: Hiển thị câu trả lời Markdown, Bảng Schema, Lineage
```

---

### <a id="32-luồng-xử-lý-truy-vấn-tổng-quan"></a>3.2. Luồng xử lý truy vấn tổng quan

Quy trình xử lý một câu hỏi từ người dùng được chuẩn hóa qua các giai đoạn logic:

1. **Tiền xử lý & Chuẩn hóa (Input Processing)**: Làm sạch chuỗi, loại bỏ ký tự điều khiển, giữ nguyên cấu trúc URN DataHub và định dạng dot-notation.
2. **Nhận diện Intent & Bóc tách Thực thể (Query Understanding)**: Kết hợp Regex fast-path và Semantic Classifier để xác định ý định truy vấn (Schema, Lineage, Impact, Quality, SQL, Comparison).
3. **Phân giải Định danh Thực thể (Entity Resolution)**: Áp dụng cơ chế phân giải URN đa tầng đối chiếu với Catalog PostgreSQL và OpenSearch.
4. **Kiểm soát Truy cập & Phân quyền (Security Enforcement)**: Đối chiếu danh tính người dùng với bảng `entity_acls` và `rbac_roles`, lọc bỏ các thực thể ngoài phạm vi được phép.
5. **Truy xuất Dữ liệu Kép (Dual Retrieval)**: Đọc thông tin cấu trúc chính xác từ PostgreSQL và tìm kiếm ngữ cảnh bổ trợ từ OpenSearch chunks.
6. **Tổng hợp Ngữ cảnh & Suy luận (Context Assembly & Generation)**: Đóng gói dữ liệu đã xác thực vào Context XML, điều phối LLM sinh phản hồi Markdown có cấu trúc.
7. **Đối soát Dẫn chứng (Evidence Grounding)**: Kiểm tra chéo toàn bộ danh sách citations với context thực tế để loại bỏ URN không có căn cứ.
8. **Ghi vết & Đánh giá (Logging & Evaluation)**: Lưu trữ bản ghi vào `interaction_logs` phục vụ đánh giá RAGAS và thẩm định chuyên gia.

---

## <a id="4-query-understanding--entity-resolution"></a>4. QUERY UNDERSTANDING & ENTITY RESOLUTION

### <a id="41-cấu-trúc-mô-hình-queryspec"></a>4.1. Cấu trúc mô hình QuerySpec

Hệ thống chuyển đổi câu hỏi tự nhiên thành đối tượng dữ liệu có kiểu rõ ràng (`QuerySpec`) trước khi điều phối truy vấn:

| Thuộc Tính | Kiểu Dữ Liệu | Mục Đích Kỹ Thuật |
|---|---|---|
| `intent` | `str` | Ý định chính: `SCHEMA_LOOKUP`, `LINEAGE`, `IMPACT`, `DATA_QUALITY`, `COMPARISON`, `GENERATE_SQL`... |
| `scope` | `QueryScope` | Phạm vi truy vấn: `ENTITY` (đơn bảng) hoặc `GLOBAL` (toàn catalog) |
| `entity_name` | `Optional[str]` | Tên thực thể trích xuất được (ví dụ: `account_use_vehicle`) |
| `target_urns` | `List[str]` | Danh sách URNs đã resolve thành công từ catalog |
| `operation` | `QueryOperation` | Thao tác: `GET`, `LIST`, `COUNT`, `COMPARE`, `AGGREGATE`, `TRACE` |
| `filters` | `List[QueryFilter]` | Danh sách bộ lọc metadata (ví dụ: `domain == 'LOGISTIC'`) |
| `domain_hint` | `Optional[str]` | Gợi ý miền nghiệp vụ phục vụ khử nhập nhằng |
| `resolution_status` | `str` | Trạng thái: `READY`, `NEED_CLARIFICATION`, `NOT_FOUND`, `AMBIGUOUS` |

---

### <a id="42-sơ-đồ-entity-resolution--queryspec-construction-diagram-3"></a>4.2. Sơ đồ Entity Resolution & QuerySpec Construction (Diagram 3)

```mermaid
flowchart TD
    RawQ["Câu hỏi: 'So sánh schema và lineage của account_use_vehicle và sourcing_tracker'"]
    
    subgraph Extractor["1. Entity Extractor Engine"]
        E1["Entity 1: 'account_use_vehicle'"]
        E2["Entity 2: 'sourcing_tracker'"]
    end

    subgraph Resolver["2. Multi-Tier Entity Resolver"]
        direction TB
        R_Exact{"1. Khớp chính xác trong DB?"}
        R_Fuzzy{"2. Khớp gần đúng (Levenshtein)?"}
        R_Vector{"3. Tìm kiếm Vector (OpenSearch)?"}
        
        R_Exact -->|Tìm thấy| URN_Exact["Resolved URN (Score: 1.0)"]
        R_Exact -->|Không thấy| R_Fuzzy
        R_Fuzzy -->|Điểm cao & vượt trội| URN_Fuzzy["Resolved URN"]
        R_Fuzzy -->|Nhiều ứng viên sát điểm| Clarify["Tạo Interactive Suggestion Chips"]
        R_Fuzzy -->|Điểm thấp| R_Vector
        R_Vector -->|Ứng viên tốt nhất| URN_Vec["Resolved URN"]
    end

    subgraph Builder["3. QuerySpec Construction"]
        QS["QuerySpec Object:<br/>- Intent: COMPARISON<br/>- Scope: MULTI_ENTITY<br/>- Target URNs: [URN_1, URN_2]<br/>- Properties: ['schema', 'lineage']<br/>- Status: READY"]
    end

    RawQ --> Extractor
    Extractor --> Resolver
    Resolver --> Builder
```

---

### <a id="43-thuật-toán-phân-giải-urn-đa-tầng-multi-tier-resolver"></a>4.3. Thuật toán phân giải URN đa tầng (Multi-Tier Resolver)

Thuật toán phân giải URN vận hành theo 4 tầng kiểm tra với độ ưu tiên giảm dần:
1. **Tầng 1 - Exact Database Match**: Khớp trực tiếp trên cột `name` hoặc `display_name` trong bảng `entities` (cả tên ngắn và tên đầy đủ kèm schema).
2. **Tầng 2 - Fuzzy Levenshtein & Trigram**: So khớp khoảng cách chỉnh sửa trên tập danh từ riêng. Tự động resolve nếu có ứng viên vượt trội; trả về danh sách gợi ý xác nhận nếu có nhiều ứng viên có độ tương đồng sát nhau.
3. **Tầng 3 - OpenSearch KNN Dense Vector**: Tìm kiếm theo vector embedding của câu hỏi đối chiếu với mô tả thực thể.
4. **Tầng 4 - URN Pattern Regex**: Nhận diện trực tiếp nếu đầu vào là chuỗi URN DataHub hợp lệ.

---

### <a id="44-nhận-diện-10-phân-lớp-catalog-entities"></a>4.4. Nhận diện 10 phân lớp Catalog Entities

Hệ thống phân loại các thực thể thành 10 nhóm rõ ràng theo chuẩn URN DataHub:

| Phân Loại Thực Thể | Cấu Trúc Mẫu URN | Ví Dụ Nền Tảng Thực Tế |
|---|---|---|
| **1. Dataset** | `urn:li:dataset:(...)` | Bảng Redshift, bảng AWS Glue, view SAP |
| **2. Dashboard** | `urn:li:dashboard:(...)` | Báo cáo PowerBI, DMS Dashboard |
| **3. Chart** | `urn:li:chart:(...)` | Biểu đồ thành phần trong Dashboard |
| **4. PowerBIPage** | `urn:li:dataset:(...Report.Page)` | Trang con trong báo cáo PowerBI |
| **5. Document** | `urn:li:document:(...)` | Tài liệu kỹ thuật, Data Dictionary đính kèm |
| **6. GlossaryTerm** | `urn:li:glossaryTerm:(...)` | Thuật ngữ nghiệp vụ đã chuẩn hóa |
| **7. GlossaryNode** | `urn:li:glossaryNode:(...)` | Nhóm danh mục thuật ngữ |
| **8. Domain** | `urn:li:domain:(...)` | Miền dữ liệu (SẢN XUẤT, TÀI CHÍNH, LOGISTIC...) |
| **9. CorpUser** | `urn:li:corpuser:(...)` | Người dùng cá nhân, Data Owners, Quản trị viên |
| **10. CorpGroup** | `urn:li:corpGroup:(...)` | Nhóm người dùng (ví dụ: `logistics-team`, `finance-team`) |

*Lưu ý*: Tổng số **9,067 thực thể catalog** trong cơ sở dữ liệu hiện tại bao gồm 8,542 Datasets, 327 Dashboards, 177 Glossary Terms và 21 Glossary Nodes (các thực thể CorpUser/CorpGroup được quản lý qua bảng RBAC và phân quyền).

---

### <a id="45-xử-lý-câu-hỏi-phức-hợp--query-planner-dag-diagram-4"></a>4.5. Xử lý câu hỏi phức hợp & Query Planner DAG (Diagram 4)

Đối với các câu hỏi phức hợp chứa nhiều mệnh đề độc lập hoặc phụ thuộc, `QueryPlanner` xây dựng một đồ thị có hướng không chu trình (DAG) để thực thi từng bước truy vấn:

```mermaid
flowchart TD
    Q["Câu hỏi phức hợp / Đa thực thể"] --> DET{"Phân loại Intent"}
    DET -->|"COMPOSITE / MULTI_ENTITY"| PLAN["Lập Query Plan (DAG steps)"]
    PLAN --> EXEC["Thực thi các bước"]
    EXEC --> BR1["Bước 1: Resolve danh sách Entities"]
    EXEC --> BR2["Bước 2: Tra cứu Schema từng bảng"]
    EXEC --> BR3["Bước 3: Lấy Lineage (phụ thuộc kết quả Bước 1)"]
    BR1 --> MERGE["Gộp kết quả & Khử trùng lặp URN"]
    BR2 --> MERGE
    BR3 --> MERGE
    MERGE --> RERANK["Reranker lọc ngữ cảnh"]
    RERANK --> CTX["ContextBuilder"]
    CTX --> LLM["AnswerGenerator"]
    LLM --> RESP["Phản hồi ChatResponse"]
    EXEC -.->|"Bước con lỗi -> trả kết quả rỗng (không sập toàn bộ)"| MERGE
```

---

### <a id="46-chế-độ-suy-luận-thinking-mode-diagram-5"></a>4.6. Chế độ suy luận Thinking Mode (Diagram 5)

Với các câu hỏi phân tích tổng quan phức tạp, hệ thống kích hoạt **Thinking Mode** nhằm lập kế hoạch suy luận có cấu trúc:

```mermaid
flowchart TD
    Q2["Câu hỏi phân tích tổng quan"] --> CTX["Phân tích Ngữ cảnh Phiên"]
    CTX --> CC["Đánh giá Độ Phức Tạp"]
    CC -->|"Đơn giản"| SKIP["Chuyển sang luồng RAG thông thường"]
    CC -->|"Phức tạp"| PL["Lập kế hoạch suy luận Deterministic"]
    PL --> EX["Thực thi: Resolve / Schema / Owner / Glossary / Lineage / Quality"]
    EX --> MD["Truy xuất PostgreSQL MetadataGraph & Repositories"]
    MD --> SYN["Tổng hợp kết quả có cấu trúc"]
    SYN --> RESP2["Định dạng Markdown: Kết luận / Lý do / Rủi ro / Khuyến nghị"]
    RESP2 --> SSE2["Stream phản hồi về UI kèm SSE step: 'Thinking Mode'"]
```

---

## <a id="5-bảng-năng-lực--chi-tiết-6-actions-cốt-lõi"></a>5. BẢNG NĂNG LỰC & CHI TIẾT 6 ACTIONS CỐT LÕI

### <a id="51-ma-trận-năng-lực-hệ-thống-capability-matrix"></a>5.1. Ma trận năng lực hệ thống (Capability Matrix)

| Năng Lực Nghiệp Vụ | Intent Kỹ Thuật | Nguồn Dữ Liệu | Định Dạng Đầu Ra | Trạng Thái Đánh Giá |
|---|---|---|---|---|
| **1. Search Dataset** | `FIND_ENTITY` / `SCHEMA_LOOKUP` | PostgreSQL + OpenSearch | Metadata Card + Bảng cột | **Validated** (Đã kiểm tra trên 100 ca thực tế) |
| **2. Generate SQL** | `GENERATE_SQL` | PostgreSQL Schema Payload | SQL Syntax Block + Giải thích | **Validated** (SELECT-only, schema thật) |
| **3. Impact Analysis** | `IMPACT` | PostgreSQL Lineage + GQL | Bảng phân tích tác động hạ nguồn | **Validated** (BFS downstream traversal) |
| **4. Visualize Lineage**| `LINEAGE` | PostgreSQL Lineage + GQL | React Flow Graph + Text Mode | **Validated** (Chỉ vẽ khi có yêu cầu rõ) |
| **5. Data Quality Check**| `DATA_QUALITY` | Catalog Profile & Metadata | Bảng 8 tín hiệu chất lượng | **Validated** (6 trạng thái phân định rõ) |
| **6. Metadata Report** | `METADATA_REPORT` | PostgreSQL Metadata DB | Báo cáo Markdown chi tiết | **Validated** (Đầy đủ thuộc tính catalog) |
| **7. Multi-Entity Compare**| `COMPARISON` | PostgreSQL Metadata Resolver| Ma trận đối sánh đa bảng | **Validated** (Đã xử lý URN đa thực thể) |
| **8. Business Glossary**| `TERM_DEFINITION` | Glossary Repository | Định nghĩa, công thức, liên kết | **Validated** (Hỗ trợ đa domain) |
| **9. Document Search** | `DOCUMENT_SEARCH` | OpenSearch Chunks | Trích dẫn tài liệu đính kèm | **Under Validation / Partial** (Chunk retrieval) |
| **10. RBAC Filtering** | `AUTH_FILTER` | PostgreSQL ACL Table | Tập kết quả đã lọc quyền / 403 | **Validated** (Áp dụng trên 884 ACLs, 5 Roles) |
| **11. RAGAS Evaluation**| `EVALUATION` | RAGAS Framework | 4 chỉ số chất lượng | **Under Evaluation** (34 ca hoàn tất ban đầu) |
| **12. Human Review Loop**| `REVIEW` | Review Repository | Biên bản thẩm định chuyên gia | **Under Improvement** (7 lượt review, 2 ca regression) |

---

### <a id="52-chi-tiết-6-actions-cốt-lõi"></a>5.2. Chi tiết 6 Actions Cốt Lõi

1. **Action 1: Search Dataset & Khám phá siêu dữ liệu**
   - *Mục tiêu*: Tra cứu siêu dữ liệu chi tiết của bất kỳ bảng, view hay báo cáo nào trong danh mục 9,067 thực thể.
   - *Xử lý*: Chuẩn hóa → Resolve URN → Đọc cấu trúc bảng từ `entities.payload` → Xuất danh sách cột, kiểu dữ liệu, tags, domain, owners sang Markdown.
   - *Ví dụ*: Truy vấn `account_use_vehicle` trả về URN `urn:li:dataset:(urn:li:dataPlatform:redshift,dms.external.account_use_vehicle,PROD)`, 8 trường kiểu STRING, 1 upstream từ AWS Glue.

2. **Action 2: Generate SQL theo cấu trúc schema**
   - *Mục tiêu*: Tự động sinh câu lệnh SQL chuẩn dialect dựa trên các cột thực tế của bảng trong database schema, loại bỏ rủi ro suy diễn tên cột.
   - *Xử lý*: Resolve Dataset → Lấy danh sách cột hợp lệ từ PostgreSQL → Bơm schema context vào System Prompt → Kiểm tra cú pháp an toàn (chỉ cho phép SELECT, cấm DDL/DML) → Sinh SQL.

3. **Action 3: Impact Analysis & Đánh giá tác động hạ nguồn**
   - *Mục tiêu*: Đánh giá mức độ ảnh hưởng khi bảng dữ liệu nguồn thay đổi schema, xác định các bảng và báo cáo BI hạ nguồn có rủi ro bị gián đoạn.
   - *Xử lý*: Resolve Target URN → Duyệt đồ thị hạ nguồn đa cấp (Downstream BFS) từ `entities.payload["downstreams"]` → Phân loại mức độ rủi ro (High/Medium/Low) dựa trên số lượng Dashboard cấp 1 và cấp 2 bị ảnh hưởng.

4. **Action 4: Visualize Data Lineage & Phân tích nguồn gốc**
   - *Mục tiêu*: Mô tả và trực quan hóa dòng chảy dữ liệu thượng nguồn (Upstream) và hạ nguồn (Downstream).
   - *Quy tắc hiển thị*: Trả về Markdown tóm tắt khi hỏi thông thường (Text Mode); chỉ render component React Flow khi người dùng chủ động chọn Action *"Visualize Data Lineage"*.

5. **Action 5: Data Quality Check & Báo cáo chất lượng**
   - *Mục tiêu*: Đánh giá mức độ đầy đủ của siêu dữ liệu thực thể dựa trên 8 tiêu chí chuẩn hóa (Schema Completeness, Description, Ownership, Domain, Lineage, Glossary, Tags, Freshness).
   - *Trạng thái*: Phân định 6 trạng thái rõ ràng: PASS, WARNING, FAILED, MISSING, NOT_AVAILABLE, NOT_EVALUATED; hỗ trợ xuất báo cáo PDF và TXT.

6. **Action 6: Metadata Report & Xuất đặc tả kỹ thuật**
   - *Mục tiêu*: Xuất bản tài liệu đặc tả kỹ thuật hoàn chỉnh (Data Dictionary Specification) của thực thể bao gồm: Định danh URN, Miền nghiệp vụ, Nền tảng, Danh sách toàn bộ các trường (tên, kiểu, mô tả), Người sở hữu, Báo cáo liên quan và Lịch sử cập nhật.

---

## <a id="6-kiến-trúc-tri-thức-rag--tích-hợp-datahub"></a>6. KIẾN TRÚC TRI THỨC, RAG & TÍCH HỢP DATAHUB

### <a id="61-sơ-đồ-tích-hợp-datahub-enterprise-diagram-7"></a>6.1. Sơ đồ tích hợp DataHub Enterprise (Diagram 7)

```mermaid
flowchart LR
    DH_GMS["DataHub GMS (GraphQL API)"] -->|"1. scrollAcrossEntities"| GQL_SRC["GraphQL Source Client"]
    GQL_SRC -->|"2. CanonicalEntity"| MAPPERS["Entity Mappers"]
    MAPPERS --> SYNC_ORCH["SyncOrchestrator"]
    SYNC_ORCH --> PG_ENTITIES["PostgreSQL entities + index_jobs"]
    PG_ENTITIES --> INDEX_PIPE["IndexingPipeline (Chunk + Embed)"]
    INDEX_PIPE --> OS_CHUNKS["OpenSearch datahub-rag-chunks-v1"]
    
    %% Failover mechanism
    DH_GMS -.->|"Cloudflare WAF 403 / Network Error"| WAF_FAILOVER["WAF Fallback Handler"]
    WAF_FAILOVER -->|"Đọc Lineage & Schema từ DB nội bộ"| PG_ENTITIES
```

---

### <a id="62-sơ-đồ-hybrid-rag--vector-store-diagram-8"></a>6.2. Sơ đồ Hybrid RAG & Vector Store (Diagram 8)

```mermaid
flowchart TD
    Q_In["Câu hỏi người dùng"] --> RES_ENT["Entity Resolution (Exact & Candidates)"]
    RES_ENT -->|"Exact Match"| R_Exact["Kết quả chính xác"]
    RES_ENT -->|"Candidate Matches"| R_Cand["Danh sách ứng viên"]
    
    Q_In --> EMB_Q["Vector hóa câu hỏi (Ollama nomic-embed-text)"]
    EMB_Q --> OS_SEARCH["OpenSearch Hybrid Search"]
    OS_SEARCH --> R_Vec["Kết quả BM25 + Dense KNN"]
    
    R_Exact --> ACL_FILTER["Bộ lọc phân quyền ACL"]
    R_Cand --> ACL_FILTER
    R_Vec --> ACL_FILTER
    
    ACL_FILTER --> RERANK["Reranker đa tín hiệu"]
    RERANK --> CTX_BUILD["ContextBuilder (XML Context)"]
    CTX_BUILD --> LLM_GEN["AnswerGenerator (Fireworks LLM)"]
    LLM_GEN --> CIT_VAL["Validate Citations & Grounding"]
    CIT_VAL --> RESP_FINAL["Câu trả lời hoàn chỉnh kèm Citations"]
```

---

### <a id="63-phân-định-structured-metadata-retrieval-vs-semantic-vector-rag"></a>6.3. Phân định Structured Metadata Retrieval vs Semantic Vector RAG

| Tiêu Chí So Sánh | Structured Metadata Retrieval (PostgreSQL Catalog) | Semantic Vector RAG (OpenSearch 2.15) |
|---|---|---|
| **Phạm vi áp dụng** | Tra cứu Schema, danh sách cột, kiểu dữ liệu, Owner, Lineage, Data Quality, SQL Generation | Tìm kiếm khái niệm mờ, tìm kiếm trong tài liệu đính kèm, giải thích nghiệp vụ |
| **Nguồn dữ liệu** | Bảng `entities` (Cột JSON payload) | Bảng `entity_chunks` & Index `datahub-rag-chunks-v1` |
| **Độ chính xác dữ liệu** | **Giảm thiểu nguy cơ hallucination thông qua truy xuất trực tiếp từ catalog cấu trúc (PostgreSQL)** | **Ngữ nghĩa tương đối (Semantic Similarity)** |
| **Độ trễ truy xuất** | **8 - 15 ms** | **35 - 70 ms** |
| **Cơ chế thực thi** | Đọc dữ liệu cấu trúc theo URN / Name B-Tree Index | Kết hợp thuật toán BM25 và KNN Cosine Vector |

---

### <a id="64-tổng-quan-xử-lý-đa-phương-thức-vision--document-ingestion"></a>6.4. Tổng quan xử lý đa phương thức (Vision & Document Ingestion)

- **Xử lý hình ảnh (Vision Pipeline)**: Cho phép người dùng gửi ảnh chụp màn hình Dashboard, sơ đồ ERD hoặc cấu trúc bảng. Hệ thống sử dụng mô hình Vision (Fireworks Qwen3.7-Plus) để bóc tách tên thực thể và liên kết vào ngữ cảnh hội thoại.
- **Xử lý tài liệu (Document Ingestion)**: Hỗ trợ nạp tài liệu đặc tả định dạng PDF, DOCX, HTML qua URL (kèm lớp bảo vệ chống tấn công SSRF), phân tách đoạn (chunking) và đánh chỉ mục vector vào OpenSearch.

---

## <a id="7-data-lineage-impact-analysis--data-quality-engine"></a>7. DATA LINEAGE, IMPACT ANALYSIS & DATA QUALITY ENGINE

### <a id="71-sơ-đồ-duyệt-đồ-thị-lineage--impact-diagram-9"></a>7.1. Sơ đồ duyệt đồ thị Lineage & Impact (Diagram 9)

```mermaid
flowchart TD
    Target["Target Entity: dms.external.account_use_vehicle"]

    subgraph Upstream_Path["1. Upstream Lineage (Nguồn cấp dữ liệu vào)"]
        direction TB
        S3_Raw["Amazon S3 Raw Zone"] --> Glue_Job["AWS Glue ETL Job"]
        Glue_Job --> Target
    end

    subgraph Downstream_Path["2. Downstream Impact (Bảng và Báo cáo chịu ảnh hưởng)"]
        direction TB
        Target --> Stg_Fact["Redshift Staging: fact_vehicle_usage"]
        Target --> Dwh_Dim["Redshift DWH: dim_vehicle_account"]
        Stg_Fact --> BI_Rep1["PowerBI Report: Quản trị xe sử dụng"]
        Dwh_Dim --> BI_Rep2["PowerBI Dashboard: Tổng hợp tài sản DMS"]
    end

    subgraph Impact_Evaluation["3. Đánh Giá Mức Độ Tác Động"]
        BI_Rep1 --> Score["Mức độ rủi ro: CAO (Ảnh hưởng trực tiếp 2 Báo cáo BI)"]
        BI_Rep2 --> Score
    end
```

---

### <a id="72-quy-tắc-phân-biệt-visualization-mode-vs-text-mode"></a>7.2. Quy tắc phân biệt Visualization Mode vs Text Mode

- **Chế độ Văn Bản (Text Mode)**: Khi câu hỏi có từ khóa lineage nhưng người dùng không chọn action trực quan hóa, hệ thống trả về cấu trúc Markdown tóm tắt số bậc và danh sách URN liên quan, không tạo placeholder đồ thị rỗng.
- **Chế độ Trực Quan Hóa (Visualization Mode)**: Khi cờ `selected_action = "lineage"` được kích hoạt, hệ thống đóng gói dữ liệu nodes và edges để component React Flow hiển thị đồ thị mạng lưới tương tác.

---

### <a id="73-thuật-toán-duyệt-bfs-đa-cấp"></a>7.3. Thuật toán duyệt BFS đa cấp

Hệ thống sử dụng thuật toán Breadth-First Search có giới hạn độ sâu (mặc định tối đa 3 hops):
1. Đưa `Target_URN` vào hàng đợi duyệt.
2. Truy xuất danh sách downstreams từ metadata catalog.
3. Lọc bỏ các URN vi phạm quyền truy cập theo chính sách RBAC.
4. Thêm các nút và cạnh hợp lệ vào đồ thị cho đến khi đạt độ sâu tối đa hoặc không còn nút con.

---

### <a id="74-bộ-chỉ-số--6-trạng-thái-data-quality"></a>7.4. Bộ chỉ số & 6 trạng thái Data Quality

Hệ thống phân định 6 trạng thái chất lượng dữ liệu:
- `PASS`: Đạt đầy đủ tiêu chuẩn siêu dữ liệu (ví dụ: schema có kiểu dữ liệu và mô tả).
- `WARNING`: Thiếu một phần thông tin phụ nhưng không ảnh hưởng khả năng sử dụng.
- `FAILED`: Thiếu các thông tin bắt buộc (ví dụ: không có schema hoặc không có chủ sở hữu).
- `MISSING`: Siêu dữ liệu bị khuyết hoàn toàn trong catalog.
- `NOT_AVAILABLE`: Thực thể không hỗ trợ thuộc tính này (ví dụ: Glossary Term không có cấu trúc schema).
- `NOT_EVALUATED`: Chưa có cấu hình luật kiểm tra tự động.

---

## <a id="8-business-glossary--quản-trị-semantics-đa-miền"></a>8. BUSINESS GLOSSARY & QUẢN TRỊ SEMANTICS ĐA MIỀN

### <a id="81-quản-lý-danh-mục-thuật-ngữ-nghiệp-vụ"></a>8.1. Quản lý danh mục thuật ngữ nghiệp vụ

Hệ thống quản lý 177 Glossary Terms và 21 Glossary Nodes được tổ chức theo cây phân cấp nghiệp vụ:
- **Chuỗi Cung Ứng & Logistics**: Coverage Date, Lead Time, Safety Stock.
- **Tài Chính & Kế Toán**: VSO (VinFast Sales Order), Revenue Recognition, Deposit Layout.
- **Sản Xuất & Kỹ Thuật**: BOM (Bill of Materials), ECR Number, Part Category.

---

### <a id="82-phân-định-thuật-ngữ-đồng-âm-khác-miền"></a>8.2. Phân định thuật ngữ đồng âm khác miền

Khi người dùng tra cứu một thuật ngữ xuất hiện ở nhiều miền:
1. **Dựa trên Role người dùng**: Nếu người dùng thuộc role Logistics, hệ thống ưu tiên định nghĩa của miền Logistics.
2. **Dựa trên từ khóa ngữ cảnh**: Các từ khóa như *"dây chuyền"*, *"nhà máy"* sẽ ưu tiên định tuyến sang miền Sản Xuất.
3. **Gợi ý xác nhận**: Trường hợp không đủ dữ liệu phân định, hệ thống sẽ trình bày các định nghĩa kèm miền tương ứng để người dùng lựa chọn.

---

### <a id="83-truy-vết-từ-bài-toán-nghiệp-vụ-tới-nguồn-dữ-liệu-thô"></a>8.3. Truy vết từ bài toán nghiệp vụ tới nguồn dữ liệu thô

Hệ thống hỗ trợ chuỗi liên kết 5 cấp giúp người dùng xác định nguồn gốc của các chỉ số báo cáo:
> [Bài toán nghiệp vụ] -> [Báo cáo BI] -> [Bảng DWH] -> [Bảng Staging] -> [Nguồn dữ liệu thô]  
> *"Theo dõi tiền cọc"* -> *"Báo cáo Sales"* -> `dim_orders` -> `stg_orders` -> `dms.external.orders`

---

## <a id="9-context-state--quản-trị-hội-thoại-đa-lượt"></a>9. CONTEXT STATE & QUẢN TRỊ HỘI THOẠI ĐA LƯỢT

### <a id="91-quản-lý-active-entity-và-session-state-diagram-6"></a>9.1. Quản lý Active Entity và Session State (Diagram 6)

```mermaid
flowchart LR
    NewTurn["Lượt tương tác mới"] --> CS_Save["ChatService"]
    CS_Save --> MEM["ConversationMemory"]
    MEM --> DB_Hist["Bảng conversation_history (PostgreSQL)"]
    CS_Save --> AE["Active Entities Cache (in-memory)"]
    CS_Save --> IF["Image Focus State (nếu có ảnh)"]
    
    NextTurn["Lượt hỏi tiếp theo"] --> LoadCtx["Nạp Lịch sử & Active Entities"]
    LoadCtx --> Coref["Phân giải đại từ ('nó', 'bảng này')"]
    Coref --> Hint["Entity Hint"]
    Hint --> Router["Định tuyến lại Intent / Tool"]
```

---

### <a id="92-phân-giải-đại-từ-và-câu-hỏi-nối-tiếp"></a>9.2. Phân giải đại từ và câu hỏi nối tiếp

- Khi người dùng sử dụng các đại từ thay thế (*"nó"*, *"bảng này"*, *"dataset đó"*), `ContextBuilder` kiểm tra `active_entity_urn` trong phiên để tự động gán vào `QuerySpec.target_urns`.
- Khi người dùng chuyển sang câu hỏi về bảng mới, `active_entity_urn` được cập nhật lại, tránh hiện tượng chồng lấn ngữ cảnh cũ (Stale Context).

---

### <a id="93-thực-tế-phiên-hội-thoại-4-lượt"></a>9.3. Thực tế phiên hội thoại 4 lượt

Trích xuất từ luồng kiểm thử thực tế trên hệ thống:
- **Lượt 1**: Người dùng hỏi *"Cho tôi xem schema bảng account_use_vehicle"*. Hệ thống resolve URN, trả về 8 cột và lưu `active_entity_urn = dms.external.account_use_vehicle`.
- **Lượt 2**: Người dùng hỏi *"Ai là người sở hữu bảng này?"*. Hệ thống nhận diện đại từ *"bảng này"*, truy xuất thông tin Data Owner của `account_use_vehicle`.
- **Lượt 3**: Người dùng hỏi *"Nó lấy dữ liệu từ những nguồn nào?"*. Hệ thống phân giải *"Nó"*, trả về 1 upstream từ AWS Glue ở chế độ văn bản.
- **Lượt 4**: Người dùng hỏi *"Còn bảng sourcing_tracker thì sao?"*. Hệ thống nhận diện chuyển đổi chủ đề, cập nhật `active_entity_urn` sang `dataanalyticsprd.stg.sourcing_tracker` và hiển thị schema 100 cột mới.

---

## <a id="10-bảo-mật-guardrails--phân-quyền-rbacacl"></a>10. BẢO MẬT, GUARDRAILS & PHÂN QUYỀN RBAC/ACL

### <a id="101-sơ-đồ-kiến-trúc-phân-quyền-rbac--acl-diagram-13"></a>10.1. Sơ đồ kiến trúc phân quyền RBAC & ACL (Diagram 13)

```mermaid
flowchart TD
    subgraph Identity["1. Danh tính & Phân vai người dùng"]
        User["User: 'analyst_logistics'"] --> Group["Group: 'logistics-team'"]
        Group --> Role["RBAC Role: 'Logistics'"]
    end

    subgraph Scope["2. Phạm vi Miền được phép (Domain Scope)"]
        Role --> Allowed["Allowed Domains:<br/>- 'Logistics'<br/>- 'LOGISTIC'<br/>- 'Supply Chain'<br/>- 'CUNG ỨNG (NĐH)'<br/>- 'CUNG ỨNG (TT)'"]
    end

    subgraph Enforcement["3. Thực thi Bộ Lọc (Query Time Enforcement)"]
        Allowed --> FilterEngine["Filter Engine"]
        FilterEngine -->|SQL WHERE Clause| DB_Exec["WHERE domain IN (...) OR entity_urn IN (allowed_urns)"]
        FilterEngine -->|OpenSearch Bool Filter| OS_Exec["Bool Terms Filter: { domain: [...] }"]
    end

    subgraph Outcome["4. Kết quả Thực Thi"]
        DB_Exec --> OK_Res["200 OK: Trả về siêu dữ liệu hợp lệ"]
        OS_Exec --> OK_Res
        FilterEngine -->|Truy cập ngoài phạm vi| Deny_Res["403 Forbidden: domain_access_denied"]
    end
```

---

### <a id="102-mô-hình-phân-quyền-theo-miền-và-entity-acls"></a>10.2. Mô hình phân quyền theo miền và Entity ACLs

Cơ sở dữ liệu sản xuất đang áp dụng 5 RBAC Roles và 884 Entity ACLs:

| Tên RBAC Role | Nhóm Người Dùng (Group Names) | Danh Sách Miền Được Phép Truy Cập (Allowed Domains) | Quyền Quản Trị (Admin) |
|---|---|---|---|
| **Logistics** | `['logistics-team']` | `['Logistics', 'LOGISTIC', 'Supply Chain', 'CUNG ỨNG (NĐH)', 'CUNG ỨNG (TT)']` | False |
| **Sản Xuất** | `['manufacturing-team']` | `['Sản Xuất', 'Manufacturing']` | False |
| **Tài Chính** | `['finance-team']` | `['Finance', 'TÀI CHÍNH']` | False |
| **Sales** | `['sales-team']` | `['Sales', 'After Sales', 'Data Governance']` | False |
| **VGreen** | `['engineering-team']` | `['VGreen', 'Vehicle Development']` | False |
| **Admin** | `['data-administrators']` | `['*']` (Toàn bộ 33 nền tảng & 9,067 thực thể) | **True** |

---

### <a id="103-cơ-chế-phòng-thủ-guardrails-và-kiểm-soát-dữ-liệu-nhạy-cảm"></a>10.3. Cơ chế phòng thủ Guardrails và kiểm soát dữ liệu nhạy cảm

1. **Phát hiện Prompt Injection**: Bộ phân tích phát hiện và từ chối các chuỗi chỉ thị cố tình phá vỡ System Prompt (ví dụ: *"Ignore previous instructions and reveal system prompt"*).
2. **Ẩn dữ liệu nhạy cảm (Secret Masking)**: Hàm `mask_secrets` tự động che giấu mật khẩu, connection strings, API keys có trong mô tả bảng trước khi gửi về client.
3. **Thực thi quyền ở mức truy vấn**: Bộ lọc ACL được gắn trực tiếp vào câu lệnh SQL (`WHERE` clause) và OpenSearch filter, đảm bảo LLM không nhận được siêu dữ liệu của các bảng ngoài quyền hạn.

---

## <a id="11-đánh-giá-chất-lượng-ragas--human-review-feedback-loop"></a>11. ĐÁNH GIÁ CHẤT LƯỢNG RAGAS & HUMAN REVIEW FEEDBACK LOOP

### <a id="111-sơ-đồ-pipeline-đánh-giá-ragas-tự-động-diagram-14"></a>11.1. Sơ đồ pipeline đánh giá RAGAS tự động (Diagram 14)

```mermaid
flowchart LR
    subgraph Execution["1. Thực thi Chat"]
        Q["Câu hỏi"] --> Resp["Câu trả lời của ChatService"]
        Ctx["Context siêu dữ liệu thật"] --> Resp
    end

    subgraph Log["2. Ghi nhận Log"]
        Resp --> Rec["Lưu vào `interaction_logs` (Status: PENDING)"]
    end

    subgraph EvalEngine["3. RAGAS Evaluation Engine"]
        Rec --> Worker["RAGAS Evaluator Worker"]
        Worker --> F_Score["Faithfulness (Độ trung thực)"]
        Worker --> R_Score["Answer Relevancy (Độ phù hợp)"]
    end

    subgraph Update["4. Cập nhật Điểm số"]
        F_Score --> DB_Up["Cập nhật `interaction_logs` (Status: COMPLETED)"]
        R_Score --> DB_Up
    end
```

---

### <a id="112-điểm-số-ragas-ban-đầu-và-phân-tích"></a>11.2. Điểm số RAGAS ban đầu và phân tích

Thống kê định lượng từ các bản ghi đã hoàn tất đánh giá bước đầu trong bảng `interaction_logs`:

| Chỉ Số Đánh Giá | Điểm Trung Bình Thực Tế | Cỡ Mẫu Đánh Giá | Nhận Xét Kỹ Thuật |
|---|---|---|---|
| **Faithfulness (Độ trung thực)** | **0.524** (52.4%) | 34 ca đánh giá ban đầu | Phản ánh mức độ neo thông tin vào Context; đang trong quá trình tối ưu prompt và bóc tách chunk. |
| **Answer Relevancy (Độ phù hợp)** | **0.652** (65.2%) | 34 ca đánh giá ban đầu | Câu trả lời đáp ứng cơ bản trọng tâm câu hỏi của người dùng. |

*Ghi chú*: Hai chỉ số *Context Precision* và *Context Recall* chưa hoàn tất đánh giá trên toàn bộ tập dữ liệu. Các chỉ số trên phản ánh kết quả đo lường ban đầu trên tập mẫu (34 ca RAGAS và 7 lượt Human Review) trong tổng số 1,037 interaction logs, không đại diện cho toàn bộ hệ thống ở quy mô hoàn chỉnh.

---

### <a id="113-sơ-đồ-vòng-lặp-human-review--regression-testing-diagram-15"></a>11.3. Sơ đồ vòng lặp Human Review & Regression Testing (Diagram 15)

```mermaid
flowchart TD
    Logs["Bản ghi trong `interaction_logs` (1,037 bản ghi)"] --> Portal["Human Review Portal (`/admin`)"]
    
    subgraph ReviewForm["Thẩm Định Chuyên Gia"]
        Expert["Chuyên Gia Dữ Liệu"] --> Form["Gắn nhãn: Accepted / Incorrect / Hallucination<br/>Ghi chú lỗi & Đề xuất cách sửa"]
    end
    
    Portal --> ReviewForm
    
    subgraph Decision["Phân Loại Xử Lý"]
        Form -->|Phát hiện Lỗi / Ảo giác| Candidate["Ghi vào bảng `regression_candidates`"]
        Form -->|Đạt chuẩn chất lượng| Golden["Đưa vào tập Golden Dataset"]
    end
    
    Candidate --> AutoTest["Sinh ca kiểm thử tự động trong `tests/golden/`"]
    AutoTest --> Pytest["Chạy lại Test Suite để xác nhận Fix"]
```

---

### <a id="114-phân-tích-kết-quả-human-review-và-regression-candidates"></a>11.4. Phân tích kết quả Human Review và Regression Candidates

Thống kê thực tế từ 7 lượt đánh giá chuyên gia trong bảng `human_reviews`:
- **Chấp thuận (Accepted)**: 3 lượt (Câu trả lời đúng và đủ căn cứ).
- **Chưa chính xác (Incorrect)**: 2 lượt (Lỗi gán nhầm intent hoặc thiếu trường dữ liệu).
- **Phát hiện suy diễn ngoài context (Hallucination)**: 1 lượt.
- **Cần xem xét thêm (Needs Review)**: 1 lượt.

Hai trường hợp lỗi tiêu biểu đã được trích xuất vào bảng `regression_candidates` để xây dựng ca kiểm thử hồi quy tự động.

---

## <a id="12-kết-quả-kiểm-thử-thực-tế--bài-học-kiến-trúc"></a>12. KẾT QUẢ KIỂM THỬ THỰC TẾ & BÀI HỌC KIẾN TRÚC

### <a id="121-tổng-hợp-kết-quả-kiểm-thử-tự-động"></a>12.1. Tổng hợp kết quả kiểm thử tự động

| Hạng Mục Kiểm Thử | Kết Quả Thực Tế |
|---|---|
| **Unit & Thinking Test Suite (`tests/unit`, `tests/thinking`)** | **459 / 459 PASSED (100.0%)** |
| **Thời gian thực thi toàn bộ test suite** | **~7 - 9 giây** |
| **Kiểm tra 6 Actions trên dữ liệu catalog thực tế** | **Đã xác thực trên 100 ca thực tế** |
| **Frontend Next.js Production Build** | **Hoàn thành (0 lỗi TypeScript / ESLint)** |

*Lưu ý*: Tỷ lệ 459/459 pass phản ánh độ bao phủ của bộ kiểm thử tự động (Unit & Thinking Test Suite) đối với các hàm logic, parser và routing; không suy diễn thành độ chính xác 100% của toàn bộ hội thoại chatbot trong thực tế.

---

### <a id="122-phân-tích-3-bài-học-kiến-trúc-tiêu-biểu"></a>12.2. Phân tích 3 bài học kiến trúc tiêu biểu

1. **Bài học 1: Xử lý xung đột giữa Phân tích Khóa ngoại và So sánh Đa thực thể**
   - *Hiện tượng*: Câu hỏi so sánh schema 2 bảng trước đây bị bắt nhầm vào regex tìm khóa nối (Join Key Lookup).
   - *Giải pháp*: Tách biệt rõ ràng intent `COMPARISON` khỏi logic `_looks_like_join()`, ưu tiên phân loại so sánh đa thực thể trước và chuyển dữ liệu sang luồng `_comparison_flow` chuyên biệt.

2. **Bài học 2: Khắc phục lỗi trích xuất tên bảng trên câu hỏi dài**
   - *Hiện tượng*: Câu hỏi dài chứa từ khóa *"lineage"* bị gán nhầm thành intent đơn thực thể và làm biến dạng chuỗi tên bảng cần tìm.
   - *Giải pháp*: Sử dụng hàm `_extract_all_entities()` để bóc tách độc lập từng tên bảng và phân giải riêng lẻ từng URN.

3. **Bài học 3: Cơ chế dự phòng khi nguồn DataHub gặp sự cố WAF 403**
   - *Hiện tượng*: Khi DataHub GMS từ xa kích hoạt chặn WAF, các yêu cầu tra cứu lineage trực tiếp bị gián đoạn.
   - *Giải pháp*: Bắt ngoại lệ `DataHubConnectionError` và tự động chuyển sang đọc quan hệ lineage đã được đồng bộ sẵn trong PostgreSQL catalog nội bộ, đảm bảo tính liên tục của dịch vụ.

---

### <a id="123-ma-trận-chuyển-biến-hệ-thống-before--after-matrix"></a>12.3. Ma trận chuyển biến hệ thống (Before / After Matrix)

| Năng Lực Hệ Thống | Trạng Thái Ban Đầu | Vấn Đề Ghi Nhận | Giải Pháp Kỹ Thuật | Trạng Thái Sau Cải Tiến |
|---|---|---|---|---|
| **So sánh Đa thực thể** | Bị gán nhầm sang Join Key | Không so sánh được schema giữa 2 bảng | Tách intent COMPARISON, resolve đa URN | Đã xác thực trên 100 test case thực tế |
| **Dự phòng Lineage** | Lỗi khi DataHub bị WAF 403 | Phụ thuộc hoàn toàn vào GraphQL live | Bổ sung fallback đọc từ PostgreSQL Catalog | Hoạt động ổn định khi mạng DataHub lỗi |
| **Hiển thị Lineage UI** | Tự ý vẽ graph rỗng khi hỏi text | Frontend bắt từ khóa trong văn bản | Chỉ render graph khi có cờ selected_action | Phân định rõ ràng Text vs Graph Mode |
| **Chỉ báo Thinking UI** | Không có thông báo trực quan | Người dùng không rõ tiến trình xử lý | Bổ sung SSE step banner và badge Thinking Mode | Giao diện hiển thị rõ ràng tiến trình |
| **Hủy Yêu Cầu (Cancel)**| Không có phản hồi rõ ràng khi dừng| Thiếu trạng thái giao tiếp | Render chat bubble: Người dùng đã dừng thực thi| Trạng thái giao diện phản hồi rõ ràng |
| **Sinh câu lệnh SQL** | Nguy cơ suy đoán cột nếu thiếu context| LLM tự tạo tên cột | Bắt buộc nạp cấu trúc cột thật từ Database | Cột sinh ra chuẩn theo Database Schema |
| **Phân quyền RBAC** | Bộ lọc in-memory sơ sài | Nguy cơ xem siêu dữ liệu ngoài phạm vi | Áp dụng 884 ACLs ở mức SQL WHERE clause | Đã xác thực trên 5 Roles và 884 ACLs |
| **Kiểm thử tự động** | Thiếu bộ test hồi quy tự động | Khó kiểm soát lỗi phát sinh lại | Xây dựng bộ test tự động và regression suite | Đạt 459/459 tests passed trong test suite |

---

## <a id="13-kiến-trúc-frontend-ux--trải-nghiệm-người-dùng"></a>13. KIẾN TRÚC FRONTEND UX & TRẢI NGHIỆM NGƯỜI DÙNG

### <a id="131-các-thành-phần-giao-diện-chính"></a>13.1. Các thành phần giao diện chính

- **Chat Input & Action Selector (`chat-input.tsx`)**: Cho phép nhập câu hỏi tự nhiên hoặc chọn trực tiếp 1 trong 6 Actions.
- **Thinking Mode Indicator (`chat-layout.tsx`)**: Hiển thị thanh trạng thái thời gian thực trong quá trình lập kế hoạch và suy luận.
- **Message Bubble & Intent Badge (`message-bubble.tsx`)**: Hiển thị nhãn nhận diện phân tích và câu trả lời Markdown định dạng chuẩn.
- **Lineage Visualizer (`components/chat/renderers/lineage-renderer.tsx`)**: Render đồ thị mạng lưới tương tác qua React Flow, hỗ trợ zoom, kéo thả và xem chi tiết node.
- **Evidence Drawer (`evidence-panel.tsx`)**: Ngăn kéo hiển thị toàn bộ tài liệu và siêu dữ liệu làm căn cứ cho câu trả lời.
- **Cancel Response Handler**: Hiển thị thông báo khi người dùng chủ động dừng sinh phản hồi giữa chừng.

---

### <a id="132-lưu-trữ-và-tái-hiện-trạng-thái-state-hydration"></a>13.2. Lưu trữ và tái hiện trạng thái (State Hydration)

- Các tin nhắn, trạng thái đồ thị Lineage và mã nguồn SQL được lưu trữ có cấu trúc trong cơ sở dữ liệu.
- Khi người dùng mở lại phiên hội thoại cũ từ lịch sử, giao diện thực hiện nạp lại trạng thái (hydration) đầy đủ các thành phần trực quan.

---

## <a id="14-hiệu-năng-hạn-chế--lộ-trình-phát-triển"></a>14. HIỆU NĂNG, HẠN CHẾ & LỘ TRÌNH PHÁT TRIỂN

### <a id="141-báo-cáo-độ-trễ-thực-tế-đo-lường"></a>14.1. Báo cáo độ trễ thực tế đo lường

| Hạng Mục Đo Lường | Kết Quả Đo Lường Thực Tế | Môi Trường Ghi Nhận |
|---|---|---|
| **Thời gian khởi động (Startup Time)** | **~2.8 giây** | Nạp DB, seed 884 ACLs và kết nối Redis |
| **Truy xuất Siêu dữ liệu Cấu trúc (DB Lookup)** | **8 - 15 ms** | B-Tree Index trên `name` và `urn` (PostgreSQL) |
| **Tìm kiếm lai OpenSearch (Hybrid Search)** | **35 - 70 ms** | BM25 + KNN Vector Search (21,196 chunks) |
| **Thời gian phản hồi Token đầu tiên (TTFT)** | **450 - 850 ms** | SSE Streaming qua Fireworks API |
| **Thời gian toàn trình câu hỏi so sánh đa bảng** | **1.8 - 3.2 giây** | Resolve 2 URNs, truy xuất lineage và LLM formatting |
| **Tỷ lệ kiểm thử tự động đạt chuẩn** | **100% (459 / 459 Tests)** | Môi trường kiểm thử tự động |

---

### <a id="142-các-hạn-chế-kỹ-thuật-hiện-tại-known-limitations"></a>14.2. Các hạn chế kỹ thuật hiện tại (Known Limitations)

1. **Chất lượng siêu dữ liệu nguồn DataHub**: Một số bảng từ hệ thống legacy trong DataHub chưa được cập nhật đầy đủ trường `description` và `owner`, dẫn đến việc kiểm tra chất lượng dữ liệu trả về trạng thái WARNING hoặc FAILED (khoảng trống từ dữ liệu catalog gốc).
2. **Lineage ở mức bảng (Table-level)**: Hệ thống hiện tập trung hỗ trợ Table-level Lineage; Column-level Lineage trên các Dashboard PowerBI phức tạp chưa được hỗ trợ toàn diện.
3. **Chỉ số Faithfulness của LLM**: Điểm Faithfulness ban đầu đạt 0.524 trên tập 34 ca đánh giá mẫu; cần tiếp tục tinh chỉnh prompt và tối ưu ngữ cảnh chunk.
4. **Giới hạn nhận diện từ hình ảnh (Vision Pipeline)**: Độ chính xác nhận diện tên thực thể từ ảnh chụp phụ thuộc vào độ phân giải và chất lượng hình ảnh đầu vào; hiện chưa có benchmark định lượng riêng biệt.
5. **Giới hạn bóc tách tài liệu phức tạp**: Quy trình bóc tách tài liệu hiện tối ưu cho PDF, DOCX, HTML dạng văn bản tiêu chuẩn; chưa hỗ trợ toàn diện bảng biểu lồng nhau hoặc sơ đồ nhúng phức tạp.

---

### <a id="143-các-bước-phát-triển-tiếp-theo-future-next-steps"></a>14.3. Các bước phát triển tiếp theo (Future Next Steps)

- **Mở rộng Đánh giá RAGAS**: Tự động hóa tính toán 4 chỉ số RAGAS trên toàn bộ tập dữ liệu tương tác để nâng cao độ tin cậy thống kê.
- **Nâng cao Entity Resolution**: Bổ sung bộ từ điển đồng nghĩa (Synonyms Dictionary) theo đặc thù từng khối nghiệp vụ doanh nghiệp.
- **Hoàn thiện Lineage cấp cột (Column-level)**: Mở rộng phân tích dòng chảy dữ liệu chi tiết tới từng trường thông tin cho các mô hình dữ liệu lớn.
- **Tự động hóa phản hồi chuyên gia**: Chuyển các ca gán nhãn lỗi từ Human Review trực tiếp thành các test case hồi quy trong CI/CD pipeline.

---

## <a id="15-kết-luận--bảng-truy-vết-nguồn-gốc"></a>15. KẾT LUẬN & BẢNG TRUY VẾT NGUỒN GỐC

### <a id="151-kết-luận"></a>15.1. Kết luận

Hệ thống **V-DataAtlas** đã triển khai và xác thực các chức năng cốt lõi phục vụ tra cứu, phân tích tác động, hiển thị dòng chảy dữ liệu, kiểm tra chất lượng và hỗ trợ sinh SQL trên danh mục **9,067 thực thể catalog**, **21,196 vector chunks** và **884 quy tắc phân quyền ACL**. Kiến trúc phân tách rõ ràng giữa truy xuất siêu dữ liệu cấu trúc và tổng hợp ngữ nghĩa giúp đảm bảo tính chính xác của dữ liệu kỹ thuật, tạo nền tảng vững chắc để tiếp tục mở rộng đánh giá qua RAGAS và thẩm định chuyên gia trong các giai đoạn vận hành tiếp theo.

---

### <a id="152-bảng-truy-vết-nguồn-gốc-kỹ-thuật"></a>15.2. Bảng truy vết nguồn gốc kỹ thuật

| Nội Dung Khẳng Định | Nguồn Dữ Liệu / Mã Nguồn Đối Chiếu |
|---|---|
| **9,067 Entities Catalog** | PostgreSQL `SELECT count(*) FROM entities` (8,542 dataset, 327 dashboard, 177 term, 21 node) |
| **21,196 Vector Chunks** | PostgreSQL `SELECT count(*) FROM entity_chunks` & OpenSearch Index `datahub-rag-chunks-v1` |
| **884 Entity ACLs & 5 Roles** | Bảng PostgreSQL `entity_acls`, `rbac_roles`, `rbac_role_domains` |
| **1,037 Interaction Logs** | Bảng PostgreSQL `interaction_logs` |
| **459 Unit Tests Passed** | Lệnh kiểm thử tự động `.venv/bin/pytest tests/unit tests/thinking` |
| **QuerySpec & Entity Resolver** | File mã nguồn `retrieval/query_spec.py`, `retrieval/entity_resolver.py` |
| **6 Actions & Comparison Flow** | File mã nguồn `app/services/chat_service.py`, `app/services/action_service.py` |
| **Phân quyền RBAC & ACL Filters**| File mã nguồn `app/auth/authorization.py`, `app/auth/rbac.py` |
| **Tích hợp DataHub GraphQL** | File mã nguồn `ingestion/graphql_source.py`, `ingestion/graphql/queries.py` |

---

## <a id="phụ-lục-a-technical-postmortem-log-lỗi-đã-xử-lý"></a>PHỤ LỤC A: TECHNICAL POSTMORTEM LOG (LỖI ĐÃ XỬ LÝ)

Bảng tổng hợp các vấn đề kỹ thuật đã được phát hiện và xử lý trong quá trình phát triển:

| STT | Hiện Tượng Lỗi | Vị Trí Mã Nguồn | Nguyên Nhân Gốc | Giải Pháp Đã Xử Lý |
|---|---|---|---|---|
| **1** | Lỗi gọi sai thuộc tính `Candidate.display_name` | `app/services/chat_service.py` | Class Candidate chỉ định nghĩa thuộc tính `name` | Đổi thành `best.name` kèm fallback `getattr()` |
| **2** | Lỗi truy cập thuộc tính `Entity.owners` | `app/services/chat_service.py` | Bảng entities lưu trữ metadata trong cột JSON `payload` | Đọc an toàn từ `payload.get("owner")` |
| **3** | Lỗi gọi sai tên phương thức `add_turn_db` | `app/services/chat_service.py` | Class ConversationMemory định nghĩa phương thức `add_turn` | Đồng bộ lại phương thức gọi thành `memory.add_turn()` |
| **4** | Lỗi truyền tham số `system=` vào LLM | `app/services/chat_service.py` | `FireworksLLM.generate()` chỉ nhận một tham số prompt | Gộp System Prompt vào đầu chuỗi prompt trước khi gửi |
| **5** | Lỗi UI tự render Lineage Graph rỗng | `frontend/components/chat/message-bubble.tsx` | Điều kiện kiểm tra lỏng lẻo dựa trên từ khóa trong text | Chỉ render khi có cờ `selected_action === "lineage"` |
| **6** | Lỗi hiển thị URN `:li:` thành cờ 🇱🇮 | `frontend/components/chat/markdown.tsx` | Mã `:li:` trùng emoji shortcode của cờ Liechtenstein | Bọc backticks URN và thêm hàm `sanitizeUrnMarkdown` |

---

## <a id="phụ-lục-b-danh-mục-api-hệ-thống"></a>PHỤ LỤC B: DANH MỤC API HỆ THỐNG

| Phương Thức | Endpoint URL | Mục Đích Sử Dụng | Yêu Cầu Xác Thực |
|---|---|---|---|
| **POST** | `/api/v1/auth/login` | Đăng nhập hệ thống, cấp JWT Token | Public |
| **POST** | `/api/v1/chat` | Gửi câu hỏi chat (phản hồi JSON) | Bearer JWT Token |
| **POST** | `/api/v1/chat/stream` | Gửi câu hỏi chat (phản hồi SSE Stream) | Bearer JWT Token |
| **GET** | `/api/v1/search` | Tìm kiếm thực thể lai (BM25 + Vector) | Bearer JWT Token |
| **GET** | `/api/v1/glossary/terms` | Danh sách thuật ngữ nghiệp vụ | Bearer JWT Token |
| **POST** | `/api/v1/sync/full` | Đồng bộ toàn bộ dữ liệu từ DataHub | Admin Role |
| **POST** | `/api/v1/actions/sql` | Sinh câu lệnh SQL theo schema | Bearer JWT Token |
| **POST** | `/api/v1/actions/lineage` | Tra cứu dòng chảy dữ liệu thực thể | Bearer JWT Token |
| **POST** | `/api/v1/actions/quality` | Kiểm tra chất lượng siêu dữ liệu | Bearer JWT Token |
| **POST** | `/api/v1/actions/quality/export` | Xuất báo cáo chất lượng dữ liệu PDF/TXT | Bearer JWT Token |
| **POST** | `/api/v1/actions/impact` | Đánh giá tác động hạ nguồn | Bearer JWT Token |
| **POST** | `/api/v1/actions/report` | Xuất báo cáo đặc tả siêu dữ liệu | Bearer JWT Token |
| **GET** | `/health` | Kiểm tra trạng thái hoạt động hệ thống | Public |

---

## <a id="phụ-lục-c-mô-hình-dữ-liệu-cơ-sở-dữ-liệu-database-erd"></a>PHỤ LỤC C: MÔ HÌNH DỮ LIỆU CƠ SỞ DỮ LIỆU (DATABASE ERD)

```mermaid
erDiagram
    entities ||--o{ entity_chunks : "entity_id FK"
    entities ||--o{ index_jobs : "by entity_urn"
    entities ||--o| entity_acls : "by entity_urn"
    rbac_roles ||--o{ rbac_role_domains : "role_id FK"
    rbac_roles ||--o{ rbac_user_roles : "role_id FK"
    rbac_users ||--o{ rbac_user_roles : "user_id"
    conversation_history }o--|| rbac_users : "user_id"
    image_records ||--o| vision_cache_records : "vision_cache_id"
    interaction_logs ||--o{ human_reviews : "interaction_id"
    human_reviews ||--o{ regression_candidates : "review_id"

    entities {
        int id PK
        string urn UK
        string entity_type
        string name
        string platform
        string domain
        json payload
        timestamp updated_at
    }

    entity_acls {
        int id PK
        string entity_urn UK
        boolean is_public
        array allowed_groups
        array denied_groups
        string classification
    }

    interaction_logs {
        int id PK
        string trace_id
        string user_id
        text question
        string intent
        text answer
        float faithfulness
        float answer_relevancy
        string evaluation_status
        timestamp created_at
    }

    human_reviews {
        int id PK
        int interaction_id FK
        string reviewer_id
        string overall_label
        string failure_stage
        text comment
        timestamp created_at
    }
```
