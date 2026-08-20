# Báo cáo công việc dự án DataAtlas

> Báo cáo tổng kết công việc đã thực hiện và kết quả đạt được của dự án DataAtlas (AI Chatbot cho DataHub).
> Mọi thông tin trong báo cáo đều được kiểm chứng từ source code, dữ liệu vận hành và kết quả test (thời điểm: 2026-08-18 → 19).

---

## 1. Các công việc đã hoàn thành

### 1.1. DataHub và dữ liệu

**Đã kết nối và khai thác metadata từ DataHub corporate qua GraphQL API**, xử lý được các khó khăn thực tế của hệ thống nguồn:

- Xây dựng client GraphQL chịu lỗi: retry với backoff, phát hiện WAF chặn, xử lý lỗi xác thực.
- Xây dựng công cụ pull metadata với checkpoint/resume, kéo được **45 MB dữ liệu, ~11.259 entity thuộc 12 loại** (dataset, dashboard, chart, container, data_flow, glossary, domain, platform, user, group, tag...).
- Đồng bộ vào hệ thống: **8.542 dataset, 327 dashboard, 177 glossary term, 21 glossary node** đã nạp vào cơ sở dữ liệu (tổng 9.067 entity), cùng 21.077 chunk đã index vào OpenSearch.
- Khai thác được các loại metadata: schema/field (233.345 field entries), lineage (upstream/downstream), glossary term kèm định nghĩa, domain, platform, owner, tags, chứng nhận (certified).
- Hỗ trợ cả **mock data source** (chạy không cần DataHub thật) và **real source**, giúp phát triển/test không phụ thuộc môi trường corporate.
- Bổ sung khả năng ingest tài liệu từ URL (PDF/DOCX/HTML) có kiểm soát an ninh mạng (chống SSRF).

### 1.2. AI Chatbot và Agent

**Đã hoàn thiện hệ thống hiểu câu hỏi và định tuyến theo intent** cho tiếng Việt:

- **Intent understanding**: bộ phân loại intent bằng quy tắc (~60 mẫu, hỗ trợ cả tiếng Việt không dấu) kết hợp phân loại ngữ nghĩa bằng LLM cho các trường hợp phức tạp; hỗ trợ trộn tín hiệu từ câu hỏi, lựa chọn thao tác (action menu) và lịch sử hội thoại.
- **Entity resolution**: nhận diện entity được nhắc đến (dataset, glossary term, dashboard...) với các mức khớp chính xác/chứa từ/gần đúng, nhận diện được tên bị gõ sai và đề xuất "Ý bạn là...".
- **Retrieval thông minh**: phân biệt câu hỏi metadata (trả lời trực tiếp từ dữ liệu đã sync) với câu hỏi tìm kiếm tổng hợp (đi qua RAG).
- **Thinking/Agent workflow**: chế độ suy luận (Thinking Mode) cho câu hỏi phức tạp — lập kế hoạch nhiều bước, thu thập bằng chứng từ nhiều nguồn, tổng hợp kết luận kèm lý do và rủi ro. Có cơ chế lập kế hoạch DAG cho câu hỏi tổng hợp nhiều entity.
- **Multi-turn context**: giữ ngữ cảnh giữa các lượt hỏi, hiểu được đại từ ("nó", "đó"), câu hỏi tiếp nối ("còn X thì sao?"), và câu hỏi tham chiếu kết quả trước ("field đó", "kết quả vừa rồi").
- **Evidence/citation**: mỗi câu trả lời bám vào metadata thực tế, có nguồn trích dẫn (E1, E2...), không bịa đặt.
- **Khả năng phân tích metadata**: sinh SQL an toàn (chỉ đọc, giới hạn trên schema thực), phân tích tác động khi thay đổi dataset (impact), báo cáo chất lượng dữ liệu (quality), so sánh schema giữa các dataset, phân tích join, định nghĩa term theo domain ("Demand" trong SẢN XUẤT khác "Demand" trong KINH DOANH), hiểu ý nghĩa cột từ tên trường.
- **Visual understanding**: phân tích ảnh chụp dashboard/ERD/bảng dữ liệu bằng vision model, nhận diện dataset trong ảnh và định tuyến câu hỏi về đúng entity đó.

### 1.3. Retrieval / RAG

**Đã xây dựng pipeline RAG hoàn chỉnh từ dữ liệu thô đến câu trả lời:**

- **Chuẩn hóa và chunk hóa**: mỗi entity được chuyển thành tài liệu có cấu trúc (summary, schema fields, lineage...) rồi cắt thành chunk phù hợp độ dài token, kèm metadata (domain, platform, owner, glossary terms, URL).
- **Embedding**: nhúng 768 chiều bằng model `nomic-embed-text` (qua Ollama), có mock embedder cho môi trường test.
- **Lưu trữ và tìm kiếm**: lưu song song vào PostgreSQL (chunk + metadata) và OpenSearch (chỉ mục kNN); tìm kiếm hybrid kết hợp **keyword (BM25) + vector (kNN)** với tỉ trọng 50/50.
- **Kết hợp retrieval với structured metadata**: phần lớn câu hỏi metadata (schema, owner, domain, lineage, term) được trả lời trực tiếp từ dữ liệu có cấu trúc thay vì vector search — đảm bảo chính xác và giảm chi phí LLM. Vector search chỉ dùng cho câu hỏi tìm kiếm/tổng hợp.
- **Reranking**: kết hợp nhiều tín hiệu (độ phù hợp retrieval, ngữ nghĩa, độ sâu trong graph lineage, độ giàu metadata, citation) để xếp hạng lại kết quả.
- **Context đưa vào LLM**: tối đa 8 chunk (~24.000 ký tự), được đóng gói kèm nguồn để LLM sinh câu trả lời có trích dẫn.

### 1.4. Context và Evidence

**Đã xây dựng cơ chế giữ ngữ cảnh và bằng chứng xuyên suốt hội thoại:**

- Hệ thống giữ **lịch sử hội thoại, entity đang quan tâm và kho bằng chứng (evidence)** cho từng phiên trò chuyện, lưu cả trong bộ nhớ và database.
- Mỗi lượt hỏi tự động ghi lại metadata đã lấy được dưới dạng evidence có đánh dấu (E1, E2, ...) — ví dụ: lấy schema xong thì ghi lại danh sách field.
- **Câu hỏi tiếp nối được trả lời từ evidence đã thu thập**, không tìm kiếm lại từ đầu. Ví dụ: hỏi "lấy schema của fact_inventory_movement" rồi hỏi tiếp "field warehouse_id kiểu gì?" — hệ thống trả lời từ schema đã lấy, đảm bảo đúng ngữ cảnh.
- Câu hỏi tham chiếu ngữ cảnh ("chỉ dựa trên metadata vừa lấy") được **ràng buộc trả lời chỉ từ dữ liệu đã thu thập**, không mở rộng tìm kiếm.
- **Citation**: câu trả lời LLM gắn nguồn trích dẫn (E1...) trỏ về entity/URN thật; có kiểm tra loại bỏ citation không có thật trong ngữ cảnh.
- Cơ chế này giúp **giảm việc tìm kiếm lại không cần thiết**, trả lời nhanh và nhất quán với ngữ cảnh hội thoại.

### 1.5. Refactor và cải thiện kiến trúc

**Đã tổ chức lại hệ thống backend từ kiến trúc cũ tập trung sang tách trách nhiệm rõ ràng:**

- **Vấn đề kiến trúc cũ**: service xử lý chat quá lớn, nhiều trách nhiệm lẫn nhau (định tuyến, retrieval, trả lời, evidence...), khó bảo trì và khó thêm tính năng mới.
- **Đã tách**: service chat trung tâm được phân chia thành các service chuyên trách — nhận diện entity, retrieval có cấu trúc, evidence, listing, lineage, các flow đặc thù (SQL/quality), kiểm soát truy cập domain, và xử lý ảnh — giao tiếp qua một context dùng chung.
- **Đã tách lớp** giữa các tầng: ingestion (lấy dữ liệu từ DataHub), indexing (chunk/embed/lưu trữ), retrieval (tìm kiếm/định tuyến), LLM (sinh câu trả lời), guardrails (chặn ngoài phạm vi, chống prompt injection, che secret).
- **Lợi ích**: mỗi thành phần có trách nhiệm rõ ràng, có test riêng, giảm rủi ro khi sửa đổi; các tính năng mới (evidence, thinking mode, vision, RBAC) được thêm vào như các lớp độc lập mà không phá vỡ luồng chính.

### 1.6. Backend / API

**Đã hoàn thiện các nhóm API phục vụ chatbot và quản trị dữ liệu:**

| Nhóm API | Chức năng chính |
|---|---|
| Chat | Trả lời câu hỏi, **streaming theo thời gian thực (SSE)**, gửi ảnh kèm câu hỏi, chọn model |
| Tìm kiếm | Hybrid search có lọc theo domain/platform/owner/tag, thống kê catalog |
| Actions | Sinh SQL, phân tích tác động (impact), lineage, báo cáo chất lượng dữ liệu (kèm export PDF/TXT), báo cáo metadata tổng hợp |
| Glossary | Danh sách và chi tiết glossary term |
| Hội thoại | Lịch sử trò chuyện, đổi tên, ghim, đánh dấu yêu thích |
| Admin | Quản lý roles/người dùng/phân quyền domain, đồng bộ dữ liệu (sync), rebuild index, kiểm tra sức khỏe DataHub |
| Documents | Import tài liệu từ URL |
| Storage | Quản lý ảnh đã upload (xem, tải, phân tích lại, xóa/khôi phục) |
| Vận hành | Health check các dịch vụ, metrics Prometheus |

**Bảo mật/xác thực**: xác thực JWT, phân quyền theo vai trò (admin/editor/steward/viewer/user), phân quyền theo domain (RBAC) kèm kiểm soát truy cập cấp entity (ACL), ghi log kiểm toán các quyết định chặn truy cập.

### 1.7. Frontend

**Đã xây dựng giao diện web hoàn chỉnh bằng Next.js/React**:

- **Chat interface** với streaming real-time, hiển thị trạng thái xử lý (đang phân tích intent, đang tìm kiếm, đang suy luận, đang sinh câu trả lời).
- **Citations** hiển thị dạng pill bấm được, danh sách entity liên quan kèm link DataHub.
- **Thinking Mode**: hiển thị trạng thái suy luận cho câu hỏi phức tạp.
- **Lineage graph** dạng SVG (upstream/downstream) trực quan.
- **Quality report card** hiển thị báo cáo chất lượng dữ liệu, có nút export PDF/TXT.
- **Search page** duyệt metadata với bộ lọc; **entities browser** duyệt theo loại; **glossary page** xem thuật ngữ.
- **Conversation history**: danh sách hội thoại, ghim, yêu thích, tìm kiếm, đổi tên.
- **Image upload**: chọn file hoặc dán từ clipboard, xem trước ảnh.
- **Authentication/RBAC**: trang đăng nhập, phân quyền hiển thị theo vai trò (trang admin/glossary chỉ cho người có quyền).

### 1.8. Testing và validation

**Đã xây dựng hệ thống test đầy đủ và toàn bộ đều PASS:**

- **Tổng cộng 620 test**, chia theo nhóm: unit (intent, entity resolution, retrieval, guardrails, sync, mappers, document parsers, auth...), context propagation, thinking mode, visual, integration (DB + OpenSearch + Redis), E2E (chat, RBAC, impact).
- **Kết quả**: `620 passed` — chạy lại toàn bộ thành công (2026-08-18).
- Các nhóm chức năng quan trọng được kiểm chứng bằng test chuyên biệt:
  - Context/evidence: 20 test về câu hỏi tiếp nối dựa trên evidence và ngữ cảnh field.
  - Thinking mode: 10 test về suy luận đa bước.
  - Visual: 60 test về phân tích ảnh.
  - ACL/RBAC: test tích hợp xác nhận bộ lọc truy cập hoạt động trên DB và OpenSearch.
  - SQL generation: 9 test tích hợp.
  - E2E chat: 14 test chạy cả quy trình đồng bộ dữ liệu + trả lời.
- **Evaluation framework**: bộ golden dataset (14 mẫu Q&A tiếng Việt), metrics đo độ chính xác (recall/precision entity, faithfulness, no-answer accuracy), script chấm điểm đa lượt (~35 case) qua API thật với 3 vai trò.
- **Benchmark độc lập trên 8.500+ dataset** (48 case): so với baseline, **pipeline pass tăng từ 7/48 (14.6%) lên 15/48 (31.3%)**, **0 test hồi quy** (+8 test được sửa); các chỉ số an toàn đạt mức cao: **không hallucination (0%), loại trừ dữ liệu ngoài quyền 100%, độ chính xác citation 85.4%, từ chối khi thiếu thông tin 87.5%, intent accuracy 93.8%**.
- **Lần đánh giá mới nhất** (19/08, `audit/final_metrics.json`): rich semantic pass đạt **31/48 (64.6%)**; intent accuracy **97.9%**, evidence grounding 72.9%, citation accuracy 79.2%, abstention accuracy 95.8%; **hallucination rate 0%, forbidden exclusion 100%**; same-term-different-domain 6/6, hard-negative 6/7, multi-hop 3/7.
- **Hạn chế của kết quả test (nêu rõ, không che giấu)**: các nhóm còn yếu gồm report/document discovery (3/8), glossary resolution thấp (~23%), raw-source resolution 0/2, multi-hop 3/7; hệ thống vẫn hay hỏi làm rõ khi gặp nhiều entity trùng khớp — chi tiết ở Mục 5.

### 1.9. Phân tích dữ liệu (EDA)

Đã tiến hành phân tích dữ liệu thực tế (Exploratory Data Analysis) trên toàn bộ dữ liệu đã đồng bộ từ DataHub — gồm cơ sở dữ liệu `entities`/`entity_chunks`, chỉ mục OpenSearch và dữ liệu raw đã pull — để hiểu rõ hiện trạng dữ liệu trước khi thiết kế retrieval và đánh giá.

**Tổng quan dữ liệu:**

| Loại entity | Số lượng | Ghi chú |
|---|---|---|
| dataset | 8.542 | Trọng tâm chính |
| dashboard | 327 | Power BI |
| glossary_term | 177 | Định nghĩa phong phú (2.4MB) |
| glossary_node | 21 | Nhóm Business Terms, KPI Logic |
| **Tổng đã load vào DB** | **9.067** | |
| chart / container / data_flow | 1.487 / 347 / 221 | Đã pull file nhưng **chưa load vào DB** |
| domain / tag / user / group | 9 / 5 / 32 / 5 | Đã pull file, chưa load |

**Phát hiện chính của EDA:**

- **Phân bố nền tảng không đồng đều**: 92% dataset thuộc 3 nền tảng lớn — powerbi (3.396), redshift (3.089), glue (1.336); phần còn lại trải rải rác ở ~20 nền tảng nhỏ (SAP 430, MES 141...).
- **Dữ liệu dirty**: cùng một nền tảng bị ghi nhiều tên khác nhau — `Salesforce`/`Saleforce`, `Excel`/`EXCEL`, `Qualtrics`/`Qualrics`, `JIRA`/`Jira` → cần chuẩn hóa khi xử lý.
- **Environment**: 100% dataset = `PROD` (không có DEV/QA/UAT).
- **Thiếu mô tả trầm trọng**: **91.8% dataset (7.838/8.542) không có description** — toàn bộ nhóm powerbi/redshift/glue/s3 (7.838 dataset) không có mô tả; chỉ các nền tảng nhỏ (SAP/MES/Excel...) có mô tả 100%.
- **Thiếu domain**: **88.8% dataset (7.581/8.542) chưa gán domain**; 8 domain còn lại gắn cho ~11% dataset (SẢN XUẤT 489, TÀI CHÍNH 201, KINH DOANH 92, CUNG ỨNG 65, LOGISTIC 47...). Glossary term cũng không có domain (0/177).
- **Schema khá đầy đủ**: 91.4% dataset có schema; tổng **233.345 field** (trung bình ~27 field/dataset, max 4.561 field); field có type, nullable, is_primary_key nhưng **không có** glossary term/tags gắn field-level.
- **Thiếu owner 100%**: 0/8.542 dataset có owner; dashboard cũng 0 owner.
- **Không có lineage**: 0 dataset có upstream/downstream; 0 dashboard có link tới dataset nguồn.
- **Liên kết dataset ↔ glossary gần như không tồn tại**: chỉ 20/8.542 dataset (0.2%) có glossary terms.
- **Ambiguity tên rất lớn**: **1.899 nhóm tên dataset trùng** (4.614 tên / 8.542 entity) — ví dụ `stas`/`stko` trùng tên giữa glue và redshift, `DIM_PACKED` ×21, `.Measure` ×11; family `fact_inventory*` có 129 biến thể; cùng một tên field xuất hiện ở hàng trăm dataset (`plant_id` ×892, `material_id` ×808).
- **Term trùng khái niệm, khác định nghĩa**: ví dụ `Coverage Date` có 2 URN với 2 định nghĩa khác nhau (inventory coverage vs working-day coverage); nhiều cặp term global vs `[VN]` (Dealer IN/OUT, Sell In/Out).

**Hàm ý thiết kế**: dữ liệu nguồn thiếu mô tả/domain/owner/lineage nên hệ thống phải (a) dựa chủ yếu vào tên dataset + schema field thay vì mô tả; (b) xử lý tốt ambiguity tên trùng bằng cơ chế hỏi làm rõ và lọc theo platform/domain; (c) trả lời thẳng thắn `UNKNOWN` cho owner/lineage/custom properties khi không có bằng chứng. Chi tiết đầy đủ trong `audit/data_landscape_audit.md`.

---

## 2. Kiến trúc hiện tại

Kiến trúc hiện tại được phân tầng rõ ràng:

```
Frontend (Next.js)
  ↓ chat/search/actions qua API
Backend / API (FastAPI)
  ↓
Chat / Agent Orchestration (định tuyến intent, chuỗi gate)
  ↓
Context & Evidence (lịch sử hội thoại, evidence E1..En, active entities)
  ↓
Retrieval / DataHub (structured metadata + hybrid search)
  ↓
LLM (sinh câu trả lời RAG)
```

- **Frontend**: giao diện chat và các trang quản trị; giao tiếp backend qua API, streaming qua SSE.
- **Backend/API**: lớp API FastAPI, xác thực JWT, phân quyền theo role + domain, chặn rate limit, ghi metrics.
- **Chat/Agent Orchestration**: trung tâm định tuyến — hiểu ý định câu hỏi, đi qua chuỗi các bước kiểm soát (scope, quyền truy cập domain, mức độ liên quan DataHub, ngữ cảnh trước đó, chế độ suy luận) trước khi quyết định cách trả lời.
- **Context & Evidence**: giữ lịch sử, entity đang quan tâm và bằng chứng đã thu thập để trả lời câu tiếp nối chính xác.
- **Retrieval/DataHub**: hai đường — truy vấn trực tiếp metadata có cấu trúc (schema/owner/lineage/term) và hybrid search (keyword + vector) trên OpenSearch.
- **LLM**: sinh câu trả lời tổng hợp có trích dẫn; LLM chỉ được dùng ở những chỗ có kiểm soát, không tự bịa metadata.
- **Storage**: PostgreSQL (metadata, chunk, RBAC/ACL, lịch sử), OpenSearch (vector + keyword index), Redis (cache, rate limit, hàng đợi), filesystem (tài liệu, ảnh).

---

## 3. Data Pipeline

```
DataHub (GraphQL)
  → Data ingestion (pull metadata, sync, normalize)
  → Database / Vector / Search (PostgreSQL + OpenSearch)
  → Retrieval (structured + hybrid)
  → Context & Evidence (gắn ngữ cảnh hội thoại)
  → LLM (sinh câu trả lời có trích dẫn)
  → Response (kèm citation/entity)
```

- **Data ingestion**: kéo metadata từ DataHub qua GraphQL (có checkpoint để tiếp tục khi gián đoạn), chuẩn hóa thành entity thống nhất, kiểm tra thay đổi bằng content hash để tránh index lại không cần thiết.
- **Database / Vector / Search**: metadata lưu ở PostgreSQL; mỗi entity được chunk hóa, nhúng vector và lưu song song vào PostgreSQL và OpenSearch (keyword + kNN) phục vụ tìm kiếm.
- **Retrieval**: với câu hỏi metadata cụ thể, truy vấn trực tiếp từ dữ liệu có cấu trúc; với câu hỏi tìm kiếm/tổng hợp, dùng hybrid search rồi xếp hạng lại.
- **Context & Evidence**: kết quả thu được mỗi lượt được ghi thành evidence; câu hỏi tiếp nối dùng lại evidence này.
- **LLM**: chỉ nhận context đã kiểm soát (tối đa 8 chunk), sinh câu trả lời bám vào nguồn, có trích dẫn và đánh giá độ tin cậy.
- **Response**: trả về câu trả lời kèm entity, citation, độ tin cậy, và đánh dấu trường hợp thiếu ngữ cảnh hoặc mơ hồ.

---

## 4. Kết quả đạt được

| Nhóm | Kết quả kiểm chứng |
|---|---|
| Dữ liệu | **9.067 entity** đã nạp (8.542 dataset, 327 dashboard, 177 glossary term, 21 glossary node); **21.077 chunk** đã index; 884 bản ghi ACL, 5 vai trò RBAC |
| Chat/Agent | Hỏi-đáp tiếng Việt cho schema, owner, domain, lineage, glossary, term→dataset, SQL, quality, impact, tìm kiếm; multi-turn + evidence; thinking mode; xử lý ảnh |
| Retrieval/RAG | Hybrid search (BM25 + vector) trên 21.077 chunk + truy vấn metadata có cấu trúc; reranking; citation có kiểm soát |
| Kiến trúc | Backend tách trách nhiệm rõ ràng; frontend Next.js hoàn chỉnh; phân quyền role + domain; vận hành (health, metrics, rate limit) |
| Testing | **620/620 test pass**; evaluation framework + benchmark; **0% hallucination, 100% loại trừ dữ liệu ngoài quyền** |
| Bảo mật | Xác thực JWT, RBAC domain, ACL entity, chống prompt injection, che secret, chặn SSRF, audit log |

**Các capability quan trọng hiện đã hoạt động**: hỏi-đáp metadata tiếng Việt chính xác theo từng field, định nghĩa term theo domain, lineage có sơ đồ trực quan, sinh SQL an toàn, báo cáo chất lượng dữ liệu, phân tích tác động, streaming real-time, hội thoại đa lượt giữ được ngữ cảnh, phân quyền dữ liệu theo domain.

---

## 5. Hạn chế hiện tại

> Chỉ nêu hạn chế đã xác định từ source code, test và dữ liệu vận hành.

- **Chất lượng metadata nguồn hạn chế**: 88.8% dataset chưa gán domain; trên 75% dataset không có mô tả (toàn bộ nhóm powerbi/redshift/glue/s3); không có glossary/tags gắn theo field; mô tả field thường trống. Hệ thống do đó phụ thuộc chủ yếu vào tên dataset và schema field.
- **Dữ liệu nguồn chưa sạch**: tên platform bị ghi không nhất quán (Salesforce/Saleforce, Excel/EXCEL...).
- **Chưa nạp hết dữ liệu đã pull**: 8 loại metadata (chart, container, data_flow, user, group, platform, tag, domain) đã kéo về nhưng chưa đưa vào database phục vụ chatbot.
- **Semantic precision chưa đạt mục tiêu**: rich semantic pass ở lần đánh giá mới nhất là **64.6% (31/48)**; các nhóm còn yếu: report/document discovery (3/8), glossary resolution thấp (~23%), raw-source resolution 0/2, multi-hop 3/7; hệ thống vẫn hay hỏi làm rõ thay vì chọn ứng viên rõ ràng nhất khi gặp nhiều entity trùng khớp.
- **Một số thành phần kỹ thuật còn tồn tại gap**: pagination qua scroll chưa được dùng cho luồng đồng bộ chính; một số luồng sync vẫn gọi API từng entity (N+1); 2 worker nền (document/embedding) chưa được triển khai thực chất; vài LLM provider (OpenAI/Cohere/Bedrock) mới chỉ là khung.
- **Một số điểm về chất lượng code**: README chưa cập nhật theo hiện trạng; có code trùng lặp nhỏ (metrics, schema); thông tin đăng nhập demo còn đặt trong code.

---

## 6. Công việc tiếp theo

`TODO — Project owner will define next steps.`
