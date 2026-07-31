# AGENTS.md — AI Chatbot for DataHub

## Tổng quan project

AI Chatbot cho DataHub với RAG pipeline. FastAPI backend, PostgreSQL, OpenSearch, Redis. Mock mode hoạt động không cần DataHub thật.

## Cấu trúc thư mục

```
datahub-ai-chatbot/
├── app/                    # FastAPI app
│   ├── api/                # Routers: chat, search, sync, health, metrics, documents, glossary, index, me
│   ├── auth/               # Authentication/Authorization: identity, jwt, models, authorization
│   ├── middleware/          # Error handler, metrics, rate limit
│   ├── schemas/            # Pydantic request/response models
│   ├── services/           # ChatService (orchestrator)
│   ├── static/             # Frontend HTML
│   └── main.py             # FastAPI app entry point
├── config/                 # Settings, constants, logging, prompts
├── database/               # SQLAlchemy models, session, repositories, migrations
├── ingestion/              # DataHub source abstraction
│   ├── mock_source.py      # Mock data source
│   ├── graphql_source.py   # Real DataHub GraphQL source
│   ├── graphql/            # GraphQL client + queries
│   ├── mappers/            # Entity mappers (dataset, dashboard, glossary, document)
│   ├── document_parsers/   # PDF, DOCX, HTML parsers + SSRF guard
│   └── sync.py             # SyncOrchestrator
├── indexing/               # Chunking, embedding, vector store, pipeline
├── retrieval/              # Intent classification, entity resolver, hybrid search, reranker, context, citation
├── llm/                    # LLM abstraction (Fireworks working; OpenAI/Cohere/Bedrock stubs)
├── workers/                # Background workers (sync, indexing, document, embedding)
├── sync/                   # Incremental sync, event handler, DLQ, retry, locks, consumer
├── evaluation/             # Golden dataset, evaluator, metrics
├── infrastructure/         # Redis, cache, storage
├── tests/                  # Unit, integration, e2e tests
├── deploy/                 # Docker Compose variants, Helm chart, nginx
└── scripts/                # Bootstrap, rebuild index
```

## Các vấn đề CRITICAL cần sửa

### 1. GraphQL pagination không hoạt động

**File:** `ingestion/graphql/queries.py` — `SEARCH_WITH_CURSOR_QUERY`

**Vấn đề:** Query `search` không hỗ trợ cursor pagination. Cursor parameter được gửi lên nhưng GQL `search` API của DataHub bỏ qua nó.

**Yêu cầu:** Thay thế bằng `scrollAcrossEntities` query hỗ trợ cursor:

```graphql
query scrollAcrossEntities($input: ScrollAcrossEntitiesInput!) {
  scrollAcrossEntities(input: $input) {
    nextScrollId
    count
    total
    searchResults {
      entity { urn type ... }
    }
  }
}
```

**File cần sửa:**
- `ingestion/graphql/queries.py` — Thêm `SCROLL_ACROSS_ENTITIES_QUERY`
- `ingestion/graphql_source.py` — Sửa `list_entities()` dùng scroll thay vì search
- `ingestion/mock_source.py` — Cập nhật `list_entities()` signature nếu cần

### 2. N+1 API calls trong GraphQL sync

**File:** `ingestion/graphql_source.py`

**Vấn đề:** `_list_type()` và `search_entities()` gọi `get_entity()` (1 GraphQL call) cho mỗi kết quả tìm kiếm. N+1 calls.

**Yêu cầu:** Sửa để search results trả về đủ dữ liệu để map thành `CanonicalEntity` mà không cần gọi `get_entity()` riêng lẻ. Dùng GraphQL fragments để lấy đủ field trong search result.

**Cách sửa:**
- Search query cần include inline fragments đủ field cho từng entity type
- Tạo `search_result_to_canonical()` để map từ search hit trực tiếp
- Chỉ gọi `get_entity()` khi cần detail đầy đủ (lineage, schema)

### 3. URN type routing sai

**File:** `ingestion/graphql_source.py` — `get_entity()` method (line 109-116)

**Vấn đề:** URN routing chỉ kiểm tra `dataset`, `glossaryTerm`, `dashboard`. Các type khác (chart, dataFlow, dataJob, container, tag, mlModel, v.v.) fallback thành `_get_dataset`.

**Yêu cầu:** Route đúng entity type dựa trên URN pattern:
- `:chart:` hoặc `:chart(` → graphQL `chart` query
- `:dataFlow:` → `dataFlow` query  
- `:dataJob:` → `dataJob` query
- `:container:` → `container` query
- `:tag:` → tag query
- `:mlModel:` → `mlModel` query
- v.v.

Hoặc dùng generic `search` với scroll để lấy entity data mà không cần type-specific query.

### 4. ACL filtering không hoạt động

**File:** `app/auth/authorization.py`

**Vấn đề:**
- `build_database_acl_filter()` và `build_opensearch_acl_filter()` luôn return `None` kể cả với non-admin users
- ACL chỉ lưu in-memory — không sync từ DataHub, không persist trong DB
- `ChatService.answer()` hardcode `user_id="local-developer"`

**Yêu cầu:**

a) **Persist ACL:** Tạo bảng `entity_acls` trong database:
```python
class EntityAclDB(Base):
    __tablename__ = "entity_acls"
    id: Mapped[int]
    entity_urn: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    is_public: Mapped[bool]
    allowed_user_ids: Mapped[list] = mapped_column(ARRAY(String))
    allowed_groups: Mapped[list] = mapped_column(ARRAY(String))
    denied_user_ids: Mapped[list] = mapped_column(ARRAY(String))
    denied_groups: Mapped[list] = mapped_column(ARRAY(String))
    classification: Mapped[str]  # internal, confidential, restricted
```

b) **Implement ACL filter cho Database:**
```python
async def build_database_acl_filter(self, user: UserContext):
    if user.is_admin:
        return None
    # WHERE clause: entity_urn NOT IN denied OR entity_urn IN allowed OR is_public
    # Complex logic cần raw SQL hoặc ORM expression
```

c) **Implement ACL filter cho OpenSearch:**
```python
async def build_opensearch_acl_filter(self, user: UserContext):
    if user.is_admin:
        return None
    return {
        "bool": {
            "should": [
                {"term": {"is_public": True}},
                {"terms": {"entity_urn": user_accessible_urns}},
            ]
        }
    }
```

d) **Wire ACL vào ChatService:**
- Nhận `UserContext` từ dependency injection thay vì hardcode
- Gọi `AuthorizationService.filter_entities()` hoặc build filter trước search
- Audit denied access

### 5. Auth bypass trong ChatService

**File:** `app/services/chat_service.py` (line 29)

**Vấn đề:** `answer()` method nhận `user_id: str = "local-developer"` hardcoded.

**Yêu cầu:** Thay đổi signature để nhận `UserContext` từ dependency injection, pass qua từ chat API endpoint.

**File cần sửa:**
- `app/api/chat.py` — Inject `get_current_user` dependency, pass user context vào `ChatService.answer()`
- `app/services/chat_service.py` — Sửa `answer()` nhận `UserContext`, dùng cho entity resolution filtering + audit

## Các vấn đề HIGH cần sửa

### 6. Docker build không nhất quán

**File:** `.github/workflows/ci.yml` references `platform/docker/chatbot.Dockerfile` nhưng root `Dockerfile` ở `datahub-ai-chatbot/Dockerfile`.

**Yêu cầu:** Đồng bộ Dockerfile paths trong CI workflow. Quyết định dùng root Dockerfile hoặc deploy/docker/Dockerfile và sửa CI tương ứng.

### 7. PDF parser missing dependency

**File:** `pyproject.toml` — thiếu `PyMuPDF` (fitz). `ingestion/document_parsers/pdf_parser.py` dùng `fitz` nhưng fallback silent thành latin-1 decode.

**Yêu cầu:** Thêm `PyMuPDF>=1.23.0` vào `pyproject.toml` dependencies.

### 8. Empty workers

**Files:** `workers/document_worker.py`, `workers/embedding_worker.py`

**Vấn đề:** Cả 2 worker đều là infinite loop không làm gì, nhưng được định nghĩa trong `compose.yaml`.

**Yêu cầu:**
- Nếu chưa implement: xóa khỏi `compose.yaml` và thêm TODO trong README
- Nếu muốn giữ: implement logic tối thiểu (ví dụ document worker poll Redis queue cho document ingestion jobs)

### 9. Hardcoded JWT secret

**File:** `config/settings.py` line 24 — `JWT_SECRET_KEY: str = "dev-secret"`

**Yêu cầu:** Không set default value cho JWT_SECRET_KEY. Raise error ở runtime nếu dùng JWT mode mà không set secret.

### 10. Index rebuild type error

**File:** `app/api/index.py` lines 26-32

```python
all_entities = await entity_repo.list_by_type("dataset")
for ent in await entity_repo.list_by_type("dashboard"):
    all_entities = list(all_entities) + [ent]
```

**Vấn đề:** `list_by_type` trả về `Sequence[Entity]`. Gán lần đầu là Sequence, sau đó cast thành list. Code lộn xộn.

**Yêu cầu:** Sửa thành list comprehension sạch:
```python
all_entities = []
for etype in ["dataset", "dashboard", "glossary_term", "document"]:
    all_entities.extend(await entity_repo.list_by_type(etype))
```

## Test

Sau mỗi fix:

```bash
# Kiểm tra import
python -c "from app.main import app; print('OK')"

# Unit tests
python -m pytest tests/unit -q --timeout=60

# Integration tests (cần postgres, redis, opensearch running)
python -m pytest tests/integration -q --timeout=120

# Lint
ruff check .

# Type check
mypy app ingestion indexing retrieval llm sync workers database config infrastructure
```
