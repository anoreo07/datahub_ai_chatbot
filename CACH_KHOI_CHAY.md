# DataHub AI Chatbot — LỆNH CHẠY NHANH

> Full stack REAL, 1 lượt khởi động gọn. Dữ liệu đã sync/index sẵn trong volume (320 entities, 318 jobs completed).
> Repo gốc: `/home/annh45/Desktop/datahub_ai_chatbot` — chatbot backend ở `datahub-ai-chatbot/`, frontend Next.js ở `datahub-ai-chatbot/frontend/`.

## 0. Bật tất cả trong 1 lượt

```bash
cd /home/annh45/Desktop/datahub_ai_chatbot

# 1) DataHub thật (mysql, kafka, opensearch, gms :8080, frontend :9002)
set -a; source ~/.datahub/quickstart/.local-secrets.env; set +a
export DATAHUB_VERSION=quickstart
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml up -d

# 2) Deps chatbot (postgres :5433, redis :6380, opensearch :9201)
cd datahub-ai-chatbot && docker compose up -d postgres redis opensearch

# 3) Ollama (chạy qua docker, image ollama/ollama có sẵn) + đảm bảo model embed
docker start ollama 2>/dev/null || docker run -d --name ollama --restart unless-stopped \
  -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
docker exec ollama ollama pull nomic-embed-text 2>/dev/null

# 4) Migrations (nếu volume mới / chưa upgrade)
source .venv/bin/activate
alembic upgrade head

# 5) Backend API :8000 (detach)
setsid nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  > /tmp/datahub_chatbot_uvicorn.log 2>&1 < /dev/null &

# 6) Frontend Next.js :3000 (detach)
cd frontend && setsid nohup npm run dev > /tmp/datahub_frontend_next.log 2>&1 < /dev/null &
```

## 1. Một lệnh duy nhất (copy-paste toàn bộ)

```bash
cd /home/annh45/Desktop/datahub_ai_chatbot && \
set -a; source ~/.datahub/quickstart/.local-secrets.env; set +a; export DATAHUB_VERSION=quickstart && \
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml up -d && \
cd datahub-ai-chatbot && docker compose up -d postgres redis opensearch && \
docker start ollama 2>/dev/null || docker run -d --name ollama --restart unless-stopped -p 11434:11434 -v ollama:/root/.ollama ollama/ollama; \
source .venv/bin/activate && alembic upgrade head && \
setsid nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/datahub_chatbot_uvicorn.log 2>&1 < /dev/null & \
cd frontend && setsid nohup npm run dev > /tmp/datahub_frontend_next.log 2>&1 < /dev/null &
```

## 2. Kiểm tra nhanh

```bash
curl -s http://localhost:8000/health        # {"status":"ok"}
curl -s http://localhost:8000/ready         # postgres/redis/opensearch/llm đều ok
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000   # frontend Next.js = 200
curl -s http://localhost:11434/api/tags     # ollama + nomic-embed-text
```

## 3. URL truy cập

| Ứng dụng | URL |
|----------|-----|
| Chat UI (Next.js) | http://localhost:3000 |
| Chat API (Swagger) | http://localhost:8000/docs |
| DataHub UI | http://localhost:9002 (datahub / datahub) |

## 4. Dừng

```bash
pkill -f "uvicorn app.main:app"; pkill -f "next-server"; pkill -f "next dev"
cd /home/annh45/Desktop/datahub_ai_chatbot/datahub-ai-chatbot && docker compose down
docker compose --profile quickstart -f ~/.datahub/quickstart/docker-compose.yml down
docker stop ollama
```

## 5. (Chỉ khi cần) Chạy lại sync + index từ đầu

Dữ liệu real DataHub đã sync/index sẵn trong volume — thông thường KHÔNG cần chạy lại.

```bash
cd /home/annh45/Desktop/datahub_ai_chatbot/datahub-ai-chatbot
source .venv/bin/activate
python -m scripts.full_sync
for i in 1 2 3 4 5 6 7 8 9 10; do python -m scripts.rebuild_index; done
```

## 6. Lưu ý

- `USE_MOCK_DATAHUB=false`, `USE_MOCK_LLM=false`, `USE_MOCK_EMBEDDING=false` → chế độ REAL toàn bộ.
- Backend proxy qua Next.js rewrites (`/api/*` → `localhost:8000`) nên chat UI same-origin.
- API chat yêu cầu auth (`AUTH_REQUIRED=true`) — cần login/token để gọi `/api/v1/chat`.
- Ollama chạy bằng docker (image `ollama/ollama` có sẵn) thay vì service local — model `nomic-embed-text` đã pull.
