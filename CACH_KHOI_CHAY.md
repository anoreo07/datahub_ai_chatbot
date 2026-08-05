# Hướng dẫn khởi chạy dự án DataHub AI Chatbot (Full Stack — Real)

> Dự án gồm 2 phần chính trong repo `/home/annh45/Desktop/datahub_ai_chatbot`:
> - `datahub/` — mã nguồn DataHub (fork `datahub-project/datahub`) + stack quickstart chạy bằng Docker
> - `datahub-ai-chatbot/` — backend chatbot (FastAPI + PostgreSQL + OpenSearch + Redis)
>
> Tài liệu này mô tả **chế độ REAL toàn bộ** (không mock ở bất kỳ bước nào).

## 1. Kiến trúc tổng quan

```
                          ┌──────────────────────────────┐
                          │   DataHub (REAL)            │
                          │   GMS :8080 / Frontend :9002│
                          │   MySQL :3306, Kafka :9092  │
                          │   OpenSearch :9200          │
                          └──────────┬───────────────────┘
                                     │ GraphQL API
                         ┌───────────▼───────────────────┐
                         │ Chatbot (datahub-ai-chatbot)  │
                         │  Sync → Postgres :5433        │
                         │  Index → OpenSearch :9201     │
                         │  Embed: Ollama :11434 (REAL)  │
                         │  LLM : Fireworks (REAL)       │
                         └───────────────────────────────┘
```

## 2. Điều kiện tiên quyết

- Python 3.12, Docker + Docker Compose
- **Ollama** chạy local `:11434` với model `nomic-embed-text` (embedding thật)
- **Fireworks API key** (LLM thật) — đã có trong `.env` chatbot
- Images DataHub `acryldata/*:quickstart` đã pull sẵn trên máy
- `datahub` CLI (acryl-datahub) — cài trong venv chatbot

## 3. Khởi chạy DataHub thật

Compose quickstart được generate ở `~/.datahub/quickstart/docker-compose.yml`.

```bash
# Bước 1: khởi chạy toàn bộ DataHub (mysql, kafka, opensearch, gms, frontend, actions)
set -a; source ~/.datahub/quickstart/.local-secrets.env; set +a
export DATAHUB_VERSION=quickstart
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml up -d

# Bước 2: chờ GMS + frontend healthy
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml ps
#  datahub-datahub-gms-quickstart-1   Up (healthy)  0.0.0.0:8080->8080
#  datahub-frontend-quickstart-1      Up (healthy)  0.0.0.0:9002->9002
#  datahub-system-update-quickstart-1 Exited (0)     ← phải exit 0 (đã setup DB/index)
```

> ⚠️ `system-update` là job một lần (khởi tạo DB + index), phải `Exited (0)`.
> Nếu gặp lỗi port trùng, đổi `DATAHUB_MAPPED_GMS_PORT`/`DATAHUB_MAPPED_FRONTEND_PORT`.

## 4. Seed dữ liệu thật vào DataHub

Dùng `datahub` CLI trong venv chatbot để chạy data pack `showcase-ecommerce` (thực tế, tải từ GitHub).

```bash
source /home/annh45/Desktop/datahub_ai_chatbot/datahub-ai-chatbot/.venv/bin/activate
export DATAHUB_GMS_URL=http://localhost:8080 DATAHUB_GMS_TOKEN=
# Khởi tạo credentials CLI (chỉ chạy 1 lần; GMS quickstart dùng datahub/datahub)
datahub init --username datahub --password datahub

# Ingest showcase-ecommerce (dữ liệu real từ datahub-project/static-assets)
cat > /tmp/showcase_ingest.dhub.yaml <<'EOF'
source:
  type: "demo-data"
  config:
    pack_name: "showcase-ecommerce"
    trust_community: true
    trust_custom: true
sink:
  type: "datahub-rest"
  config:
    server: 'http://localhost:8080'
EOF
datahub ingest -c /tmp/showcase_ingest.dhub.yaml
```

> ⚠️ **Bug đã gặp:** lệnh `datahub ingest` có thể báo
> "No metadata was produced by the source" do cache pack rỗng. Cách chạy chắc chắn:
> chạy pipeline trực tiếp trong Python (xem mục 7 "Xử lý sự cố").
>
> Sau khi seed, DataHub có ~209 datasets, 4 dashboards, 14 charts, 177 glossary terms,
> 31 users. Kiểm tra: `curl -s -X POST http://localhost:8080/api/graphql -H "Content-Type: application/json" -d '{"query":"{ search(input:{type: DATASET, query:\"*\", start:0, count:0}){ total } }"}'`

## 5. Cấu hình chatbot chế độ REAL

File `datahub-ai-chatbot/.env` — các dòng bắt buộc:

```ini
USE_MOCK_DATAHUB=false
DATAHUB_GMS_URL=http://localhost:8080
DATAHUB_FRONTEND_URL=http://localhost:9002
DATAHUB_TOKEN=                # GMS quickstart tắt auth (METADATA_SERVICE_AUTH_ENABLED=false) nên để trống

USE_MOCK_LLM=false
USE_MOCK_EMBEDDING=false
USE_FAKE_OPENSEARCH=false
USE_IN_MEMORY_DATABASE=false
USE_IN_MEMORY_QUEUE=false

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
OLLAMA_BASE_URL=http://localhost:11434/v1

LLM_PROVIDER=fireworks
FIREWORKS_API_KEY=<key>
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/chatbot
REDIS_URL=redis://localhost:6380/0
OPENSEARCH_URL=http://localhost:9201
```

## 6. Chạy chatbot (migrations → sync → index → API)

```bash
cd datahub-ai-chatbot
source .venv/bin/activate

# Dependencies riêng của chatbot (Postgres :5433, Redis :6380, OpenSearch :9201)
docker compose up -d postgres redis opensearch

# Migrations
alembic upgrade head

# (Tùy chọn) Reset DB + OpenSearch khi muốn sync lại từ đầu — TRÁNH lẫn dữ liệu cũ/mock:
#   TRUNCATE entities, entity_chunks, index_jobs, sync_checkpoints, audit_logs RESTART IDENTITY CASCADE
#   curl -s -X DELETE http://localhost:9201/datahub-rag-chunks-v1

# Sync toàn bộ từ DataHub thật (GraphQL) → PostgreSQL
python -m scripts.full_sync
#  full_sync_complete results={'dataset': 209, 'dashboard': 4, 'glossary_term': 177, 'glossary_node': 5, 'document': 19}

# Index toàn bộ entities → OpenSearch (embed qua Ollama), chạy lặp đến khi pending=0
for i in 1 2 3 4 5 6 7 8 9 10; do
  python -m scripts.rebuild_index
  P=$(python - <<'EOF'
import asyncio
from sqlalchemy import text
from database.session import async_session_factory
async def m():
    async with async_session_factory() as s:
        return (await s.execute(text("SELECT count(*) FROM index_jobs WHERE status IN ('pending','processing')"))).scalar()
print(asyncio.run(m()))
EOF
)
  [ "$P" = "0" ] && break
done

# Khởi chạy API (dùng setsid để sống sót khi thoát shell)
setsid nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  > /tmp/datahub_chatbot_uvicorn.log 2>&1 < /dev/null &
disown
```

## 7. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready          # postgres/redis/opensearch/llm đều ok

# Glossary term (dữ liệu real)
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" \
  -d '{"question":"Term Revenue nghia la gi?"}'

# Schema dataset thực
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" \
  -d '{"question":"Dataset fact_sales_order co nhung field nao?"}'

# Owner lookup
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" \
  -d '{"question":"Ai so huu dataset dim_product_model?"}'

# Search
curl "http://localhost:8000/api/v1/search?q=revenue"
```

- UI chat: `http://localhost:8000/`
- UI DataHub: `http://localhost:9002/` (login `datahub` / `datahub`)
- Trạng thái DataHub: `docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml ps`

## 8. Dừng / quản lý

```bash
# Dừng chatbot API
pkill -f "uvicorn app.main:app" || true

# Dừng chatbot deps
cd datahub-ai-chatbot && docker compose down

# Dừng DataHub (giữ volume data)
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml down

# Xem log
tail -f /tmp/datahub_chatbot_uvicorn.log
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml logs -f datahub-datahub-gms-quickstart-1
```

## 9. Xử lý sự cố

| Lỗi | Nguyên nhân | Xử lý |
|-----|-------------|-------|
| `DataHubConnectionError: Temporary failure in name resolution` | `.env` để `USE_MOCK_DATAHUB=false` nhưng DataHub không chạy / sai `DATAHUB_GMS_URL` | Khởi động DataHub (mục 3) hoặc kiểm tra URL |
| `datahub ingest` → "No metadata was produced" | Cache data pack rỗng trong CLI | Chạy pipeline trực tiếp: |
| | | `python - <<'EOF'` |
| | | `from datahub.ingestion.run.pipeline import Pipeline` |
| | | `p=Pipeline.create({"source":{"type":"demo-data","config":{"pack_name":"showcase-ecommerce","trust_community":True,"trust_custom":True}},"sink":{"type":"datahub-rest","config":{"server":"http://localhost:8080"}}})` |
| | | `p.run()` |
| | | `p.pretty_print_summary()` |
| | | `EOF` |
| `openai.BadRequestError: invalid input` khi index | Ollama trả 400 khi gửi list embed rỗng (entity không có chunk) | Đã fix trong `indexing/pipeline.py` (skip khi `texts` rỗng). Pull code mới trước khi chạy |
| Port trùng 9200/9201/3306/9092 | DataHub + chatbot dùng port khác nhau nhưng trùng service khác | Đổi port qua env trong compose quickstart hoặc `.env` chatbot |
| `datahub init` báo thiếu token | Cần cấu hình trước khi dùng CLI | `datahub init --username datahub --password datahub` |
| Chat trả "không đủ thông tin" | Dataset không có owner/schema trong DataHub thật | Hỏi về dataset có dữ liệu (xem DB: `SELECT name FROM entities WHERE entity_type='dataset' LIMIT 20`) |

## 10. Ghi chú môi trường hiện tại (đã xác nhận chạy được)

- DataHub thật: GMS `:8080` (healthy), Frontend `:9002` (healthy), system-update exit 0
- DataHub data: 209 datasets, 4 dashboards, 177 glossary terms, 14 charts, 31 users (showcase-ecommerce)
- Chatbot: 414 index jobs completed, 844 chunks trong OpenSearch `:9201`, 0 failed
- Chat verified: TERM_DEFINITION, SCHEMA_LOOKUP, OWNER_LOOKUP trả lời đúng dữ liệu thực
- Embedding: Ollama `nomic-embed-text` (768-dim); LLM: Fireworks `deepseek-v4-flash`
- DataHub quickstart images tag `quickstart` đã có sẵn trên máy (không cần build)

## 11. Mock mode (chỉ khi không cần DataHub thật)

Đổi `.env` chatbot: `USE_MOCK_DATAHUB=true` (và tùy chọn `USE_MOCK_LLM=true`, `USE_MOCK_EMBEDDING=true`, `USE_FAKE_OPENSEARCH=true`, `USE_IN_MEMORY_DATABASE=true`, `USE_IN_MEMORY_QUEUE=true`), rồi chạy:
`alembic upgrade head && python -m scripts.bootstrap && uvicorn app.main:app --port 8000`.
