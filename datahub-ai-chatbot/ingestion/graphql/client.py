import asyncio
import random
import time
import uuid
from typing import Any

import requests
import structlog

from config.settings import settings
from guardrails.sanitizer import mask_secrets
from ingestion.errors import (
    DataHubAuthError,
    DataHubConnectionError,
    DataHubGraphQLError,
    DataHubTimeoutError,
)

log = structlog.get_logger()

WAF_MARKERS = ("im_under_attack_box", "loading-page")
USER_AGENT = "DataAtlas-MetadataSync/2.0 (internal metadata mirror; contact: dataatlas team)"
RETRY_BACKOFF = 3.0
RETRY_BACKOFF_MAX = 30.0


class DataHubRetryExhaustedError(DataHubGraphQLError):
    pass


def _jittered_sleep(base: float) -> None:
    time.sleep(base + random.uniform(0.0, base * 0.5))


def _sanitize_error_text(text: str, limit: int = 500) -> str:
    """Truncate + mask server-controlled content before it enters exceptions.

    Response bodies and GraphQL error objects are attacker/server-controlled and
    may echo the request (incl. the Authorization header). Sanitize here so the
    content is safe even when the exception later flows to a log, the DLQ, or an
    API response outside the logging-boundary redaction.
    """
    return mask_secrets(text[:limit])


def _classify_gql_errors(errors: list[dict]) -> str:
    for err in errors:
        ext = err.get("extensions") or {}
        c = ext.get("classification", "")
        if c == "ValidationError":
            return "validation"
        if c == "DataFetchingException":
            return "data_fetching"
    return "other"


class GraphQLClient:
    """GraphQL client cho DataHub corporate.

    Dùng requests (sync, chạy trong thread) giống scripts/pull_datahub_data.py —
    cơ chế đã chứng minh hoạt động với DataHub công ty (curl/requests OK, httpx 500).
    Gồm: UA riêng, jitter/backoff, phát hiện WAF, retry DataFetchingException.
    """

    def __init__(
        self,
        gms_url: str | None = None,
        token: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        raw = (gms_url or settings.DATAHUB_GMS_URL).rstrip("/")
        self._gms_url = raw.removesuffix("/api/graphql").rstrip("/")
        self._token = token or settings.DATAHUB_TOKEN
        self._timeout = timeout_seconds or settings.DATAHUB_REQUEST_TIMEOUT_SECONDS
        self._max_retries = max_retries or settings.DATAHUB_MAX_RETRIES
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            session = requests.Session()
            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            session.headers.update(headers)
            self._session = session
        return self._session

    def _request_sync(self, query: str, variables: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        url = f"{self._gms_url}/api/graphql"
        last: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                r = self._get_session().post(url, json=payload, timeout=self._timeout)
            except requests.exceptions.Timeout:
                last = DataHubTimeoutError(f"GraphQL request timed out after {self._timeout}s")
                log.warning("graphql_timeout", attempt=attempt, max_retries=self._max_retries)
                if attempt < self._max_retries:
                    _jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                    continue
                raise last
            except requests.exceptions.RequestException as exc:
                last = DataHubConnectionError(
                    f"Request failed: {_sanitize_error_text(str(exc), limit=300)}")
                log.warning("graphql_request_error", attempt=attempt)
                if attempt < self._max_retries:
                    _jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                    continue
                raise last

            if r.status_code == 403 or any(m in r.text.lower() for m in WAF_MARKERS):
                last = DataHubConnectionError(
                    f"HTTP 403 WAF: {_sanitize_error_text(r.text)}")
                log.warning("graphql_waf_blocked", attempt=attempt)
                if attempt < self._max_retries:
                    _jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                    continue
                raise last
            if r.status_code == 429:
                last = DataHubConnectionError(
                    f"HTTP 429: {_sanitize_error_text(r.text)}")
                log.warning("graphql_rate_limited", attempt=attempt)
                if attempt < self._max_retries:
                    _jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                    continue
                raise last
            if r.status_code == 401:
                raise DataHubAuthError("DataHub authentication failed: invalid or missing token")
            if r.status_code == 404:
                return {}
            if r.status_code != 200:
                last = DataHubConnectionError(
                    f"HTTP {r.status_code}: {_sanitize_error_text(r.text)}")
                log.warning("graphql_http_error", attempt=attempt, status=r.status_code)
                if attempt < self._max_retries:
                    _jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                    continue
                raise last

            data = r.json()
            if "errors" in data and data["errors"]:
                error_msg = _sanitize_error_text(str(data["errors"][:3]))
                cls = _classify_gql_errors(data["errors"])
                log.warning("graphql_errors", errors=error_msg, classification=cls, attempt=attempt)
                if cls == "validation":
                    raise DataHubGraphQLError(f"GraphQL validation error: {error_msg}")
                if self._is_auth_error(data["errors"]):
                    raise DataHubAuthError(f"GraphQL auth error: {error_msg}")
                if attempt < self._max_retries:
                    _jittered_sleep(min(RETRY_BACKOFF * 2 ** (attempt - 1), RETRY_BACKOFF_MAX))
                    continue
                raise DataHubConnectionError(f"GraphQL server error: {error_msg}")
            return data.get("data") or {}

        raise DataHubRetryExhaustedError(
            f"GraphQL request failed after {self._max_retries} retries"
        ) from last

    @staticmethod
    def _is_auth_error(errors: list[dict]) -> bool:
        for err in errors:
            msg = (err.get("message") or "").lower()
            if any(kw in msg for kw in ("unauthorized", "unauthenticated", "forbidden", "auth")):
                return True
        return False

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        if correlation_id is None:
            correlation_id = uuid.uuid4().hex[:12]
        return await asyncio.to_thread(self._request_sync, query, variables)

    async def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            await asyncio.to_thread(session.close)

    async def __aenter__(self) -> "GraphQLClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
