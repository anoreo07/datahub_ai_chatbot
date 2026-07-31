# System Architecture

> Kiến trúc tổng thể của AI Chatbot cho DataHub.
>
> Hệ thống gồm 5 tầng: **Presentation → Application → Retrieval → Data → Infrastructure**.
> Giao tiếp bất đồng bộ qua PostgreSQL job queue (index_jobs) và Redis cache.

```mermaid
flowchart LR

%% =====================================================
%% PRESENTATION LAYER
%% =====================================================
subgraph PRES["🌐 Presentation"]
    direction TB
    P1[Static HTML · app/static/index.html]
    P2[Nginx Reverse Proxy · security + rate limit]
end


%% =====================================================
%% AUTH LAYER
%% =====================================================
subgraph AUTH["🔐 Authentication & Authorization"]
    direction TB
    A1[IdentityProvider · Mock / Header / JWT]
    A2[AuthorizationService · ACL engine]
    A3[EntityAclDB · PostgreSQL-backed permissions]
    A4[AuditLog · all access decisions]
end


%% =====================================================
%% APPLICATION LAYER
%% =====================================================
subgraph APP["⚙️ Application · FastAPI"]
    direction TB

    subgraph API["API Endpoints"]
        EP1[POST /api/v1/chat]
        EP2[GET /api/v1/search]
        EP3[POST /api/v1/sync]
        EP4[POST /api/v1/index/rebuild]
        EP5[GET /health /metrics]
        EP6[GET /api/v1/documents /glossary]
    end

    subgraph SVC["Services"]
        S1[ChatService · orchestrator]
        S2[SyncOrchestrator · data sync]
        S3[IndexingPipeline · chunk + embed]
    end

    subgraph MID["Middleware"]
        M1[ErrorHandlingMiddleware]
        M2[MetricsMiddleware · Prometheus]
        M3[RateLimitMiddleware · Redis token bucket]
    end
end

P2 --> EP1 & EP2 & EP3 & EP4 & EP5 & EP6
EP1 & EP2 --> A2
A1 --> A2
A2 --> A3 & A4


%% =====================================================
%% RETRIEVAL LAYER
%% =====================================================
subgraph RET["🧠 Retrieval Layer"]
    direction TB
    R1[Intent Classifier · intent.py]
    R2[Entity Resolver · exact + fuzzy matching]
    R3[Hybrid Search · KNN + BM25]
    R4[Reranker · score normalization + fusion]
    R5[Context Builder · XML context assembly]
    R6[Citation Generator · source attribution]
    R7[Graph Expander · lineage + related entities]
    R8[Answer Generator · LLM call]

    R1 --> R2 & R3
    R3 --> R4
    R2 --> R4
    R4 --> R5
    R5 --> R6
    R6 --> R8
    R7 -.-> R5
end

S1 --> RET


%% =====================================================
%% DATA LAYER
%% =====================================================
subgraph DATA["💾 Data Layer"]
    direction TB

    subgraph PG["PostgreSQL"]
        D1[(entities · sync source)]
        D2[(entity_chunks · indexed content)]
        D3[(index_jobs · pending/completed)]
        D4[(sync_checkpoints · cursor)]
        D5[(audit_logs · access trail)]
        D6[(entity_acls · permissions)]
    end

    subgraph OS["OpenSearch"]
        D7[(dense_vector · 384d embeddings)]
        D8[(text + metadata · hybrid search)]
    end

    subgraph RC["Redis"]
        D9[(search_cache · TTL 300s)]
        D10[(rate_limit buckets)]
    end
end

R3 -.-> D7 & D8
S1 -.-> D9
M3 -.-> D10


%% =====================================================
%% INGESTION LAYER
%% =====================================================
subgraph ING["📡 Ingestion Layer"]
    direction TB
    I1[DataHubSource · abstract]
    I2[GraphQLDataHubSource · scrollAcrossEntities]
    I3[MockDataHubSource · JSON fixtures]
    I4[Mappers · dataset/dashboard/glossary/document]
    I5[Document Parsers · PDF/DOCX/HTML + SSRF guard]
    I6[URL Builder · DataHub frontend links]
end

I1 --> I2 & I3
I2 --> I4
I4 --> I5
I4 --> I6
I2 -.->|GraphQL| DH[(🏢 DataHub GMS)]

S2 --> I1


%% =====================================================
%% WORKERS
%% =====================================================
subgraph WRK["⚡ Background Workers"]
    direction TB
    W1[SyncWorker · polls sync API]
    W2[IndexingWorker · polls index_jobs]
end

W1 --> S2
W2 --> S3
W2 -.-> D3


%% =====================================================
%% LLM LAYER
%% =====================================================
subgraph LLM["🤖 LLM Abstraction"]
    direction TB
    L1[LLMProvider · abstract]
    L2[FireworksProvider · DeepSeek v4 Flash]
    L3[OpenAIProvider · stub]
    L4[CohereProvider · stub]
    L5[BedrockProvider · stub]
    L1 --> L2
    L1 -.-> L3 & L4 & L5
end

R8 --> L2


%% =====================================================
%% INFRASTRUCTURE
%% =====================================================
subgraph INFRA["☸️ Infrastructure"]
    direction TB
    F1[Docker · compose.yaml]
    F2[Docker Compose · dev/test/staging]
    F3[Helm Chart · K8s deployment]
    F4[CI/CD · GitHub Actions]
end

S1 & S2 & S3 & W1 & W2 -.-> F1


%% =====================================================
%% CONNECTIONS
%% =====================================================
EP1 & EP2 & EP3 & EP4 & EP5 & EP6 -.- S1 & S2 & S3

S2 -.->|upsert| D1
S3 -.->|read + write| D1 & D2 & D3
S3 -.->|bulk upsert| D7 & D8


%% =====================================================
%% STYLING
%% =====================================================
style PRES fill:#e3f2fd,stroke:#1e88e5,color:#000
style AUTH fill:#fce4ec,stroke:#d81b60,color:#000
style APP  fill:#e8f5e9,stroke:#43a047,color:#000
style API  fill:#e3f2fd,stroke:#1976d2,color:#000
style SVC  fill:#e0f7fa,stroke:#00838f,color:#000
style MID  fill:#f3e5f5,stroke:#8e24aa,color:#000
style RET  fill:#e8eaf6,stroke:#3949ab,color:#000
style DATA fill:#fff8e1,stroke:#f9a825,color:#000
style PG   fill:#fce4ec,stroke:#c62828,color:#000
style OS   fill:#fff3e0,stroke:#ef6c00,color:#000
style RC   fill:#f3e5f5,stroke:#6a1b9a,color:#000
style ING  fill:#e0f7fa,stroke:#00695c,color:#000
style WRK  fill:#e0f2f1,stroke:#00796b,color:#000
style LLM  fill:#f3e5f5,stroke:#6a1b9a,color:#000
style INFRA fill:#fafafa,stroke:#616161,color:#333
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI + Uvicorn | REST endpoints, async |
| **Auth** | PyJWT + custom IdentityProvider | JWT / Header / Mock modes |
| **Database** | PostgreSQL 16 + asyncpg | Entity store, jobs, audit |
| **Vector** | OpenSearch 2.15 | Dense vectors (384d) + BM25 |
| **Cache** | Redis 7 | Search cache, rate limiting |
| **LLM** | Fireworks AI (DeepSeek v4 Flash) | Answer generation |
| **Sync** | DataHub GraphQL API (`scrollAcrossEntities`) | Entity ingestion |
| **Monitoring** | Prometheus + structlog | Metrics + structured logging |
| **Orch** | Docker Compose + Helm | Local dev → K8s production |

## Component Responsibilities

| Component | Responsible For |
|-----------|----------------|
| `ChatService` | Orchestrate retrieval → generation → response |
| `SyncOrchestrator` | Pull entities from DataHub, upsert to DB |
| `IndexingPipeline` | Chunk entities, generate embeddings, index to OpenSearch |
| `HybridSearch` | KNN (α=0.6) + BM25 (1-α=0.4) fusion search |
| `EntityResolver` | Resolve entity name → exact URN via DB lookup |
| `AuthorizationService` | Check `can_view_entity`, build ACL filters |
| `IdentityProvider` | Authenticate user from JWT/header/mock |
| `DataHubSource` | Abstract interface for DataHub/mock data |
