"""Test GraphQL client with mocked HTTP responses."""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from ingestion.graphql.client import (
    DataHubAuthError,
    DataHubConnectionError,
    DataHubGraphQLError,
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
    resp.text = json.dumps(json_data or {})
    return resp


def _patch_session(client, response=None, side_effect=None):
    session = MagicMock()
    if side_effect is not None:
        session.post.side_effect = side_effect
    else:
        session.post.return_value = response
    return patch.object(client, "_get_session", return_value=session), session


@pytest.mark.asyncio
async def test_execute_success(client):
    resp = _mock_response(json_data={"data": {"__typename": "Query"}})
    patcher, session = _patch_session(client, response=resp)
    with patcher:
        result = await client.execute("{ __typename }")
    assert result == {"__typename": "Query"}
    session.post.assert_called_once()
    _, kwargs = session.post.call_args
    assert kwargs["json"]["query"] == "{ __typename }"


@pytest.mark.asyncio
async def test_execute_unauthorized(client):
    resp = _mock_response(status_code=401)
    patcher, _ = _patch_session(client, response=resp)
    with patcher:
        with pytest.raises(DataHubAuthError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_timeout(client):
    patcher, _ = _patch_session(client, side_effect=requests.exceptions.Timeout("timeout"))
    with patcher:
        with pytest.raises(DataHubTimeoutError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_graphql_errors(client):
    resp = _mock_response(json_data={"errors": [{"message": "Something went wrong"}]})
    patcher, _ = _patch_session(client, response=resp)
    with patcher:
        with pytest.raises(DataHubConnectionError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_graphql_validation_error(client):
    resp = _mock_response(json_data={
        "errors": [{"message": "Validation", "extensions": {"classification": "ValidationError"}}],
    })
    patcher, _ = _patch_session(client, response=resp)
    with patcher:
        with pytest.raises(DataHubGraphQLError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_headers_contain_token():
    client = GraphQLClient(
        gms_url="http://fake:8080",
        token="super-secret-token-12345",
        max_retries=1,
    )
    headers = client._get_session().headers
    assert headers["Authorization"] == "Bearer super-secret-token-12345"


@pytest.mark.asyncio
async def test_execute_auth_error_in_graphql_response(client):
    resp = _mock_response(json_data={
        "errors": [{"message": "Unauthorized: token expired"}],
    })
    patcher, _ = _patch_session(client, response=resp)
    with patcher:
        with pytest.raises(DataHubAuthError):
            await client.execute("{ __typename }")


@pytest.mark.asyncio
async def test_execute_404_returns_empty(client):
    resp = _mock_response(status_code=404)
    patcher, _ = _patch_session(client, response=resp)
    with patcher:
        result = await client.execute("{ __typename }")
    assert result == {}


@pytest.mark.asyncio
async def test_execute_retries_then_raises():
    client = GraphQLClient(
        gms_url="http://fake:8080",
        token="test-token",
        timeout_seconds=5,
        max_retries=2,
    )
    resp = _mock_response(status_code=500)
    patcher, session = _patch_session(client, response=resp)
    with patcher:
        with pytest.raises(DataHubConnectionError):
            await client.execute("{ __typename }")
    assert session.post.call_count == 2
