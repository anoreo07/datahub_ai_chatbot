# Báo Cáo Cải Tiến — DataHub AI Chatbot v02

## 1. Dữ Liệu DataHub

### 1.1. Tổng Quan Dữ Liệu

Trước v02, hệ thống chỉ có dữ liệu mock (5 datasets, 1 dashboard, vài glossary terms). v02 seeding 500 entities vào DataHub GMS qua GraphQL API:

| Loại | Số lượng | Chi tiết |
|------|----------|----------|
| Dataset | 228 | fact/dim/agg tables cho Sản Xuất, Bán Hàng, Hậu Mãi, Chuỗi Cung Ứng, Tài Chính |
| Dashboard | 91 | Power BI + Looker dashboards cho các phòng ban |
| Glossary Term | 181 | Định nghĩa nghiệp vụ (OEE, OTIF, Doanh thu, Tồn kho, ...) |
| Domain | 9 | Sản Xuất, Bán Hàng, Hậu Mãi, Chuỗi Cung Ứng, Tài Chính, ... |
| Tag | 20 | PII, Critical, Regulatory, Finance, Production, ... |

### 1.2. Quy Trình Seed Dữ Liệu

**Module:** `metadata_generator/`

```
metadata_generator/
├── config.py              # Cấu hình DataHub GMS URL + credentials
├── data/
│   ├── domains.py         # 9 domains
│   ├── tags.py            # 20 tags
│   ├── glossary.py        # 180 glossary terms (6 domains x 30 terms)
│   ├── datasets_batch1.py # 60 datasets: fact (SAP), dim (PostgreSQL), agg (materialized)
│   ├── datasets_batch2.py # 60 datasets: sản xuất + hậu mãi
│   ├── datasets_batch3.py # 60 datasets: chuỗi cung ứng + tài chính + bán hàng
│   ├── dashboards.py      # 90 dashboards: Power BI + Looker
│   └── lineage.py         # 26 lineage chains (fact → dim, agg → fact)
├── generators/
│   ├── domain.py          # POST /domains
│   ├── tag.py             # POST /tags
│   ├── glossary.py        # POST /glossaryTerms
│   ├── dataset.py         # POST /entities?action=upsert (dataset)
│   ├── dashboard.py       # POST /entities?action=upsert (dashboard)
│   └── lineage.py         # POST /relationships?relatedTypes=DataJobUpstreamLineage
└── main.py                # Orchestrator: chạy theo thứ tự dependency
```

Dữ liệu mô phỏng môi trường automotive manufacturing thực tế:
- **Sản Xuất (Production)**: `fact_oee_daily`, `dim_production_line`, `agg_line_utilization`
- **Bán Hàng (Sales)**: `fact_sales_daily`, `dim_dealer`, `agg_monthly_target`
- **Hậu Mãi (After Sales)**: `fact_as_warranty`, `fact_as_service`, `agg_service_csat`
- **Chuỗi Cung Ứng (Supply Chain)**: `fact_inventory`, `dim_supplier`, `agg_supplier_scorecard`
- **Tài Chính (Finance)**: `fact_finance_actuals`, `dim_cost_center`, `agg_spend_by_category`

### 1.3. Data Pipeline

```
DataHub GMS (seed từ metadata_generator/)
    ↓ full_sync (scripts/full_sync.py)
PostgreSQL Entity table (228 datasets, 91 dashboards, 181 terms)
    ↓ rebuild_index (scripts/rebuild_index.py)
OpenSearch index (datahub-rag-chunks-v1, 500 docs)
    ↓
Chatbot RAG pipeline
```

- **Sync pipeline**: Đọc entities từ DataHub GraphQL API → tính `content_hash` → upsert vào PostgreSQL
- **Index pipeline**: Load entities từ PostgreSQL → `build_chunks_for_entity()` → embed → bulk upsert vào OpenSearch
- **Mỗi entity sinh nhiều chunks**: dataset → summary + schema_fields + upstream_lineage + downstream_lineage

---

## 2. Nhận Diện Intent

### 2.1. Danh Sách Intent Hỗ Trợ

| # | Intent | Ví dụ | Cơ chế |
|---|--------|-------|--------|
| 1 | TERM_DEFINITION | "OEE là gì" | EntityResolver → glossary_term lookup |
| 2 | OWNER_LOOKUP | "Ai sở hữu fact_oee_daily" | EntityResolver → entity payload → owners |
| 3 | TERM_TO_DATASETS | "Dataset nào gắn term OEE" | EntityResolver + DB filter by glossary_terms |
| 4 | LINEAGE | "fact_oee_daily lấy dữ liệu từ đâu" | EntityResolver → payload upstreams |
| 5 | SCHEMA_LOOKUP | "fact_oee_daily có những field nào" | EntityResolver → payload schema_fields |
| 6 | DATAHUB_URL | "Link fact_oee_daily trên DataHub" | EntityResolver → datahub_url |
| 7 | ENTITY_EXISTS | "Dataset fact_oee_daily có tồn tại không" | EntityResolver |
| 8 | DOCUMENT_QA | "Tài liệu nói gì về OEE" | HybridSearch (document chunks) |
| 9 | LISTING | "có các dataset gì" | Listing detection → PostgreSQL list_by_type |
| 10 | GENERAL | "OEE hôm nay là bao nhiêu" | HybridSearch → OpenSearch |
| 11 | GREETING | "Xin chào" | Hardcoded responses |
| 12 | CHITCHAT | "Cảm ơn" | Hardcoded responses |

### 2.2. Intent Classification Engine

**File:** `retrieval/intent.py`

Rule-based classification với 2 lớp pattern (Vietnamese raw + ASCII-folded):

```python
_RULES = [
    (r"(nghĩa|là gì|định nghĩa|definition)", TERM_DEFINITION),
    (r"(ai sở hữu|owner|của ai)", OWNER_LOOKUP),
    (r"(field|column|schema|cột|trường)", SCHEMA_LOOKUP),
    (r"(upstream|downstream|lineage|nguồn|phụ thuộc)", LINEAGE),
    ...
]
_RULES_ASCII = [(re.compile(_norm_vn(p)), intent) for p, intent in ...]
```

Xử lý anaphora: Khi câu hỏi chứa "đó", "nó", "ấy", "này", hệ thống tự động infer entity từ lịch sử hội thoại và route đến intent phù hợp.

### 2.3. Intent Mới: LISTING

**Phát triển hoàn toàn mới trong v02.**

Pattern-based detection với `^...$` anchors:

```python
_LISTING_PATTERNS = [
    r'^(?:có các|các)\s+(dataset|dashboard|glossary)\s+(?:gì|nào)\??$',
    r'^liệt kê\s+(?:các\s+)?(dataset|dashboard|glossary)\s*$',
    r'^list\s+(?:all\s+)?(datasets|dashboards|glossary\s+terms)\s*$',
    ...
]
```

**Cơ chế:** Bypass LLM hoàn toàn, sinh câu trả lời local từ PostgreSQL:

```
Có tổng cộng 228 datasets trong hệ thống.

aggregate: agg_contract_coverage, agg_daily_sales_by_model, ...
dimension: dim_customer, dim_dealer, dim_material, ...
fact: fact_as_quality_inspection, fact_oee_daily, ...
powerbi: pbi_dg_compliance, pbi_fin_ar, pbi_sc_supplier, ...
sap: aenr, fact_oee_daily, ...
```

**Kết quả:** Response time < 500ms (không gọi LLM), không timeout, không corrupt data.

---

## 3. Nhớ Context (Conversation Memory)

### 3.1. Kiến Trúc

**File mới:** `app/services/conversation.py`

```
ConversationMemory
├── In-memory dict: user_id → { conv_id → [(q, a), ...] }
└── DB persistence: ConversationHistory table (PostgreSQL)
    ├── user_id, conversation_id, role (user/assistant)
    ├── content, metadata (JSONB)
    └── created_at (indexed)
```

### 3.2. Load/Save History

```python
async def load_history_from_db(self, session, user_id, conv_id, limit=10):
    """Load recent conversation turns"""
    
async def add_turn_db(self, session, user_id, conv_id, question, answer):
    """Save turn to both memory and DB"""
```

### 3.3. Xử Lý Anaphora

Khi phát hiện từ chỉ định trong câu hỏi:

```python
_ANAPHORA = {"đó", "do", "nó", "no", "ấy", "ay", "này", "nay", "đây", "day", "kia"}
```

ChatService tự động:
1. `_infer_entity_from_history()` — trích xuất entity name từ history
2. Thử lần lượt các structured intent (OWNER_LOOKUP → SCHEMA_LOOKUP → LINEAGE → TERM_DEFINITION → ...)
3. Trả về kết quả đầu tiên có entities

### 3.4. Conversations API

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/api/v1/conversations` | Danh sách conversations của user |
| `POST` | `/api/v1/conversations` | Tạo conversation mới (trả về conversation_id) |
| `DELETE` | `/api/v1/conversations/{id}` | Xóa conversation |

Conversation ID được persist trong `localStorage` (frontend) để giữ context xuyên suốt.

---

## 4. Phân Quyền

### 4.1. Authentication

**JWT-based authentication** với 3 hardcoded accounts:

| User | Password | Role | Quyền truy cập |
|------|----------|------|----------------|
| admin | admin123 | Admin | Tất cả entities |
| finance | finance123 | Finance | Finance entities + public |
| logistics | logistics123 | Logistics | Logistics entities + public |

**File:** `app/auth/jwt.py`, `app/auth/identity.py`

- JWT token với expiry (24h)
- Password hashed với bcrypt
- Frontend gửi `Authorization: Bearer <token>` qua `authHeaders()`
- Auto-logout khi nhận HTTP 401

### 4.2. ACL Entity-Level Authorization

**File:** `app/auth/authorization.py`

**ACL Rules (seeded in-memory):**

| Entity URN pattern | Allowed groups |
|-------------------|----------------|
| `*:finance.*` | `finance-team`, `admin` |
| `*:logistic.*` | `logistics-team`, `admin` |
| `*:sales.*` | Public (all users) |
| `urn:li:glossaryTerm:doanh_thu` | `finance-team`, `admin` |
| `urn:li:dashboard:finance_dashboard` | `finance-team`, `admin` |

**AuthorizationService:**

```python
class AuthorizationService:
    async def can_view_entity(self, user: UserContext, urn: str) -> bool:
        if user.is_admin:
            return True
        # Check is_public → allowed groups → denied groups
        return has_access(user, self._get_acls(urn))
```

**Tích hợp vào ChatService:**

```python
if self._auth_service:
    filtered = []
    for r in results:
        if await self._auth_service.can_view_entity(user_ctx, r.urn):
            filtered.append(r)
    denied_count = total_before - len(filtered)
    results = filtered
```

Khi tất cả entities đều bị từ chối:
```
"Thông tin này không thể truy cập bởi phòng ban của bạn.
 Vui lòng đăng nhập bằng tài khoản có quyền truy cập phù hợp
 hoặc liên hệ quản trị viên để được cấp quyền."
```

### 4.3. Login UI

Frontend login overlay hiển thị trước khi vào chat. Có sẵn hướng dẫn tài khoản:
```
Admin:    admin / admin123
Finance:  finance / finance123
Logistics: logistics / logistics123
```

---

## 5. Cải Tiến Câu Trả Lời

### 5.1. System Prompt Tối Ưu

**File:** `llm/fireworks.py`

**Trước v02:**
```
"If you cannot answer from the context, say so clearly."
→ LLM trả về "Không có đủ thông tin" dù context có entity liên quan
```

**Sau v02:**
```
"If the context contains relevant entities, ALWAYS describe what information IS available"
"If the question asks for numbers/data values, explain that you have metadata definitions
 and structure but not actual values, then show related entities."
"Every important claim must reference a citation ID (e.g. [E1], [E2])."
```

**Ví dụ kết quả với câu hỏi "OEE hôm nay là bao nhiêu?":**
```
"Tôi có thông tin metadata về OEE (Overall Equipment Effectiveness) – đây là chỉ số đo lường
hiệu suất thiết bị, được theo dõi qua các dashboard trong lĩnh vực Sản Xuất. Cụ thể:
- Dashboard 'Sản Xuất - Theo Dõi OEE' [E1]: cung cấp chi tiết OEE với các thành phần
  availability, performance, quality theo dây chuyền và ca làm việc.
- Dashboard 'Sản Xuất - Tổng Quan Sản Xuất' [E2]: giám sát sản xuất thời gian thực..."
```
Confidence=high, insufficient_context=False.

### 5.2. Fallback Handler

**File:** `app/services/chat_service.py`

Trước v02: Khi `insufficient_context=True`, fallback append "Entity liên quan:\n- name1\n- name2" vào answer → duplicate với entities block trên frontend.

Sau v02: Bỏ fallback text append. Frontend render entities từ `data.entities` riêng biệt. Thêm filter `if d.entity_name` để loại bỏ entities tên rỗng (tránh hiển thị raw URN).

### 5.3. LLM Error Handling

**File:** `llm/generator.py`

| Tình huống | Xử lý |
|-----------|-------|
| LLM unavailable (no API key) | `format_fallback_answer(docs, query)` → mô tả entities từ context |
| LLM timeout/API error | Trả về "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời." |
| LLM trả về no-answer pattern | Confidence=low, insufficient_context=True |
| Listing query (233 datasets) | Bypass LLM, sinh câu trả lời local |

### 5.4. Dọn Dẹp Dữ Liệu Nhiễu

Xóa 6 corrupt entities khỏi PostgreSQL + OpenSearch:

| Entity | Vấn đề |
|--------|--------|
| `urn:li:glossaryNode:ClientsAndAccounts` | entity_type="dataset" sai, name rỗng |
| `SampleHdfsDataset` | Mock data còn sót |
| `SampleHiveDataset` | Mock data còn sót |
| `SampleKafkaDataset` | Mock data còn sót |
| `test.test_table` | Test data không domain |
| `New Document` | document entity với type=dataset |

Entity count giảm từ 505 → 500 (228 datasets, 91 dashboards, 181 glossary terms).

### 5.5. Search Quality

**Loại bỏ corrupt entry khỏi OpenSearch** giúp cải thiện chất lượng search. Trước đây corrupt entity `glossaryNode:ClientsAndAccounts` (entity_name rỗng, content="Dataset: .") luôn là top result cho mọi query vì từ "Dataset" match mọi content.

---

## 6. Kết Quả Kiểm Thử

| # | Query | Intent | Confidence | Kết quả |
|---|-------|--------|------------|---------|
| 1 | "có các dataset gì" | LISTING | high | 228 datasets theo platform |
| 2 | "có các dashboard gì" | LISTING | high | 91 dashboards (looker, powerbi) |
| 3 | "OEE là gì" | TERM_DEFINITION | high | Định nghĩa + citation |
| 4 | "fact_oee_daily là dataset gì" | GENERAL | high | Dataset SAP + owner + domain |
| 5 | "fact_oee_daily có những field nào" | SCHEMA_LOOKUP | low | Schema chưa sync được |
| 6 | "fact_oee_daily lấy dữ liệu từ đâu" | LINEAGE | high | Không có upstream |
| 7 | "OEE hôm nay là bao nhiêu" | GENERAL | high | Metadata available + entities |

---

## 7. Tồn Tại

1. **Schema fields chưa sync được**: `full_sync` không lấy schema_fields từ DataHub GraphQL (N+1 API calls issue). Cần implement `scrollAcrossEntities` với inline fragments.
2. **Embedder còn là mock**: Dùng hash-based deterministic thay vì semantic embedding. Cần tích hợp Ollama nomic-embed-text (đã cài đặt).
3. **ACL chưa persist**: Rules lưu in-memory, không sync từ DataHub. Cần bảng `entity_acls` trong PostgreSQL.
4. **Không streaming**: Chưa hỗ trợ streaming response cho UX tốt hơn.
5. **Incremental sync chưa hoàn thiện**: Module `sync/` còn ở dạng khung.
