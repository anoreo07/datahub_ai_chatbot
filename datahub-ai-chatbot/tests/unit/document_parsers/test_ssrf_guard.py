"""Tests for SSRF guard."""
from ingestion.document_parsers.ssrf_guard import SSRFGuard


def test_valid_https_url():
    guard = SSRFGuard()
    assert guard.validate("https://example.com/doc.pdf") is True


def test_valid_http_url():
    guard = SSRFGuard()
    assert guard.validate("http://example.com/doc.pdf") is True


def test_invalid_scheme():
    guard = SSRFGuard()
    assert guard.validate("ftp://example.com/file") is False
    assert guard.validate("file:///etc/passwd") is False
    assert guard.validate("data://example.com") is False


def test_localhost():
    guard = SSRFGuard()
    assert guard.validate("http://localhost:8000/doc") is False
    assert guard.validate("http://127.0.0.1:8000/doc") is False
    assert guard.validate("http://0.0.0.0:8000/doc") is False


def test_forbidden_port():
    guard = SSRFGuard()
    assert guard.validate("http://example.com:22/file") is False
    assert guard.validate("http://example.com:3306/file") is False
    assert guard.validate("http://example.com:5432/file") is False


def test_allowed_port():
    guard = SSRFGuard()
    assert guard.validate("http://example.com:8081/file") is True


def test_private_ip():
    guard = SSRFGuard()
    assert guard.validate("http://10.0.0.1/file") is False
    assert guard.validate("http://192.168.1.1/file") is False
    assert guard.validate("http://172.16.0.1/file") is False


def test_metadata_url():
    guard = SSRFGuard()
    assert guard.validate("http://169.254.169.254/latest/meta-data/") is False


def test_empty_url():
    guard = SSRFGuard()
    assert guard.validate("") is False


def test_malformed_url():
    guard = SSRFGuard()
    assert guard.validate("not a url") is False
