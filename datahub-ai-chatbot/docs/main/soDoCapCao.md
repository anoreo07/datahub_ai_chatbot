# Sơ Đồ Kiến Trúc Cấp Cao (High-Level Architecture) V-DataAtlas

Tài liệu này mô tả sơ đồ kiến trúc cấp cao theo chuẩn Mermaid của hệ thống **V-DataAtlas (DataHub AI Chatbot)**, thể hiện luồng xử lý end-to-end từ Frontend Next.js, API Gateway FastAPI, ChatService Orchestrator, Retrieval Pipeline, Ingestion, LLM đến các kho lưu trữ PostgreSQL, OpenSearch và Redis.

---

## 1. Sơ Đồ Mermaid Kiến Trúc Tổng Quan Cấp Cao

```mermaid
graph TB
    %% ---------------------------------------------------------
    %% SUBGRAPH 1: FRONTEND LAYER (Next.js 16)
    %% ---------------------------------------------------------
    subgraph Frontend["Frontend Layer (Next.js 16 / React / Tailwind)"]
        UI["User Interface (Chat UI, Topbar, Sidebar, Admin Panels)"]
        TopBar["Topbar Toggle (Response Time, ThemeSwitcher)"]
        Hooks["Custom Hooks (useChat, useApp, useNotificationStore)"]
        SSE_Client["SSE Streaming Client (onToken, onStatus, onDone)"]
    end

    %% ---------------------------------------------------------
    %% SUBGRAPH 2: API GATEWAY LAYER (FastAPI)
    %% ---------------------------------------------------------
    subgraph APILayer["API & Auth Layer (FastAPI Gateway)"]
        Endpoints["API Endpoints (/api/v1/chat/stream, /conversations, /health, /documents, /glossary)"]
        AuthDep["Authentication Dependency (JWT / Header / Mock -> UserContext)"]
        Middleware["Middleware (Rate Limit, Error Handler, Metrics)"]
    end

    %% ---------------------------------------------------------
    %% SUBGRAPH 3: CORE SERVICE ORCHESTRATOR
    %% ---------------------------------------------------------
    subgraph CoreOrchestrator["Core Service Orchestrator (ChatService)"]
        ReqPostProc["_t_start Timing & _postprocess_response Wrapper"]
        Guardrails["Guardrails (Prompt Injection Check, Scope Restriction)"]
        IntentRouter["Intent Classifier & Query Intent Router (42 Intents)"]
        QU["Query Understanding (LLM QU Engine + Validator)"]
        RBACGate["Domain RBAC Gate (AuthorizationService)"]
    end

    %% ---------------------------------------------------------
    %% SUBGRAPH 4: RETRIEVAL & METADATA INTELLIGENCE PIPELINE
    %% ---------------------------------------------------------
    subgraph RetrievalPipeline["Retrieval & Metadata Intelligence Pipeline"]
        MetadataEngine["Metadata Filter Engine (Domain, Tag, Owner, Platform, Certified)"]
        EntityResolver["Entity Resolver (Fuzzy Name Matcher & URN Resolver)"]
        HybridSearch["Hybrid Search (OpenSearch BM25 + Vector RRF)"]
        Reranker["Reranker (Semantic + Graph + Metadata Scoring)"]
        LineageService["Lineage Builder (Upstream, Downstream, Impact Analysis)"]
    end

    %% ---------------------------------------------------------
    %% SUBGRAPH 5: DATAHUB INGESTION & SYNC LAYER
    %% ---------------------------------------------------------
    subgraph IngestionLayer["DataHub Ingestion & Sync Layer"]
        SyncOrchestrator["SyncOrchestrator (Incremental Sync & Event Handler)"]
        GQLSource["GraphQLSource (scrollAcrossEntities Cursor Query & Fragments)"]
        DocParsers["Document Parsers (PDF PyMuPDF, DOCX, HTML + SSRF Guard)"]
        EntityMappers["Entity Mappers (Dataset, Dashboard, Glossary, Document)"]
    end

    %% ---------------------------------------------------------
    %% SUBGRAPH 6: LLM & GENERATION LAYER
    %% ---------------------------------------------------------
    subgraph LLMLayer["LLM & Generation Layer"]
        LLM_Registry["LLM Registry & Provider Selector"]
        FireworksProvider["Fireworks AI API (Primary LLM)"]
        OllamaProvider["Ollama / NVIDIA / Mock LLM (Fallback Provider)"]
        AnswerGenerator["Answer Generator (Streaming Token Yield & Citations)"]
    end

    %% ---------------------------------------------------------
    %% SUBGRAPH 7: DATA & INFRASTRUCTURE LAYER
    %% ---------------------------------------------------------
    subgraph Infrastructure["Data & Infrastructure Layer"]
        PostgreSQL[("PostgreSQL 16 DB\n- ConversationHistory (render_state)\n- EntityAclDB (ACLs)\n- InteractionLog")]
        OpenSearch[("OpenSearch 2.15 Vector Index\n- RAG Chunk Vectors (768d)\n- BM25 Full-text Index")]
        Redis[("Redis 7 Cache & Queue\n- Conversation State\n- Distributed Locks & DLQ")]
        OllamaEmbed["Ollama Embedding Service (nomic-embed-text 768d)"]
    end

    %% ---------------------------------------------------------
    %% CONNECTIONS & DATA FLOW
    %% ---------------------------------------------------------
    UI --> TopBar
    UI --> Hooks
    Hooks --> SSE_Client
    SSE_Client -- "HTTP POST SSE Stream" --> Endpoints

    Endpoints --> AuthDep
    Endpoints --> Middleware
    AuthDep --> CoreOrchestrator

    ReqPostProc --> Guardrails
    Guardrails --> RBACGate
    RBACGate --> IntentRouter
    IntentRouter --> QU

    IntentRouter -- "Metadata Listing Query" --> MetadataEngine
    IntentRouter -- "Entity Lookup" --> EntityResolver
    IntentRouter -- "Semantic / Context Query" --> HybridSearch
    IntentRouter -- "Lineage / Impact Request" --> LineageService

    HybridSearch --> Reranker
    Reranker --> AnswerGenerator

    AnswerGenerator --> LLM_Registry
    LLM_Registry --> FireworksProvider
    LLM_Registry --> OllamaProvider

    MetadataEngine --> PostgreSQL
    EntityResolver --> PostgreSQL
    HybridSearch --> OpenSearch
    HybridSearch --> OllamaEmbed
    LineageService --> PostgreSQL

    SyncOrchestrator --> GQLSource
    SyncOrchestrator --> DocParsers
    GQLSource --> EntityMappers
    EntityMappers --> PostgreSQL
    EntityMappers --> OpenSearch

    CoreOrchestrator -- "Save persistent render_state & response_time_ms" --> PostgreSQL
    CoreOrchestrator -- "Cache & Locks" --> Redis
    AnswerGenerator -- "Stream SSE Tokens" --> SSE_Client
```

---

## 2. Mô Tả Luồng Xử Lý Cấp Cao (Execution Flow)

1. **Frontend Request & Topbar Toggle**:
   - Người dùng tương tác trên giao diện Next.js 16. Nút toggle **Response Time** trên Topbar quản lý state `showResponseTime` (lưu persistent tại `localStorage`).
   - Khi gửi câu hỏi, `useChat` hook thực hiện kết nối HTTP SSE Stream tới API Gateway.

2. **API & Authentication Layer**:
   - FastAPI nhận request tại `/api/v1/chat/stream`.
   - Dependency `get_current_user` xác thực JWT Token / Header và inject đối tượng `UserContext` vào `ChatService`.

3. **ChatService Orchestrator & Timing**:
   - `_t_start = time.perf_counter()` bắt đầu bấm giờ request.
   - Kiểm tra Guardrails (Prompt Injection & Scope Restriction).
   - Kiểm tra quyền truy cập **Domain RBAC Gate** (`AuthorizationService`).
   - Phân loại ý định **Intent Classification** (42 intents).

4. **Retrieval & Metadata Intelligence**:
   - Tùy theo Intent, truy vấn điều hướng qua:
     - **Metadata Filter Engine**: Lọc SQL trực tiếp theo Domain, Tag, Owner, Platform, Certified.
     - **Entity Resolver**: Khớp tên mờ (Fuzzy) hoặc mã URN.
     - **Hybrid Search**: Kết hợp OpenSearch BM25 + Vector Embeddings qua Reciprocal Rank Fusion (RRF).
     - **Lineage Builder**: Xây dựng cây dòng chảy Upstream/Downstream và phân tích ảnh hưởng.

5. **LLM Streaming & SSE Response**:
   - **Answer Generator** gọi LLM (Fireworks AI / Ollama fallback) sinh phản hồi theo luồng token.
   - SSE Stream đẩy trực tiếp các event `status`, `token` về Frontend.

6. **Post-processing & Persistence**:
   - Khi hoàn tất, wrapper `_postprocess_response` tính toán chính xác tổng thời gian `response_time_ms = (t_end - t_start) * 1000`.
   - Ghi nhận `response_time_ms` cùng toàn bộ thuộc tính `render_state` vào bảng `ConversationHistory` trong PostgreSQL.
   - SSE phát event `done` chứa payload hoàn chỉnh về Client để render badge Response Time.
