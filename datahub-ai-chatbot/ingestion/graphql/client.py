import uuid
from typing import Any

import httpx
import structlog
from httpx import HTTPStatusError, RequestError, TimeoutException

from config.settings import settings

log = structlog.get_logger()


class DataHubGraphQLError(Exception):
    pass


class DataHubConnectionError(DataHubGraphQLError):
    pass


class DataHubAuthError(DataHubGraphQLError):
    pass


class DataHubTimeoutError(DataHubGraphQLError):
    pass


class DataHubRetryExhaustedError(DataHubGraphQLError):
    pass


class GraphQLClient:
    def __init__(
        self,
        gms_url: str | None = None,
        token: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._gms_url = (gms_url or settings.DATAHUB_GMS_URL).rstrip("/")
        self._token = token or settings.DATAHUB_TOKEN
        self._timeout = timeout_seconds or settings.DATAHUB_REQUEST_TIMEOUT_SECONDS
        self._max_retries = max_retries or settings.DATAHUB_MAX_RETRIES
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._gms_url,
                timeout=httpx.Timeout(self._timeout),
                headers=self._headers(),
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = correlation_id or uuid.uuid4().hex[:12]
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                client = await self._get_client()
                response = await client.post("/api/graphql", json=payload)
                response.raise_for_status()
            except TimeoutException as e:
                last_error = DataHubTimeoutError(f"GraphQL request timed out after {self._timeout}s")
                log.warning("graphql_timeout", correlation_id=cid, attempt=attempt, max_retries=self._max_retries)
                if attempt < self._max_retries:
                    import asyncio
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue
                raise DataHubTimeoutError(f"GraphQL request timed out after {self._max_retries} retries") from e
            except HTTPStatusError as e:
                status = e.response.status_code
                if status == 401:
                    raise DataHubAuthError("DataHub authentication failed: invalid or missing token") from e
                if status == 404:
                    return {}
                last_error = DataHubConnectionError(f"HTTP {status}: {e.response.text[:500]}")
                log.warning("graphql_http_error", correlation_id=cid, attempt=attempt, status=status)
                if attempt < self._max_retries and status >= 500:
                    import asyncio
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue
                raise last_error
            except RequestError as e:
                last_error = DataHubConnectionError(f"Request failed: {e}")
                log.warning("graphql_request_error", correlation_id=cid, attempt=attempt)
                if attempt < self._max_retries:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise last_error

            data = response.json()

            if "errors" in data and data["errors"]:
                error_msg = str(data["errors"][:3])
                log.warning("graphql_errors", correlation_id=cid, errors=error_msg)
                if self._is_auth_error(data["errors"]):
                    raise DataHubAuthError(f"GraphQL auth error: {error_msg}")
                return data.get("data") or {}

            return data.get("data") or {}

        raise DataHubRetryExhaustedError(f"GraphQL request failed after {self._max_retries} retries") from last_error

    @staticmethod
    def _is_auth_error(errors: list[dict]) -> bool:
        for err in errors:
            msg = (err.get("message") or "").lower()
            if any(kw in msg for kw in ("unauthorized", "unauthenticated", "forbidden", "auth")):
                return True
        return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GraphQLClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
