"""Test GraphQL client with mocked HTTP responses."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingestion.graphql.client import (
    DataHubAuthError,
    DataHubTimeoutError,
    GraphQLClient,
)


@pytest.fixture
def client():
    return GraphQLClient(
        gms_url="http://fake:8080",
        token="test-token",
        timeout_seconds=5,
        max_retries=1,
    )


def _mock_response(status_code: int = 200, json_data: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data or {})
    return resp


@pytest.mark.asyncio
async def test_execute_success(client):
    resp = _mock_response(json_data={"data": {"__typename": "Query"}})
    mock_post = AsyncMock(return_value=resp)

    with patch.object(client, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        result = await client.execute("{ __typename }")
        assert result == {"__typename": "Query"}


@pytest.mark.asyncio
async def test_execute_unauthorized(client):
    resp = _mock_response(status_code=401)
    mock_post = AsyncMock(return_value=resp)
    resp.raise_for_status.side_effect = __import__("httpx").HTTPStatusError(
        "401", request=MagicMock(), response=resp,
    )

    with patch.object(client, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        with pytest.raises(DataHubAuthError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_timeout(client):
    mock_post = AsyncMock(side_effect=__import__("httpx").TimeoutException("timeout"))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        with pytest.raises(DataHubTimeoutError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_graphql_errors(client):
    resp = _mock_response(json_data={"errors": [{"message": "Something went wrong"}]})
    mock_post = AsyncMock(return_value=resp)

    with patch.object(client, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        result = await client.execute("{ __typename }")
        assert result == {}


@pytest.mark.asyncio
async def test_headers_contain_token():
    client = GraphQLClient(
        gms_url="http://fake:8080",
        token="super-secret-token-12345",
        max_retries=1,
    )
    headers = client._headers()
    assert headers["Authorization"] == "Bearer super-secret-token-12345"


@pytest.mark.asyncio
async def test_execute_auth_error_in_graphql_response(client):
    resp = _mock_response(json_data={
        "errors": [{"message": "Unauthorized: token expired"}],
    })
    mock_post = AsyncMock(return_value=resp)

    with patch.object(client, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        with pytest.raises(DataHubAuthError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_404_returns_empty(client):
    resp = _mock_response(status_code=404)
    mock_post = AsyncMock(return_value=resp)
    resp.raise_for_status.side_effect = __import__("httpx").HTTPStatusError(
        "404", request=MagicMock(), response=resp,
    )

    with patch.object(client, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        result = await client.execute("{ __typename }")
        assert result == {}
