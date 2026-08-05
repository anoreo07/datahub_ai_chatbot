"""Production guardrails for the DataHub metadata chatbot.

Reusable sanitizers, validators, and scope checks that enforce:
- grounded answers only (no hallucination)
- metadata source citation
- secret masking
- prompt-injection protection
- scope restriction (metadata-only assistant)
- output validation against retrieved evidence
"""

from guardrails.sanitizer import (
    contains_secrets,
    detect_prompt_injection,
    mask_secrets,
)
from guardrails.scope import classify_scope, is_out_of_scope, out_of_scope_response
from guardrails.service import GuardrailService
from guardrails.validation import (
    ValidationResult,
    has_evidence,
    no_evidence_response,
    validate_generation,
)

__all__ = [
    "contains_secrets",
    "detect_prompt_injection",
    "mask_secrets",
    "classify_scope",
    "is_out_of_scope",
    "out_of_scope_response",
    "GuardrailService",
    "ValidationResult",
    "has_evidence",
    "no_evidence_response",
    "validate_generation",
]
