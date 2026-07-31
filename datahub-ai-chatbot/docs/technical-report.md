# Tài Liệu Kỹ Thuật — DataHub AI Chatbot

## 1. Tổng Quan Dự Án

**DataHub AI Chatbot** là hệ thống chatbot tích hợp AI cho phép người dùng truy vấn metadata từ **DataHub** bằng ngôn ngữ tự nhiên. Hệ thống sử dụng kiến trúc **RAG (Retrieval-Augmented Generation)** để truy xuất ngữ cảnh từ kho dữ liệu metadata, sau đó sinh câu trả lời thông qua LLM.

Hệ thống hỗ trợ hai chế độ:
- **Mock mode**: Sử dụng dữ liệu fixture JSON, không cần DataHub thật — phục vụ phát triển và demo.
- **Production mode**: Kết nối DataHub thật qua GraphQL API.

---

## 2. Kiến Trúc Hệ Thống

![Kiến trúc hệ thống](../example_flow/architecture.png)

Hệ thống được tổ chức theo mô hình đa tầng (layered architecture) gồm 6 tầng chính:

| Tầng | Công Nghệ | Chức Năng |
|------|-----------|-----------|
| **Presentation** | HTML + Nginx | Giao diện người dùng, reverse proxy, rate limiting |
| **Application** | FastAPI + Uvicorn | REST API endpoints, xác thực, phân quyền |
| **Retrieval** | Python | Phân loại intent, truy xuất thực thể, hybrid search, rerank, context assembly |
| **LLM** | Fireworks AI (DeepSeek V4 Flash) | Sinh câu trả lời từ ngữ cảnh |
| **Data** | PostgreSQL + OpenSearch + Redis | Lưu trữ entity, vector embedding, cache |
| **Infrastructure** | Docker + Kubernetes + Terraform | Triển khai, giám sát, CI/CD |

### 2.1. Danh Sách Module Chính

| Module | Vị trí | Trách nhiệm |
|--------|--------|-------------|
| `ChatService` | `app/services/chat_service.py` | Điều phối toàn bộ luồng retrieval → generation → response |
| `IntentClassifier` | `retrieval/intent.py` | Phân loại câu hỏi thành 10 intent khác nhau |
| `EntityResolver` | `retrieval/entity_resolver.py` | Tra cứu entity theo tên/URN từ PostgreSQL |
| `HybridSearch` | `retrieval/hybrid_search.py` | Kết hợp KNN vector search + BM25 text search trên OpenSearch |
| `Reranker` | `retrieval/reranker.py` | Tính điểm và sắp xếp kết quả tìm kiếm |
| `ContextBuilder` | `retrieval/context_builder.py` | Xây dựng ngữ cảnh XML từ kết quả tìm kiếm |
| `AnswerGenerator` | `llm/generator.py` | Gọi LLM, parse kết quả JSON, validate citations |
| `FireworksLLM` | `llm/fireworks.py` | Triển khai LLM provider cho Fireworks AI |
| `MockLLM` | `llm/mock.py` | LLM giả lập cho môi trường phát triển |
| `SyncOrchestrator` | `ingestion/sync.py` | Đồng bộ entity từ DataHub về PostgreSQL |
| `IndexingPipeline` | `indexing/pipeline.py` | Chunk, embed, index entity lên OpenSearch |
| `AuthorizationService` | `app/auth/authorization.py` | Kiểm tra quyền truy cập entity-level |
| `IdentityProvider` | `app/auth/identity.py` | Xác thực người dùng (Mock / Header / JWT) |

### 2.2. Các Intent Được Hỗ Trợ

| # | Intent | Ví dụ câu hỏi |
|---|--------|---------------|
| 1 | TERM_DEFINITION | "Term Revenue nghĩa là gì?" |
| 2 | TERM_TO_DATASETS | "Dataset nào gắn term Customer?" |
| 3 | OWNER_LOOKUP | "Ai sở hữu dataset sales.orders?" |
| 4 | SCHEMA_LOOKUP | "Dataset sales.orders có những field nào?" |
| 5 | LINEAGE | "Dataset finance.monthly_revenue lấy dữ liệu từ đâu?" |
| 6 | FIND_ENTITY | "Report Monthly Revenue nằm ở đâu?" |
| 7 | DATAHUB_URL | "Cho tôi link DataHub của dataset sales.orders." |
| 8 | ENTITY_EXISTS | "Dataset abc.xyz có tồn tại không?" |
| 9 | DOCUMENT_QA | "Theo tài liệu, Net Revenue được tính như thế nào?" |
| 10 | GENERAL | Câu hỏi không khớp các intent trên |

---

## 3. Luồng Dữ Liệu

![Luồng dữ liệu](../example_flow/dataflow.png)

### 3.1. Sync Pipeline (DataHub → PostgreSQL → OpenSearch)

Đây là pipeline đồng bộ dữ liệu metadata từ DataHub về hệ thống:

```
SyncOrchestrator.run_full_sync()
    ↓
GraphQLDataHubSource / MockDataHubSource
    ↓ (scrollAcrossEntities cho từng entity type)
List entities: dataset, dashboard, glossary_term, document
    ↓
Tính content_hash cho từng entity
    ↓
content_hash thay đổi?
    ├── Yes → Upsert entity vào PostgreSQL → Tạo IndexJob (PENDING)
    └── No  → Bỏ qua (không thay đổi)
```

Indexing Worker chạy vòng lặp, poll các IndexJob PENDING:

```
IndexingWorker (poll mỗi 2 giây)
    ↓
IndexingPipeline.process_pending_jobs()
    ↓
Load entity từ PostgreSQL
    ↓
Build chunks theo entity type:
    ├── dataset     → summary_chunk + schema_chunk + lineage_chunk
    ├── dashboard   → summary_chunk
    ├── glossary    → definition_chunk
    └── document    → summary_chunk + page_chunks
    ↓
Generate embedding (MockEmbedder — hash-based deterministic)
    ↓
Bulk upsert vào OpenSearch (index: datahub-rag-chunks-v1)
    ↓
Save chunks vào PostgreSQL (entity_chunks table)
    ↓
Mark IndexJob COMPLETED
```

### 3.2. Query Pipeline (User Question → Answer)

```
User gửi POST /api/v1/chat {"question": "..."}
    ↓
FastAPI middleware stack:
    ├── ErrorHandlingMiddleware
    ├── MetricsMiddleware (Prometheus)
    └── RateLimitMiddleware
    ↓
Dependency Injection:
    ├── get_current_user → UserContext
    └── AuthorizationService
    ↓
ChatService.answer(question, user_context)
    ↓
Bước 1: Intent Classification
    classify_intent(question) → QueryIntent
    ↓
Bước 2: Routing theo Intent
    ├── Structured (TERM_DEFINITION, OWNER_LOOKUP, ...)
    │   └── EntityResolver.resolve() → DB lookup
    ├── General (GENERAL, DOCUMENT_QA)
    │   └── HybridSearch.search()
    │       ├── Entity Resolution (tên → URN)
    │       ├── KNN Vector Search (α = 0.6)
    │       └── BM25 Text Search (1 - α = 0.4)
    │       └── Fusion → top-50 results
    ↓
Bước 3: ACL Filtering
    AuthorizationService.filter_entities(results, user)
    ↓
Bước 4: Reranking
    Reranker.rerank(results) → top-K sorted by score
    ↓
Bước 5: Context Building
    build_context(results) → ContextDocument[] + context_xml
    ↓
Bước 6: Answer Generation
    AnswerGenerator.generate(context, intent)
        └── firewalls_llm.generate(prompt + context)
        └── Parse JSON structured answer
        └── build_citations() + validate
    ↓
Bước 7: Response Assembly
    ChatResponse:
        ├── answer: str
        ├── intent: QueryIntent
        ├── entities: List[EntityItem]
        ├── citations: List[CitationItem]
        ├── confidence: high|medium|low
        ├── ambiguous: bool
        ├── insufficient_context: bool
        └── trace_id: str
```

---

## 4. API Endpoints

| Method | Path | Mô tả | Xác thực |
|--------|------|-------|----------|
| `GET` | `/health` | Liveness probe | Không |
| `GET` | `/ready` | Readiness probe (kiểm tra Postgres, Redis, OpenSearch) | Không |
| `GET` | `/metrics` | Prometheus metrics | Không |
| `GET` | `/` | Static frontend (index.html) | Không |
| `POST` | `/api/v1/chat` | Gửi câu hỏi, nhận câu trả lời | Tùy chọn |
| `GET` | `/api/v1/search` | Hybrid search với filters | Tùy chọn |
| `POST` | `/api/v1/sync/full` | Kích hoạt full sync metadata | Tùy chọn |
| `POST` | `/api/v1/sync/entity` | Sync một entity theo URN | Tùy chọn |
| `POST` | `/api/v1/index/rebuild` | Rebuild OpenSearch index từ DB | Tùy chọn |
| `POST` | `/api/v1/documents/import` | Import document từ URL | Tùy chọn |
| `GET` | `/api/v1/glossary/terms` | Danh sách glossary terms | Tùy chọn |
| `GET` | `/api/v1/glossary/terms/{urn}` | Chi tiết glossary term | Tùy chọn |
| `GET` | `/api/me` | Thông tin user hiện tại (dev) | Bắt buộc |

---

## 5. Công Nghệ Sử Dụng

### 5.1. Backend

| Thành phần | Công nghệ | Phiên bản |
|------------|-----------|-----------|
| Ngôn ngữ | Python | 3.12+ |
| Web framework | FastAPI | (ASGI) |
| ASGI server | Uvicorn | — |
| Database ORM | SQLAlchemy | (async) |
| Database driver | asyncpg | — |
| Migration | Alembic | — |
| Validation | Pydantic v2 | — |
| Logging | Structlog | — |
| Auth | PyJWT | — |

### 5.2. Database & Cache

| Thành phần | Công nghệ | Phiên bản | Port (local) |
|------------|-----------|-----------|--------------|
| Metadata storage | PostgreSQL | 16 | 5433 |
| Vector + keyword search | OpenSearch | 2.x | 9201 |
| Cache + job queue | Redis | 7 | 6380 |

### 5.3. AI / ML

| Thành phần | Công nghệ |
|------------|-----------|
| LLM Provider | Fireworks AI (DeepSeek V4 Flash) |
| Embedding | MockEmbedder (hash-based deterministic) |
| LLM fallback | MockLLM (không cần API key) |
| Chưa triển khai | OpenAI, Cohere, AWS Bedrock |

### 5.4. Infrastructure & DevOps

| Thành phần | Công nghệ |
|------------|-----------|
| Containerization | Docker, Docker Compose |
| Orchestration | Kubernetes (Kustomize) |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |
| Logging | Loki |
| Tracing | OpenTelemetry |
| Reverse proxy | Nginx |

---

## 6. Cấu Trúc Cơ Sở Dữ Liệu

### 6.1. PostgreSQL Tables

| Bảng | Mục đích | Các cột chính |
|------|----------|---------------|
| `entities` | Lưu metadata entity | `urn` (PK), `entity_type`, `name`, `description`, `platform`, `domain`, `payload` (JSONB), `content_hash`, `created_at`, `updated_at` |
| `entity_chunks` | Lưu chunk dữ liệu | `id` (PK), `entity_urn` (FK), `chunk_type`, `content`, `metadata` (JSONB), `embedding_model`, `created_at` |
| `index_jobs` | Queue index job | `id` (PK), `entity_urn`, `status` (PENDING/PROCESSING/COMPLETED/FAILED), `attempts`, `error`, `created_at`, `updated_at` |
| `entity_acls` | ACL permissions | `id` (PK), `entity_urn` (unique), `is_public`, `allowed_user_ids` (ARRAY), `allowed_groups` (ARRAY), `denied_user_ids` (ARRAY), `denied_groups` (ARRAY), `classification` |
| `audit_logs` | Audit trail truy cập | `id` (PK), `user_id`, `entity_urn`, `action`, `granted`, `timestamp` |
| `sync_checkpoints` | Checkpoint đồng bộ | `id` (PK), `entity_type` (unique), `cursor`, `last_sync_at` |

### 6.2. OpenSearch Index

**Index name:** `datahub-rag-chunks-v1`

| Field | Type | Mục đích |
|-------|------|----------|
| `embedding` | `dense_vector` (384d) | Vector embedding cho KNN search |
| `entity_urn` | `keyword` | Entity identifier |
| `entity_type` | `keyword` | Entity type (dataset, dashboard, ...) |
| `chunk_type` | `keyword` | Loại chunk (summary, schema, ...) |
| `content` | `text` | Nội dung chunk |
| `platform` | `keyword` | Data platform |
| `domain` | `keyword` | Business domain |
| `is_public` | `boolean` | Public access flag |
| `name` | `text` | Tên entity |

Hybrid search sử dụng weighted fusion:
- KNN vector search: weight α = 0.6
- BM25 text search: weight 1 - α = 0.4

---

## 7. Triển Khai

### 7.1. Local Development

```bash
# Yêu cầu: Python 3.12+, Docker

cd datahub-ai-chatbot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Sửa .env nếu cần

docker compose up -d postgres redis opensearch
alembic upgrade head
python -m scripts.bootstrap

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2. Docker Compose (Full Stack)

```bash
docker compose up --build
```

Compose gồm 6 services:

| Service | Port | Mô tả |
|---------|------|-------|
| `api` | 8000 | FastAPI app (6 workers) |
| `sync-worker` | — | Sync worker (chạy full sync mỗi 3600s) |
| `indexing-worker` | — | Indexing worker (poll index_jobs mỗi 2s) |
| `postgres` | 5433 | PostgreSQL 16 |
| `redis` | 6380 | Redis 7 |
| `opensearch` | 9201 | OpenSearch 2.x |

### 7.3. Kubernetes (Production)

Kustomize base manifests tại `platform/kubernetes/`:

| Resource | Replicas | CPU/Memory (requests) |
|----------|----------|-----------------------|
| API Deployment | 2 | 500m / 512Mi |
| Worker Deployment | 1 | 250m / 256Mi |
| Sync CronJob | — | scheduled |
| HPA | — | auto-scale |
| Ingress | — | chatbot.example.com |

Overlays:
- **Staging**: Reduced replicas
- **Production**: Full replicas, production LLM config

---

## 8. Cấu Hình Môi Trường

Biến môi trường được quản lý qua `config/settings.py` (Pydantic BaseSettings).

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `USE_MOCK_DATAHUB` | `true` | Dùng mock data thay vì DataHub thật |
| `DATAHUB_GMS_URL` | — | URL DataHub GMS |
| `DATAHUB_TOKEN` | — | Token xác thực DataHub |
| `AUTH_MODE` | `mock` | Chế độ xác thực (mock / header / jwt) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Kết nối PostgreSQL |
| `REDIS_URL` | `redis://localhost:6380` | Kết nối Redis |
| `OPENSEARCH_URL` | `http://localhost:9201` | Kết nối OpenSearch |
| `EMBEDDING_PROVIDER` | `mock` | Embedding provider |
| `LLM_PROVIDER` | `fireworks` | LLM provider |
| `FIREWORKS_API_KEY` | — | API key Fireworks |
| `RATE_LIMIT_MAX_REQUESTS` | `100` | Max requests mỗi window |
| `CACHE_ENABLED` | `true` | Bật/tắt caching |
| `SYNC_INTERVAL_SECONDS` | `3600` | Chu kỳ sync (giây) |

---

## 9. Monitoring & Observability

### 9.1. Metrics (Prometheus)

| Metric | Type | Mô tả |
|--------|------|-------|
| `http_requests_total` | Counter | Tổng số request theo method, path, status |
| `http_request_duration_seconds` | Histogram | Phân phối thời gian response |
| `chat_requests_total` | Counter | Số chat request theo intent |
| `search_results_count` | Histogram | Số lượng kết quả search |
| `llm_call_duration_seconds` | Histogram | Thời gian gọi LLM |
| `llm_call_total` | Counter | Số lần gọi LLM (success/failure) |
| `sync_duration_seconds` | Histogram | Thời gian sync |
| `index_jobs_processed_total` | Counter | Số index job đã xử lý |

### 9.2. Logging (Structlog)

Cấu trúc log format JSON với các trường: `timestamp`, `level`, `event`, `logger`, `trace_id`, `user_id`, `request_id`.

### 9.3. Health Checks

- **Liveness** (`GET /health`): Trả về 200 nếu app đang chạy
- **Readiness** (`GET /ready`): Kiểm tra kết nối PostgreSQL, Redis, OpenSearch

---

## 10. Bảo Mật

- **Authentication**: Hỗ trợ 3 chế độ — Mock (dev), Header (proxy), JWT (production)
- **Authorization**: ACL entity-level với filter cho PostgreSQL và OpenSearch
- **SSRF Guard**: Bảo vệ SSRF khi import document từ URL
- **Rate Limiting**: Giới hạn request theo IP (in-memory)
- **Secrets**: Không log secrets; JWT secret key phải được cấu hình ở runtime
- **Audit**: Ghi lại tất cả quyết định truy cập vào `audit_logs`

---

## 11. Hạn Chế MVP

- **Mock embedder**: Deterministic hash-based, không phải semantic embedding
- **Fireworks**: LLM provider duy nhất được triển khai đầy đủ
- **Auth bypass**: `ChatService` hardcode `user_id = "local-developer"` ở một số chỗ
- **ACL chưa hoàn thiện**: ACL filtering chưa được tích hợp đầy đủ
- **Storage**: Local filesystem, chưa hỗ trợ S3/MinIO
- **OpenSearch**: Single-node, không yêu cầu k-NN plugin
- **No streaming**: Chưa hỗ trợ streaming responses
- **No conversation memory**: Mỗi request độc lập
- **Incremental sync**: Chưa hoàn thiện (module `sync/` còn ở dạng khung)

---

## 12. Evaluation

Hệ thống tích hợp evaluation framework (`evaluation/`) với:

- **Golden dataset**: 14 cặp Q&A mẫu bao phủ tất cả intent
- **Metrics**:
  - Entity recall: Tỷ lệ entity đúng được truy xuất
  - Answer accuracy: Độ chính xác câu trả lời
  - No-answer accuracy: Chính xác khi từ chối trả lời
  - Faithfulness: Độ trung thành với ngữ cảnh
  - Intent accuracy: Độ chính xác phân loại intent

```bash
python -m scripts.evaluate
```
