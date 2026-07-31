FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY . .

FROM python:3.12-slim AS runner

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app/data /tmp && \
    chown -R appuser:appuser /app /tmp

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app

RUN rm -rf /app/tests /app/.mypy_cache /app/__pycache__ 2>/dev/null || true

USER appuser

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=2 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "workers.sync_worker"]
