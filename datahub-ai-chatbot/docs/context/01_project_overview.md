# DataAtlas — Tổng quan project

## 1. Project là gì

**DataAtlas** (tên cũ: *DataHub AI Chatbot*) là một AI chatbot cho **DataHub** (metadata platform của VinFast) với **RAG pipeline**. Chatbot trả lời câu hỏi bằng tiếng Việt về dữ liệu doanh nghiệp: tìm dataset, tra cứu schema field, định nghĩa glossary term, lineage/impact analysis, domain lookup, listing, và các câu hỏi tổng hợp.

- Backend: **FastAPI** (Python 3.12). `[VERIFIED]`
- Frontend: **Next.js** (React). `[VERIFIED]`
- Lưu trữ: **PostgreSQL 16**, **OpenSearch 2.15**, **Redis 7**. `[VERIFIED]`
- Embedding: **Ollama** (`nomic-embed-text`, 768 dim) — chạy local. `[VERIFIED]`
- LLM: **Fireworks** (`deepseek-v4-flash-0731`) với fallback template khi LLM không available. `[VERIFIED]`
- Nguồn dữ liệu: **DataHub GMS** (corporate, bị WAF chặn) + snapshot dữ liệu đã pull về `datahub_pull/`. `[VERIFIED]`

## 2. Lịch sử phiên bản (git log)

`[VERIFIED]` — 6 commits, HEAD = `8a87be5c`:

| Commit | Message |
|---|---|
| `eaac0fe5` | Initial commit |
| `d6f90219` | Update version 2.0 |
| `0d5349ba` | Add semantic context precision, RBAC, quality reports, storage, and vision features |
| `14aa0c8b` | Add opt-in Query Understanding layer (LLM) for semantic precision |
| `a6dcb717` | Fix over-answer: focused field answers instead of whole-schema listings |
| `8a87be5c` | Add deterministic answers for owner/domain/impact via stored enrichment metadata |

> ⚠️ **Lưu ý trạng thái repo**: tại thời điểm tạo tài liệu (2026-08-20), `git status` cho thấy **56 files modified chưa commit** (4,256 insertions / 1,664 deletions) — phần lớn thuộc `app/services/chat/`, `retrieval/`, `frontend/`, `tests/`, `config/`. Điều này nghĩa là một lượng lớn cải tiến mới hơn (semantic precision, deterministic answers, vision) **chưa được commit**. `[OBSERVED]`

## 3. Trạng thái vận hành hiện tại

`[OBSERVED]` (2026-08-20, localhost):

| Thành phần | Địa chỉ | Trạng thái |
|---|---|---|
| PostgreSQL `chatbot` | localhost:5433 | ✅ UP |
| OpenSearch `datahub-rag-chunks-v1` | localhost:9201 | ✅ UP, 21,194 docs |
| Redis | localhost:6380 | ✅ UP |
| Backend API | localhost:8000 (uvicorn) | ✅ UP |
| Ollama serve | localhost:11434 | ✅ UP |

- `DATAHUB_SKIP_STARTUP_SYNC=1` được set — sync từ corporate DataHub bị **WAF chặn**, dữ liệu hiện có được sync từ snapshot pull `datahub_pull/`. `[VERIFIED]`
- `AUTH_REQUIRED=true`, `AUTH_MODE=jwt`. `[VERIFIED]`
- `USE_FAKE_OPENSEARCH=false` — dùng OpenSearch thật. `[VERIFIED]`

## 4. Cấu trúc repository

```
datahub-ai-chatbot/
├── app/                  # FastAPI app
│   ├── api/              # Routers: chat, search, sync, health, metrics, documents, glossary, index, me, actions, auth, conversations, roles, storage, datasource
│   ├── auth/             # identity, jwt, models, authorization, rbac, domain_utils
│   ├── services/         # ChatService + chat/* (entity_resolution, evidence, flows, listing, question_analysis, structured_retrieval, access, field_ops, lineage, context, vision)
│   ├── schemas/          # Pydantic models
│   ├── static/           # (có frontend cũ)
│   └── main.py           # FastAPI app entry
├── audit/                # Benchmark reports, metrics, golden dataset, traces
├── config/               # settings, constants, logging, prompts
├── database/             # SQLAlchemy models, session, repositories, migrations
├── datahub_pull/         # Snapshot JSONL pull từ DataHub thật (13 loại entity)
├── enrichment/           # DataHub enrichment verification
├── evaluation/           # Golden dataset, evaluator, metrics
├── frontend/             # Next.js frontend
├── guardrails/           # sanitizer, validation, scope, service
├── indexing/             # chunker, embedder, pipeline, vector_store, keyword_index
├── ingestion/            # mock_source, graphql_source, graphql/, mappers/, document_parsers/, sync.py
├── infrastructure/       # redis, cache, storage
├── llm/                  # base, client, fireworks, mock, openai, cohere, bedrock, nvidia, generator
├── metadata_generator/   # sinh metadata
├── retrieval/            # intent, intent_resolver, query_understanding, hybrid_search, reranker, entity_resolver, context_builder, citation, evidence, tools, planner_executor, graph, discovery, ...
├── sync/                 # incremental_sync, event_handler, dlq, retry, locks, consumer
├── tests/                # unit, integration, e2e, context, retrieval, api, evaluation
├── workers/              # sync_worker, indexing_worker, document_worker, embedding_worker, scheduler
├── compose.yaml          # postgres, redis, opensearch, api, sync-worker, indexing-worker
├── Dockerfile            # root Dockerfile (CI cũ trỏ tới path khác — vấn đề #6 AGENTS.md)
├── context_data.txt      # 124KB ground truth (snapshot cũ, 135 datasets)
├── for_gpt.txt           # 318KB ground truth (snapshot mới hơn)
├── docs/                 # tài liệu + context/ (bộ tài liệu này)
└── tests/, .github/, scripts/
```

## 5. Stack & dependencies chính

`[VERIFIED]` — từ `pyproject.toml`:

- `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`
- `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
- `opensearch-py`, `redis`, `structlog`
- `openai` (dùng chung cho Fireworks/Ollama client), `httpx`
- `PyMuPDF` (fitz) — parser PDF — **có mặt** trong `pyproject.toml` (`PyMuPDF>=1.23.0`, vấn đề #7 AGENTS.md đã được giải quyết). `[VERIFIED]`
- `pytest`, `pytest-asyncio`, `ruff`, `mypy`
- `numpy`, `tenacity`, `pyjwt`, `prometheus-client`, `acryl-datahub`

## 6. Mục tiêu tổng thể

1. Trả lời chính xác, **grounded** (có citation/evidence) về metadata DataHub. `[VERIFIED]` — bộ guardrail `guardrails/validation.py` kiểm tra URN bám evidence.
2. Hỗ trợ câu hỏi phức tạp: multi-hop, multi-turn, composite, graph query. `[VERIFIED]` — `retrieval/planner_executor.py`, `retrieval/query_understanding.py`.
3. Kiểm soát truy cập theo **domain + ACL** (RBAC). `[VERIFIED]` — `app/auth/rbac.py`, `app/auth/authorization.py`.
4. Đạt chuẩn chất lượng benchmark: mục tiêu mentor là nâng từ baseline 14.6% lên mức cao (xem `05_mentor_requirements.md`). `[VERIFIED]`

## 7. Tổng quan người dùng / đối tượng

- Người dùng nội bộ VinFast: các team Tài chính, Sản Xuất, Logistics, Sales, Kinh Doanh, Cung ứng, Hậu mãi, Phát triển xe, VGreen. `[VERIFIED]` — 9 domains trong DB.
- Chatbot hỗ trợ tiếng Việt (câu trả lời, prompts đều tiếng Việt). `[VERIFIED]`