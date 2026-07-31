# Deployment Guide

## Architecture Overview

The system consists of:
- **API**: FastAPI application serving chat, search, and management endpoints
- **Sync Worker**: Periodically syncs entities from DataHub
- **Indexing Worker**: Chunks, embeds, and indexes entities into OpenSearch
- **Document Worker**: Processes document ingestion jobs
- **PostgreSQL**: Entity metadata, job tracking, audit logs, conversations
- **Redis**: Cache, rate limiting, message queues, distributed locks
- **OpenSearch**: Vector and keyword search index

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (local/staging)
- Kubernetes cluster + Helm (production)
- DataHub instance (GMS + Frontend)

## Local Development

```bash
cp .env.example .env
docker compose -f deploy/docker-compose.dev.yml up -d postgres redis opensearch
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or with full stack:

```bash
docker compose -f deploy/docker-compose.dev.yml up -d
```

### Mock Mode (no external dependencies)

```bash
USE_MOCK_DATAHUB=true \
AUTH_MODE=mock \
USE_MOCK_EMBEDDING=true \
python -m scripts.bootstrap
uvicorn app.main:app --reload
```

## Environment Variables

See `.env.example` for all configurable variables.

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_DATAHUB` | `true` | Use mock DataHub source |
| `AUTH_MODE` | `mock` | Authentication mode |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6380/0` | Redis connection string |
| `OPENSEARCH_URL` | `http://localhost:9201` | OpenSearch connection string |

## Docker Compose

### Development

```bash
docker compose -f deploy/docker-compose.dev.yml up -d
```

### Testing

```bash
docker compose -f deploy/docker-compose.test.yml up -d
pytest tests/
docker compose -f deploy/docker-compose.test.yml down
```

### Staging

```bash
docker compose -f deploy/docker-compose.staging.yml up -d
```

## Docker Build

```bash
# API
docker build -f deploy/docker/api.Dockerfile -t registry.example.com/datahub-ai-chatbot:VERSION .

# Worker
docker build -f deploy/docker/worker.Dockerfile -t registry.example.com/datahub-ai-worker:VERSION .

# Frontend (if using separate frontend)
docker build -f deploy/docker/frontend.Dockerfile -t registry.example.com/datahub-ai-frontend:VERSION .
```

## Helm (Kubernetes)

### Installation

```bash
# Staging
helm upgrade --install datahub-chatbot deploy/helm/datahub-chatbot \
  -f deploy/helm/datahub-chatbot/values-staging.yaml \
  --namespace datahub-chatbot --create-namespace

# Production
helm upgrade --install datahub-chatbot deploy/helm/datahub-chatbot \
  -f deploy/helm/datahub-chatbot/values-production.yaml \
  --namespace datahub-chatbot --create-namespace
```

### Custom Values

```bash
helm upgrade --install datahub-chatbot deploy/helm/datahub-chatbot \
  -f deploy/helm/datahub-chatbot/values-production.yaml \
  -f my-values.yaml \
  --set api.replicas=5
```

### Uninstall

```bash
helm uninstall datahub-chatbot --namespace datahub-chatbot
```

## Deployment Strategy

### Rolling Update (Default)

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

- Zero-downtime deploys
- One new pod starts before old pod terminates
- Health checks ensure new pod is ready before routing traffic

### Canary Deployments (Manual)

1. Deploy canary with reduced replica count
2. Route a percentage of traffic to canary
3. Monitor error rate and latency
4. If stable, roll out to all replicas
5. If unstable, rollback

```bash
# Deploy canary
helm upgrade --install datahub-chatbot-canary deploy/helm/datahub-chatbot \
  --set api.replicas=1 \
  --set api.image.tag=canary-v2 \
  --set ingress.enabled=false
```

### Blue/Green (Manual)

Two separate deployments: blue (current) and green (new).

```bash
# Deploy green
helm install datahub-chatbot-green deploy/helm/datahub-chatbot \
  --set api.replicas=3 \
  --set api.image.tag=v2.0.0 \
  --set ingress.enabled=false

# Test green, then switch
kubectl patch service chatbot-api -p '{"spec":{"selector":{"version":"green"}}}'

# Delete blue
helm uninstall datahub-chatbot-blue
```

## Rollback

### Docker Compose

```bash
# Revert to previous image tag
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate

# Or use git to revert code and rebuild
git revert HEAD
docker compose -f deploy/docker-compose.staging.yml build
docker compose -f deploy/docker-compose.staging.yml up -d
```

### Kubernetes / Helm

```bash
# Quick rollback to previous revision
helm rollback datahub-chatbot 1 --namespace datahub-chatbot

# Rollback to specific revision
helm rollback datahub-chatbot 2 --namespace datahub-chatbot

# Check revision history
helm history datahub-chatbot --namespace datahub-chatbot
```

### Database Rollback (Schema)

```bash
# Alembic downgrade
alembic downgrade -1

# Or to specific revision
alembic downgrade <revision_id>
```

### Full Rollback Procedure

1. **API**: `helm rollback datahub-chatbot <revision>`
2. **Database**: Run `alembic downgrade` if schema changed
3. **Index**: Rebuild if needed: `python -m scripts.rebuild_index`
4. **Verify**: Check `/health` and `/ready` endpoints

## Health and Readiness

- `/health`: Process-level health (always returns 200 if process is alive)
- `/ready`: Service readiness (checks database, Redis, OpenSearch connectivity)
- Kubernetes uses these for liveness and readiness probes

## Scaling

### Horizontal (API)

```bash
kubectl scale deploy/datahub-chatbot-api --replicas=10
```

### Autoscaling (HPA)

Configured in Helm values:
```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 15
    targetCPUUtilizationPercentage: 70
```

### Worker Autoscaling (KEDA)

When KEDA is enabled, workers scale based on queue depth:
```yaml
keda:
  enabled: true
  triggers:
    - type: redis
      metadata:
        listName: indexing:queue
        listLength: "10"
```

## Monitoring

- Prometheus metrics at `/metrics`
- Grafana dashboards for API, workers, and search quality
- Alert rules for high error rate, latency, sync lag, queue backlog

## Running Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Revert one migration
alembic downgrade -1

# Check status
alembic current
alembic heads
```

## CI/CD Pipeline

The GitHub Actions pipeline performs:

1. Lint (ruff, mypy)
2. Test (pytest unit, integration, security)
3. Migration check
4. Docker build
5. Helm lint and template validation
6. Publish images (on main/develop branches)

See `.github/workflows/ci.yml` for details.
