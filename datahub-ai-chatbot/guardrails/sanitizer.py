"""Secret masking and prompt-injection detection.

Retrieved metadata is treated as untrusted content: it may contain embedded
instructions (prompt injection) or sensitive values (connection strings,
tokens, credentials, private endpoints). These utilities sanitize that content
before it is handed to the LLM and re-check the generated output before it is
returned to the user.
"""

import re

import structlog

log = structlog.get_logger()

MASK = "[REDACTED]"

# --- Sensitive value patterns -------------------------------------------------

_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    # JWT / compact tokens
    re.compile(r"\beyJ[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\b"),
    # key=value credentials (API keys, tokens, passwords, secrets). The value
    # must contain a digit and be 8+ chars to reduce false positives on plain
    # prose ("the password is complex").
    re.compile(
        r"\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|refresh[_-]?token|"
        r"secret|client[_-]?secret|password|passwd|pwd|credential|bearer)\b"
        r"(?:\s*[:=]\s*|\s+(?:is|was|la)\s+)['\"]?"
        r"(?=[A-Za-z0-9_\-./+]*[0-9])[A-Za-z0-9_\-./+]{8,}",
        re.I,
    ),
    # connection strings with embedded credentials
    re.compile(
        r"\b(?:postgres(?:ql)?|mysql|redis|rediss|mongodb(?:\+srv)?|snowflake|jdbc|sqlite|amqp|mssql|oracle)\b"
        r"://[^\s\"'<>]+",
        re.I,
    ),
    # private / internal endpoints (with optional embedded credentials)
    re.compile(
        r"\bhttps?://(?:[^/\s@:]+(?::[^@/\s]+)?@)?"
        r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+|"
        r"[^/\s]*\.(?:internal|local|svc|corp|intranet)(?:\.[^/\s]*)?)"
        r"(?::\d+)?(?:/|$)",
        re.I,
    ),
]

# --- Prompt-injection patterns ------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"ignore\s+(?:all\s+)?(?:previous|prior|earlier|above|your)\s+"
        r"(?:instructions|prompts|rules|directions)",
        re.I,
    ),
    re.compile(r"ignore\s+(?:your\s+)?(?:system|initial|base|original)\s+prompt", re.I),
    re.compile(
        r"disregard\s+(?:your\s+)?(?:system|previous)\s+(?:instructions|prompt|rules)",
        re.I,
    ),
    re.compile(
        r"forget\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|conversation|messages)",
        re.I,
    ),
    re.compile(
        r"reveal\s+(?:your\s+)?(?:system|instructions|prompt|system\s+message|hidden\s+prompt)",
        re.I,
    ),
    re.compile(
        r"(?:print|show|display|repeat|echo)\s+(?:your\s+)?"
        r"(?:instructions|system\s+prompt|hidden\s+prompt)",
        re.I,
    ),
    re.compile(
        r"you\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|free|dani|jailbreak|"
        r"without\s+(?:rules|limits|restrictions))",
        re.I,
    ),
    re.compile(r"pretend\s+to\s+be\s+(?:a\s+different|anything\s+but)", re.I),
    re.compile(
        r"fabricate\s+(?:metadata|lineage|schema|owners|descriptions|glossary|definitions)",
        re.I,
    ),
    re.compile(
        r"(?:run|execute|write)\s+(?:arbitrary\s+)?(?:code|command|python|shell|sql)\b",
        re.I,
    ),
    re.compile(
        r"(?:output|print|show|reveal|display|echo|tell)\s+(?:me\s+)?(?:your\s+)?(?:internal\s+)?system\s+prompt",
        re.I,
    ),
    re.compile(
        r"\b(?:database_url|jwt_secret_key|redis_url|api_key|secret_key|credentials?|mật\s*khẩu)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:drop\s+table|delete\s+from|truncate\s+table|alter\s+table|insert\s+into|update\s+\w+\s+set)\b",
        re.I,
    ),
    re.compile(
        r"(?:bỏ qua|bo qua|ignore|bypass|override)\s+(?:tất cả\s+|toàn bộ\s+|all\s+)?"
        r"(?:phân\s*quyền|quyền(?: của tôi)?|quy tắc|chính sách|bảo mật|permissions?|access\s*control|acl|security|rules)",
        re.I,
    ),
    re.compile(
        r"(?:cho tôi xem|xem|hiển thị|show|reveal)\s+(?:dữ liệu|thông tin|data)\s+"
        r"(?:bảo mật|bí mật|restricted|confidential|bị cấm|bi cam|chưa được phép)",
        re.I,
    ),
    re.compile(
        r"(?:tôi là admin|toi la admin|i am admin|acting as admin)\s+(?:hãy|cho|trả|bỏ qua|ignore|reveal)",
        re.I,
    ),
]


def mask_secrets(text: str) -> str:
    """Replace known sensitive values with a redaction marker."""
    if not text:
        return text
    out = text
    for pattern in _SENSITIVE_PATTERNS:
        out = pattern.sub(MASK, out)
    if out != text:
        log.info("secrets_masked", before_len=len(text), after_len=len(out))
    return out


def contains_secrets(text: str) -> bool:
    """True when the text still exposes a known sensitive value."""
    if not text:
        return False
    return any(p.search(text) for p in _SENSITIVE_PATTERNS)


def detect_prompt_injection(text: str) -> tuple[bool, str]:
    """Return ``(detected, matched_text)`` for prompt-injection attempts."""
    if not text:
        return False, ""
    for pattern in _INJECTION_PATTERNS:
        m = pattern.search(text)
        if m:
            return True, m.group(0)
    return False, ""
