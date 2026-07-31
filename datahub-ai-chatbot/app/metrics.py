"""Prometheus metrics for the chatbot."""
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

chat_queries_total = Counter(
    "chat_queries_total", "Total chat queries", ["intent"]
)

chat_confidence_total = Counter(
    "chat_confidence_total", "Chat responses by confidence", ["confidence"]
)

entity_resolutions_total = Counter(
    "entity_resolutions_total", "Entity resolution results", ["outcome"]
)

cache_hits_total = Counter(
    "cache_hits_total", "Cache hit/miss", ["result"]
)

documents_ingested_total = Counter(
    "documents_ingested_total", "Documents ingested", ["status"]
)

upstream_health = Gauge(
    "upstream_health", "Upstream service health (1=ok, 0=error)", ["service"]
)

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
