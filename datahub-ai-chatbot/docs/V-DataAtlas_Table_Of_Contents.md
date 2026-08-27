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
