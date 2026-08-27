# DataHub AI Chatbot

AI-powered conversational assistant and grounded intelligence layer for DataHub metadata catalogs. Provides natural language search, lineage analysis, SQL generation, schema comparisons, data quality audits, and role-based access control.

---

## Architecture Overview

```
User Query / Frontend
         │
         ▼
[FastAPI Gateway / Auth Middleware]
         │
         ├── JWT Authentication & User Context
         ├── RBAC & ACL Filters (Database / OpenSearch)
         │
         ▼
[Chat Orchestration Service]
         │
         ├── Query Understanding & Intent Classification
         ├── Entity Resolution & Disambiguation
         ├── Hybrid Search (BM25 + Semantic Embeddings)
         ├── Context Builder & Grounding Assembly
         │
         ├── Specialized Flows:
         │     ├── Action Services (SQL Gen, Schema Diff, Quality, Impact, Report)
         │     ├── Direct Field Operations & Glossary Resolvers
         │     └── Multi-Entity Comparison Flow
         │
         ▼
[LLM Generation Layer (Fireworks / Provider Fallback)]
         │
         ├── SSE Streaming / Token Dispatcher
         ├── Secret Sanitization & Citation Attribution
         ├── Conversation Memory & Render State Persistence
         │
         ▼
[Background Evaluation & Monitoring (RAGAS / Interaction Logs)]
```

### Core Pipelines

1. **Ingestion & Sync**: Pulls catalog entities (datasets, dashboards, glossary terms, containers, charts) via GraphQL API or mock fixtures into PostgreSQL.
2. **Indexing**: Parses entity payloads, builds normalized documents, chunks text, generates embeddings, and indexes them into OpenSearch.
3. **Retrieval**: Combines keyword search (BM25) and dense retrieval, applying user-specific ACL filters before ranking.
4. **Generation & Verification**: Generates responses grounded strictly in metadata, citing URN sources and verifying citations against active catalog assets.
5. **Evaluation**: Evaluates responses asynchronously using RAGAS (faithfulness, answer relevancy, context precision, context recall).

---

## Key Features

- **Natural Language Metadata Q&A**: Ask questions about datasets, column definitions, owners, domains, and tags in Vietnamese or English.
- **Server-Sent Events (SSE) Streaming**: Real-time response streaming with intermediate status indicators (retrieve, rerank, plan, generate).
- **Multi-Turn Memory & Coreference Resolution**: Retains active entity context across conversation turns, resolving follow-up questions such as "còn trường này thì sao?".
- **Grounded Action Menu**:
  - **SQL Generation**: Generates dialect-aware SQL queries grounded in exact catalog schemas with automatic join discovery.
  - **Schema Comparison**: Compares structural column definitions across multiple tables with type matching.
  - **Impact Analysis**: Traverses upstream and downstream dependency graphs to measure blast radius.
  - **Data Quality Check**: Audits documentation completeness, assertion runs, profiling status, and freshness.
  - **Metadata Maturity Report**: Produces structured maturity assessments across discoverability, governance, and quality dimensions.
- **Enterprise Security & RBAC**:
  - Role-based entity access control supporting user, group, and domain-level authorization.
  - Dual-layer ACL filtering on PostgreSQL queries and OpenSearch DSL queries.
  - Secret masking and prompt injection guards on user inputs and outputs.
- **Modern Next.js Frontend**:
  - Interactive chat interface with syntax-highlighted code blocks, lineage graphs, suggestion chips, and quality report visualizations.

---

## Directory Structure

```
datahub-ai-chatbot/
├── app/                          # FastAPI application
│   ├── api/                      # REST & Streaming endpoints
│   │   ├── actions.py            # SQL gen, schema diff, quality, impact
│   │   ├── chat.py               # Chat & streaming Q&A endpoints
│   │   ├── conversations.py      # Conversation session history
│   │   ├── documents.py          # Document upload & management
│   │   ├── health.py             # Health and readiness probes
│   │   ├── search.py             # Hybrid search endpoint
│   │   └── sync.py               # Ingestion sync triggers
│   ├── auth/                     # Authentication & authorization
│   │   ├── authorization.py      # Dual-layer ACL filtering
│   │   ├── identity.py           # Identity providers
│   │   ├── jwt.py                # Token verification
│   │   └── models.py             # UserContext and ACL models
│   ├── schemas/                  # Pydantic request/response schemas
│   └── services/                 # Business logic and orchestrators
│       ├── actions/              # Specialized domain action services
│       ├── action_service.py     # Unified actions facade
│       ├── chat/                 # Chat subservices and execution flows
│       └── chat_service.py       # Core chat orchestrator
├── config/                       # Settings, prompts, and log configurations
├── database/                     # SQLAlchemy models, repositories, and migrations
├── evaluation/                   # RAGAS offline & online evaluation pipeline
├── frontend/                     # Next.js 15 TypeScript web application
├── guardrails/                   # Input sanitization and safety filters
├── indexing/                     # Vector indexing, chunking, and pipeline
├── ingestion/                    # DataHub GraphQL client, mock sources, mappers
├── llm/                          # LLM abstraction (Fireworks, Fallback)
├── retrieval/                    # Hybrid search, intent routing, context builder
├── workers/                      # Background task workers (sync, index)
├── tests/                        # Comprehensive test suite (unit & integration)
└── scripts/                      # Bootstrap and indexing utility scripts
```

---

## Prerequisites

- **Python**: 3.12 or higher
- **Node.js**: 20.x or higher (for frontend)
- **Docker & Docker Compose**: For local PostgreSQL, Redis, and OpenSearch dependencies
- **Fireworks API Key** (optional): For hosted LLM generation (fallback mode operates without external keys)

---

## Quick Start

### 1. Backend Setup

```bash
# Clone the repository
git clone git@github.com:anoreo07/datahub_ai_chatbot.git
cd datahub_ai_chatbot/datahub-ai-chatbot

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Configure environment variables
cp .env.example .env

# Start infrastructure dependencies
docker compose up -d postgres redis opensearch

# Run database migrations
alembic upgrade head

# Bootstrap metadata catalog and search indices
python -m scripts.bootstrap

# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Run frontend development server
npm run dev
```

The frontend will be available at `http://localhost:3000` and the backend API at `http://localhost:8000`.

---

## Environment Configuration

Key configuration parameters defined in `.env`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `APP_ENV` | `development` | Environment mode (`development`, `test`, `production`) |
| `USE_MOCK_DATAHUB` | `true` | When true, uses embedded mock DataHub fixtures |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6380/0` | Redis instance for cache and job queues |
| `OPENSEARCH_URL` | `http://localhost:9201` | OpenSearch endpoint |
| `LLM_PROVIDER` | `fireworks` | Primary LLM provider |
| `FIREWORKS_API_KEY` | - | API key for Fireworks.ai |
| `JWT_SECRET_KEY` | - | Secret key for signing JWT tokens |
| `RAGAS_ENABLED` | `false` | Enable automated background RAGAS evaluation |

---

## API Endpoints Overview

### Chat & Streaming
- `POST /api/v1/chat`: Synchronous chat response with citations and metadata.
- `POST /api/v1/chat/stream`: SSE stream with real-time token delivery and step events.
- `GET /api/v1/conversations`: List saved conversation sessions.
- `GET /api/v1/conversations/{id}`: Retrieve turn history with render state.

### Actions API
- `POST /api/v1/actions/sql`: Generate grounded SQL queries from natural language.
- `POST /api/v1/actions/schema-compare`: Compare schemas of two or more entities.
- `POST /api/v1/actions/impact`: Perform upstream/downstream impact analysis.
- `POST /api/v1/actions/quality`: Audit dataset quality, profiling, and completeness.
- `POST /api/v1/actions/report`: Generate comprehensive metadata maturity reports.

### Search & Management
- `GET /api/v1/search`: Hybrid search across catalog entities.
- `POST /api/v1/sync/full`: Trigger full metadata synchronization.
- `GET /health`: Health and dependency status probe.

---

## Testing & Quality Assurance

### Run Unit Tests
```bash
python -m pytest tests/unit -q
```

### Run Integration Tests
```bash
python -m pytest tests/integration -q
```

### Code Formatting and Linting
```bash
ruff check .
ruff format . --check
```

---

## Deployment with Docker

To launch the complete application stack including backend, frontend, and services:

```bash
docker compose up --build -d
```

Service mapping:
- **FastAPI Backend**: `http://localhost:8000`
- **Next.js Web UI**: `http://localhost:3000`
- **OpenSearch**: `http://localhost:9201`
- **PostgreSQL**: `localhost:5433`
- **Redis**: `localhost:6380`
