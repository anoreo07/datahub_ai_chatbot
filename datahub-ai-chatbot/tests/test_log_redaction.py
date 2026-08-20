"""Regression tests for the centralized log redaction boundary.

Every structlog event (including formatted exception tracebacks) passes through
`config.logging.redact_sensitive`. These tests assert that known secret shapes
(JWT, Bearer headers, credential key=values, connection strings) never survive
into a rendered log event, while ordinary metadata and query tokens that do not
look like secrets are unaffected by the value-pattern redaction.
"""

import json

from config.logging import _redact_text, redact_sensitive
from ingestion.graphql.client import _sanitize_error_text

_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJhZG1pbiIsInJvbGVzIjpbImFkbWluIl19."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
_BEARER_TOKEN = "abc123-xyz-4defgHIJKlmno-0123456789"
_CREDENTIAL = "SuperSecretPass123"


def test_redacts_jwt():
    out = _redact_text(_JWT)
    assert _JWT not in out
    assert "[REDACTED]" in out


def test_redacts_bearer_header():
    out = _redact_text(f"Authorization: Bearer {_BEARER_TOKEN}")
    assert _BEARER_TOKEN not in out
    assert "[REDACTED]" in out


def test_redacts_credential_key_values():
    samples = [
        f"password={_CREDENTIAL}",
        f"access_token = {_CREDENTIAL}",
        f"client_secret:{_CREDENTIAL}",
        f"auth_token='{_CREDENTIAL}'",
        f"bearer={_CREDENTIAL}",
    ]
    for sample in samples:
        out = _redact_text(sample)
        assert "[REDACTED]" in out, sample
        assert _CREDENTIAL not in out, sample


def test_redacts_connection_string():
    text = "postgresql://user:SecretPass123@db.internal:5432/mydb"
    out = _redact_text(text)
    assert "SecretPass123" not in out
    assert "[REDACTED]" in out


def test_keeps_plain_metadata():
    text = "Question 'còn dashboard nào về PFEP?' entities=2 facts=3 status=403"
    assert _redact_text(text) == text


def test_keeps_urn_and_dataset_names():
    text = (
        "urn:li:dataset:(urn:li:dataPlatform:powerbi,"
        "PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)"
    )
    assert _redact_text(text) == text


def test_processor_redacts_every_event_value():
    event = {
        "event": "graphql_errors",
        "errors": json.dumps([{"message": "auth failed", "token": _JWT}]),
        "traceback": (
            "Traceback (most recent call last):\n"
            '  File "/x/client.py", line 123, in _request_sync\n'
            f'    raise DataHubConnectionError(f"HTTP 403 WAF: Bearer {_JWT}")\n'
            f'DataHubConnectionError: HTTP 403 WAF: Bearer {_JWT}'
        ),
        "nested": {"headers": {"authorization": f"Bearer {_JWT}"}},
        "attempt": 1,
        "status": 403,
        "ratio": 0.5,
    }
    out = redact_sensitive(None, "warning", dict(event))
    rendered = json.dumps(out, ensure_ascii=False)
    assert _JWT not in rendered
    assert _BEARER_TOKEN not in rendered
    assert out["attempt"] == 1
    assert out["status"] == 403
    assert out["ratio"] == 0.5


def test_processor_redacts_list_values():
    event = {
        "event": "batch",
        "tokens": [
            f"Bearer {_JWT}",
            "plain",
            f"access_token={_BEARER_TOKEN}",
        ],
    }
    out = redact_sensitive(None, "warning", dict(event))
    rendered = json.dumps(out, ensure_ascii=False)
    assert _JWT not in rendered
    assert _BEARER_TOKEN not in rendered
    assert "plain" in rendered
    assert "[REDACTED]" in rendered


def test_gms_client_sanitizes_error_body():
    body = f"<html>WAF block. Authorization: Bearer {_JWT}</html>" * 12
    out = _sanitize_error_text(body, limit=500)
    assert _JWT not in out
    assert len(out) <= 500


def test_gms_client_sanitizes_graphql_errors():
    errors = json.dumps([
        {"message": "Unauthorized", "extensions": {"classification": "DataFetchingException"},
         "details": f"Bearer {_JWT}"},
    ])
    out = _sanitize_error_text(errors)
    assert _JWT not in out
