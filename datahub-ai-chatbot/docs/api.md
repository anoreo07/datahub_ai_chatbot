# API Reference

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| POST | `/api/v1/chat` | Chat with the AI assistant |
| POST | `/api/v1/search` | Search DataHub entities |
| GET | `/api/v1/glossary/terms` | List glossary terms |
| GET | `/api/v1/glossary/terms/{urn}` | Get glossary term details |
| POST | `/api/v1/sync/trigger` | Trigger a sync job |
| GET | `/api/v1/sync/status/{job_id}` | Get sync job status |
