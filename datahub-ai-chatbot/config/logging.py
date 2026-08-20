import re

import structlog

MASK = "[REDACTED]"

# Centralized redaction at the logging boundary. Applied to EVERY value the
# logger renders (including formatted exception tracebacks). These patterns are
# intentionally broader than guardrails.sanitizer's: the log boundary must not
# depend on which path produced the event.
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    # JWT / compact signed tokens (header "eyJ...").
    re.compile(r"\beyJ[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\b"),
    # Authorization / Bearer header values.
    re.compile(
        r"\bBearer\s+[A-Za-z0-9._\-~+/]{6,}",
        re.I,
    ),
    # Credential key=value assignments (the value is 6+ non-space chars).
    re.compile(
        r"\b(?:authorization|bearer|auth[_-]?token|access[_-]?token|refresh[_-]?token|"
        r"api[_-]?key|apikey|secret|client[_-]?secret|password|passwd|pwd|"
        r"credential|jwt[_-]?token|azure[_-]?access[_-]?token|token)\b"
        r"\s*[:=]\s*['\"]?[^\s'\"&,;|{}]+",
        re.I,
    ),
    # Connection strings with embedded credentials.
    re.compile(
        r"\b(?:postgres(?:ql)?|mysql|redis|rediss|mongodb(?:\+srv)?|snowflake|"
        r"jdbc|sqlite|amqp|mssql|oracle)://[^\s\"'<>]+",
        re.I,
    ),
]


def _redact_text(text: str) -> str:
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(MASK, out)
    return out


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v) for v in value)
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    return value


def redact_sensitive(logger, method_name, event_dict):
    """structlog processor: mask secrets in every event value, in place."""
    for key, value in event_dict.items():
        event_dict[key] = _redact_value(value)
    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        redact_sensitive,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
