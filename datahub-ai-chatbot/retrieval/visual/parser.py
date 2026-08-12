"""Parser + normaliser for the Visual Understanding layer.

Takes the raw JSON (or near-JSON) returned by the vision model and normalises it
into a validated :class:`VisionResult`. Guards against malformed output
(markdown fences, leading noise, wrong types) and enforces the business rules:
low-confidence images are flagged, unrelated images are refused, and candidate
lists are preserved instead of auto-picking a single entity.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog

from retrieval.visual.models import (
    VisionCandidate,
    VisionEntity,
    VisionImageType,
    VisionQuality,
    VisionResult,
)

log = structlog.get_logger()

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

# Canonical schema the parser always guarantees, even on total failure.
_VISION_DEFAULTS: dict[str, Any] = {
    "image_type": "unknown",
    "dataset_name": None,
    "entities": [],
    "ocr_text": "",
    "summary": "",
    "parse_error": False,
}

# Prefixes a model may slap in front of the JSON payload (e.g. "Answer:").
_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"here\s+is\s+(?:the\s+)?(?:answer|response|result|output|json)"
    r"(?:\s*[:-])?\s*"
    r"|answer\s*[:.-]\s*"
    r"|response\s*[:.-]\s*"
    r"|result\s*[:.-]\s*"
    r"|output\s*[:.-]\s*"
    r"|returned?\s*[:.-]\s*"
    r"|json\s*[:.-]\s*"
    r"|```)",
    re.IGNORECASE,
)

_TYPE_ALIASES = {
    "dashboard": VisionImageType.DASHBOARD,
    "dashboards": VisionImageType.DASHBOARD,
    "bi_dashboard": VisionImageType.DASHBOARD,
    "erd": VisionImageType.ERD,
    "er_diagram": VisionImageType.ERD,
    "data_model": VisionImageType.ERD,
    "schema_diagram": VisionImageType.ERD,
    "sql": VisionImageType.SQL,
    "query": VisionImageType.SQL,
    "sql_screenshot": VisionImageType.SQL,
    "sql_error": VisionImageType.SQL_ERROR,
    "query_error": VisionImageType.SQL_ERROR,
    "error": VisionImageType.ERROR,
    "exception": VisionImageType.ERROR,
    "error_screenshot": VisionImageType.ERROR,
    "metadata": VisionImageType.METADATA,
    "catalog": VisionImageType.METADATA,
    "profile": VisionImageType.METADATA,
    "metadata_screenshot": VisionImageType.METADATA,
    "requirement": VisionImageType.REQUIREMENT,
    "brd": VisionImageType.REQUIREMENT,
    "data_dictionary": VisionImageType.REQUIREMENT,
    "table": VisionImageType.TABLE,
    "excel": VisionImageType.TABLE,
    "spreadsheet": VisionImageType.TABLE,
    "csv_preview": VisionImageType.TABLE,
    "lineage": VisionImageType.LINEAGE,
    "dependency": VisionImageType.LINEAGE,
    "dag": VisionImageType.LINEAGE,
    "workflow": VisionImageType.WORKFLOW,
    "process": VisionImageType.WORKFLOW,
    "flowchart": VisionImageType.WORKFLOW,
    "swimlane": VisionImageType.WORKFLOW,
    "access_permission": VisionImageType.ACCESS_PERMISSION,
    "permission": VisionImageType.ACCESS_PERMISSION,
    "governance": VisionImageType.ACCESS_PERMISSION,
    "irrelevant": VisionImageType.IRRELEVANT,
    "not_data": VisionImageType.IRRELEVANT,
    "none": VisionImageType.IRRELEVANT,
    "unknown": VisionImageType.UNKNOWN,
}


def normalize_image_type(raw: Any) -> VisionImageType:
    if isinstance(raw, VisionImageType):
        return raw
    if isinstance(raw, str):
        key = raw.strip().lower().replace("-", "_")
        return _TYPE_ALIASES.get(key, VisionImageType.UNKNOWN)
    return VisionImageType.UNKNOWN


def normalize_quality(raw: Any) -> VisionQuality:
    if isinstance(raw, VisionQuality):
        return raw
    if isinstance(raw, str):
        key = raw.strip().lower().replace("-", "_")
        try:
            return VisionQuality(key)
        except ValueError:
            return VisionQuality.CLEAR
    return VisionQuality.CLEAR


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
        return out
    return []


def _to_entities(value: Any) -> list[VisionEntity]:
    if not isinstance(value, list):
        return []
    out: list[VisionEntity] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        out.append(
            VisionEntity(
                name=name,
                type=str(item.get("type") or "unknown"),
                confidence=_to_float(item.get("confidence")),
            )
        )
    return out


def _to_errors(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        msg = str(item.get("message") or "").strip()
        if not msg:
            continue
        out.append(
            {
                "message": msg,
                "code": str(item.get("code") or ""),
                "hint": str(item.get("hint") or ""),
            }
        )
    return out


def _to_candidates(value: Any) -> list[VisionCandidate]:
    if not isinstance(value, list):
        return []
    out: list[VisionCandidate] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        detected = str(item.get("detected") or "").strip()
        cands = _to_entities(item.get("candidates"))
        if not detected:
            continue
        out.append(
            VisionCandidate(
                detected=detected,
                candidates=cands,
                note=str(item.get("note") or ""),
            )
        )
    return out


def parse_vision_json(raw: Any) -> dict[str, Any]:
    """Resiliently parse model output into a validated dict — never ``{}``, never raises.

    Layer 1: try ``json.loads`` on the trimmed text directly.
    Layer 2: extract a JSON object from a markdown code fence.
    Layer 3: strip a leading "Answer:" / "Response:" / "Result:" prefix, then parse.
    Layer 4: find the first balanced-brace JSON object anywhere in the text.
    Fallback: return a structured object carrying the whole raw response so no
    information is lost even when the model produced only prose.

    The return value always satisfies :data:`_VISION_DEFAULTS`: every field is
    present and ``parse_error`` flags whether extraction succeeded.
    """
    t0 = time.perf_counter()
    text = _coerce_text(raw)

    if not text:
        result = _fallback(text)
        _log_parse(text, result, "fallback", t0, "empty response")
        return result

    parsed: dict[str, Any] | None = None
    method = "fallback"
    extracted: str | None = None
    error: str | None = None

    try:
        parsed, method, extracted, error = _extract(text)
        if parsed is not None:
            result = _validate(parsed)
        else:
            result = _fallback(text)
    except Exception as exc:  # noqa: BLE001 - never propagate to the pipeline
        result = _fallback(text)
        error = f"{type(exc).__name__}: {exc}"

    _log_parse(text, result, method, t0, error, extracted)
    return result


def _extract(text: str) -> tuple[dict[str, Any] | None, str, str | None, str | None]:
    """Try each extraction layer in priority order.

    Returns ``(parsed, method, extracted, error)`` where ``parsed`` is ``None``
    when no layer produced a dict."""
    # Layer 1: the whole trimmed response is already a JSON object.
    parsed = _parse_json_dict(text)
    if parsed is not None:
        return parsed, "direct_json", text, None

    # Layer 2: JSON wrapped in a markdown code fence.
    fence = _FENCE_RE.search(text)
    if fence:
        candidate = fence.group(1).strip()
        if candidate:
            parsed = _parse_json_dict(candidate)
            if parsed is not None:
                return parsed, "markdown_extract", candidate, None

    # Layer 3: strip a leading prose prefix such as "Answer:" / "Result:".
    prefixed = _PREFIX_RE.sub("", text).strip()
    if prefixed and prefixed != text:
        parsed = _parse_json_dict(prefixed)
        if parsed is not None:
            return parsed, "regex_extract", prefixed, None

    # Layer 4: find the first balanced-brace JSON object in the string.
    balanced = _find_balanced_object(text)
    if balanced is not None:
        parsed = _parse_json_dict(balanced)
        if parsed is not None:
            return parsed, "regex_extract", balanced, None

    return None, "fallback", None, "no JSON object found in response"


def _parse_json_dict(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _find_balanced_object(text: str) -> str | None:
    """Return the first balanced-brace JSON object, ignoring braces inside strings.

    Falls back to respecting only ``{}``; if the outer thing is an array we also
    honour ``[]`` so a top-level list can still be recovered. Robust against
    multiple sibling ``{...}`` pairs in the prose."""
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == "{":
            end = _match_balanced(text, i, "{", "}")
            if end is not None:
                return text[i:end]
        elif ch == "[":  # a top-level array may wrap the object
            end = _match_balanced(text, i, "[", "]")
            if end is not None:
                candidate = _parse_json_dict(text[i:end])
                if candidate is not None:
                    return text[i:end]
        i += 1
    return None


def _match_balanced(text: str, start: int, open_ch: str, close_ch: str) -> int | None:
    """Return the index just past the matching close bracket, or ``None``.

    Tracks string literals and escapes so braces inside JSON strings are ignored.
    """
    depth = 0
    in_string = False
    escaped = False
    i = start
    length = len(text)
    while i < length:
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _coerce_text(raw: Any) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return json.dumps(raw, ensure_ascii=False)
    if raw is None:
        return ""
    return str(raw).strip()


def _validate(parsed: dict[str, Any]) -> dict[str, Any]:
    """Fill missing fields with defaults while preserving any extra fields."""
    result = dict(_VISION_DEFAULTS)
    result.update(parsed)
    result["parse_error"] = False
    return result


def _fallback(text: str) -> dict[str, Any]:
    """Structured fallback carrying the entire raw response for downstream use."""
    result = dict(_VISION_DEFAULTS)
    result["summary"] = text
    result["parse_error"] = True
    return result


def _log_parse(
    raw_response: str,
    result: dict[str, Any],
    method: str,
    t0: float,
    error: str | None,
    extracted: str | None = None,
) -> None:
    log.info(
        "vision_json_parse",
        raw_response=raw_response[:2000],
        extracted_json=(extracted[:2000] if extracted else None),
        parse_method=method,
        parse_success=result.get("parse_error") is False,
        parse_error=result.get("parse_error"),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        error_reason=error,
    )


def build_result(raw: dict[str, Any]) -> VisionResult:
    """Normalise the raw model dict into a validated :class:`VisionResult`."""
    confidence = _to_float(raw.get("confidence"), default=0.0)
    type_ = normalize_image_type(raw.get("image_type"))
    irrelevant = bool(raw.get("irrelevant") or type_ == VisionImageType.IRRELEVANT)
    ocr_text = str(raw.get("ocr_text") or "").strip()

    quality = normalize_quality(raw.get("quality"))

    # Low-quality / unreadable signals: confidence is forced low.
    if quality in (VisionQuality.BLURRY, VisionQuality.TOO_SMALL,
                   VisionQuality.CROPPED, VisionQuality.LOW_CONTRAST):
        confidence = min(confidence, 0.35)
        if not raw.get("notes"):
            raw["notes"] = ["Cannot read the image reliably."]

    notes = _to_str_list(raw.get("notes"))

    # If the model produced unstructured prose and the parser fell back, surface
    # the raw content so the evidence card is not an empty "unrecognised" box.
    if raw.get("parse_error") is True:
        summary = str(raw.get("summary") or "").strip()
        if summary:
            notes = notes or []
            notes = [
                "Model trả về văn xuôi thay vì JSON hợp lệ — hiển thị nội dung thô:"
            ] + [summary[:500]] + notes

    non_empty_signals = bool(
        ocr_text or
        _to_entities(raw.get("detected_entities")) or
        _to_str_list(raw.get("detected_tables"))
    )
    if irrelevant and not non_empty_signals:
        notes = notes or [
            "The image does not appear to relate to data / business metadata."
        ]

    return VisionResult(
        image_type=type_,
        ocr_text=ocr_text,
        detected_entities=_to_entities(raw.get("detected_entities")),
        detected_metrics=_to_str_list(raw.get("detected_metrics")),
        detected_tables=_to_str_list(raw.get("detected_tables")),
        detected_columns=_to_str_list(raw.get("detected_columns")),
        detected_relationships=_to_str_list(raw.get("detected_relationships")),
        detected_errors=_to_errors(raw.get("detected_errors")),
        detected_questions=_to_str_list(raw.get("detected_questions")),
        confidence=confidence,
        recommended_skills=_to_str_list(raw.get("recommended_skills")),
        notes=notes,
        quality=quality,
        irrelevant=irrelevant,
        refusal_reason=str(raw.get("refusal_reason") or ""),
        candidates=_to_candidates(raw.get("candidates")),
        raw=raw,
    )
