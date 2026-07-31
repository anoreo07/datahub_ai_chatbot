# Platform

Infrastructure and deployment configurations for the DataHub AI Chatbot.

## Purpose

This folder contains all platform-level resources:

- Dockerfiles and Docker Compose for containerized deployment
- Kubernetes manifests for production orchestration
- Monitoring stack (Prometheus, Grafana, Loki, OpenTelemetry)
- Nginx reverse proxy configuration
- Terraform infrastructure-as-code modules
- Deployment scripts

## Local Monitoring

Start the monitoring stack:

```bash
docker compose -f monitoring/docker-compose.yml up -d
```

Services:

| Service | Port |
|---------|------|
| Prometheus | 9090 |
| Grafana | 3000 |
| Loki | 3100 |
| OpenTelemetry Collector | 4317 (gRPC) / 4318 (HTTP) |

## Kubernetes

Apply the base manifests:

```bash
kubectl apply -k kubernetes/base
```

### Overlays

Staging (reduced replicas):

```bash
kubectl apply -k kubernetes/overlays/staging
```

Production (full replicas):

```bash
kubectl apply -k kubernetes/overlays/production
```

## Important

- **Never commit real secrets.** The `secret.example.yaml` is a template only.
- Copy `.env.example` to `.env` and fill in actual values.
- The `registry.example.com` image placeholder must be replaced with your container registry.
