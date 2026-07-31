# DataHub AI Chatbot

AI-powered chatbot for querying DataHub metadata using natural language, with RAG (Retrieval-Augmented Generation) pipeline.

## Architecture

```
User Question → Intent Classifier → Entity Resolution → Hybrid Search → Reranker → Context Builder → LLM → Response
                               ↕                          ↕
                         Structured Lookup         OpenSearch/PostgreSQL
```

1. **Ingestion** — Sync entities from DataHub (or mock) via GraphQL API to PostgreSQL
2. **Indexing** — Build entity documents, chunk, embed (mock), index into OpenSearch
3. **Retrieval** — Intent classification, entity resolution, hybrid search, reranking
4. **Generation** — Context assembly, Fireworks LLM (or fallback), citation validation

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Fireworks API key (optional — fallback mode works without it)

## Quick Start

```bash
# Clone and enter the project
cd datahub-ai-chatbot

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env

# Start dependencies
docker compose up -d postgres redis opensearch

# Run migrations
alembic upgrade head

# Bootstrap (creates tables, OpenSearch index, seeds mock data, indexes)
python -m scripts.bootstrap

# Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Mock Mode (No DataHub Required)

Set in `.env`:
```
USE_MOCK_DATAHUB=true
```

The system includes full mock data (`tests/fixtures/datahub/`) with:
- 3 datasets, 1 dashboard, 5 glossary terms, 1 document, 2 glossary nodes
- Lineage relationships
- Document content with sections
- Complete metadata (owners, terms, schema fields)

## Example Requests

```bash
# Glossary term definition
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Term Revenue nghĩa là gì?"}'

# Owner lookup
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Ai sở hữu dataset sales.orders?"}'

# Schema lookup
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Dataset sales.orders có những field nào?"}'

# Lineage
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Dataset finance.monthly_revenue lấy dữ liệu từ đâu?"}'

# Document QA
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Theo tài liệu, Net Revenue được tính như thế nào?"}'

# Search
curl "http://localhost:8000/api/v1/search?q=sales.orders"

# Sync
curl -X POST http://localhost:8000/api/v1/sync/full

# Health
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Metrics
curl http://localhost:8000/metrics
```

## Supported Questions (MVP)

| # | Question | Intent |
|---|----------|--------|
| 1 | "Term Revenue nghĩa là gì?" | TERM_DEFINITION |
| 2 | "Dataset nào gắn term Customer?" | TERM_TO_DATASETS |
| 3 | "Ai sở hữu dataset sales.orders?" | OWNER_LOOKUP |
| 4 | "Dataset sales.orders có những field nào?" | SCHEMA_LOOKUP |
| 5 | "Dataset finance.monthly_revenue lấy dữ liệu từ đâu?" | LINEAGE |
| 6 | "Report Monthly Revenue nằm ở đâu?" | FIND_ENTITY |
| 7 | "Ai sở hữu report Monthly Revenue?" | OWNER_LOOKUP |
| 8 | "Theo document, Net Revenue được tính như thế nào?" | DOCUMENT_QA |
| 9 | "Cho tôi link DataHub của dataset sales.orders." | DATAHUB_URL |
| 10 | "Dataset abc.xyz có tồn tại không?" | ENTITY_EXISTS |

## Responses

All chat responses include:
- `answer` — Natural language answer
- `intent` — Classified intent
- `entities` — Referenced entities (with URN and URL)
- `citations` — Source citations with URN, URL, and source type
- `confidence` — high/medium/low
- `ambiguous` — Whether multiple entities matched
- `insufficient_context` — Whether answer was limited
- `trace_id` — Request tracing

## Scripts

```bash
# Bootstrap: initialize DB, OpenSearch, seed data, index
python -m scripts.bootstrap

# Full sync from DataHub (or mock)
python -m scripts.full_sync

# Rebuild OpenSearch index from PostgreSQL
python -m scripts.rebuild_index

# Same as bootstrap (legacy alias)
python -m scripts.seed
```

## Workers

```bash
# Sync worker (periodic full sync)
python -m workers.sync_worker

# Indexing worker (process pending index jobs)
python -m workers.indexing_worker
```

## Docker Compose

```bash
# Start all services
docker compose up --build

# Start only dependencies (for local dev)
docker compose up -d postgres redis opensearch
```

Services:
| Service | Port | Purpose |
|---------|------|---------|
| API | 8000 | FastAPI app |
| PostgreSQL | 5433 | Metadata storage |
| Redis | 6380 | Cache and queue |
| OpenSearch | 9201 | Vector and keyword search |

## Configuration

See `.env.example` for all configuration options. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_DATAHUB` | `true` | Use mock data instead of real DataHub |
| `EMBEDDING_PROVIDER` | `mock` | Embedding provider (mock only for MVP) |
| `LLM_PROVIDER` | `fireworks` | LLM provider (Fireworks only) |
| `FIREWORKS_API_KEY` | — | Fireworks API key (optional in MVP) |
| `OPENSEARCH_INDEX` | `datahub-rag-chunks-v1` | OpenSearch index name |

## Switching to Real DataHub

1. Deploy DataHub (or point to existing instance)
2. Set `USE_MOCK_DATAHUB=false` in `.env`
3. Set `DATAHUB_GMS_URL` and `DATAHUB_TOKEN`
4. Set `DATAHUB_FRONTEND_URL`
5. Run `python -m scripts.full_sync`

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=ingestion --cov=indexing --cov=retrieval --cov=llm --cov=database

# Run specific test
pytest tests/test_intent.py -v
```

## Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

## Placeholder Modules

The following modules remain placeholder for future implementation:
- `llm/bedrock.py` — AWS Bedrock provider
- `llm/cohere.py` — Cohere provider
- `llm/openai.py` — OpenAI provider
- `llm/prompt.py` — Prompt template manager
- `ingestion/crawler.py` — Base crawler
- `ingestion/fetch_*.py` — Entity-specific crawlers
- `indexing/keyword_index.py` — Dedicated keyword index
- `workers/scheduler.py` — Background scheduler
- `workers/embedding_worker.py` — Dedicated embedding worker

## Secrets

- Never commit `.env` files
- API keys and tokens are read from environment variables only
- No secrets are logged (keys, tokens, Authorization headers)

## MVP Limitations

- Mock embedder only (deterministic hash-based, not semantic)
- Fireworks is the only LLM provider with working implementation
- No user authentication (local-developer only)
- No DataHub ACL integration
- No S3/MinIO storage (local filesystem only)
- Single-node OpenSearch (no k-NN plugin required)
- No streaming responses
- No conversation memory
