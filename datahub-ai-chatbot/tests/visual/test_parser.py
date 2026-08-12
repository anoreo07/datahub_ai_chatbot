"""Unit tests for the resilient :func:`parse_vision_json` parser.

Guarantees tested: every input below MUST produce a valid dict that:

  * always contains the canonical fields ``image_type``, ``dataset_name``,
    ``entities``, ``ocr_text``, ``summary``, ``parse_error``;
  * is never ``{}`` and never raises an exception out of the parser.
"""

import pytest

from retrieval.visual.parser import parse_vision_json

_SCHEMA_KEYS = {"image_type", "dataset_name", "entities", "ocr_text", "summary", "parse_error"}


def _assert_valid(result: dict) -> None:
    assert isinstance(result, dict)
    assert result != {}
    assert _SCHEMA_KEYS <= set(result.keys()), f"missing schema keys in {result}"


# --------------------------------------------------------------------------- #
# 1. Standalone, well-formed JSON
# --------------------------------------------------------------------------- #
def test_valid_json() -> None:
    raw = '{"image_type":"dashboard","dataset_name":"dim_inventory_category",' \
          '"ocr_text":"revenue","entities":[{"name":"a"}]}'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "dashboard"
    assert result["dataset_name"] == "dim_inventory_category"
    assert result["entities"] == [{"name": "a"}]
    assert result["parse_error"] is False


# --------------------------------------------------------------------------- #
# 2. JSON inside a markdown code fence
# --------------------------------------------------------------------------- #
def test_markdown_fence() -> None:
    raw = '```json\n{"image_type":"sql","dataset":null}\n```'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "sql"
    assert result["parse_error"] is False


def test_markdown_fence_no_lang() -> None:
    raw = '```\n{"image_type":"table","dataset":null}\n```'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "table"


# --------------------------------------------------------------------------- #
# 3. JSON clamped between surrounding prose
# --------------------------------------------------------------------------- #
def test_json_clamped_between_text() -> None:
    raw = 'Some lead-in text {"image_type":"lineage","dataset":null} and trailing.'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "lineage"


def test_multiple_brace_pairs_recover_first_object() -> None:
    raw = 'Talk {"a":1} then more {"image_type":"erd","dataset":null}'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "unknown"  # first object has no image_type
    assert result["a"] == 1


def test_braces_inside_strings_ignored() -> None:
    raw = 'note {"image_type":"table","ocr_text":"key {part} value"} ok'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "table"
    assert result["ocr_text"] == "key {part} value"


# --------------------------------------------------------------------------- #
# 4. JSON with a leading "Answer:"-style prefix
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("prefix", [
    "Answer:",
    "Response:",
    "Result:",
    "Output:",
    "Here is the answer:",
    "Here is the result:",
    "JSON:",
])
def test_prefix_extraction(prefix: str) -> None:
    raw = f"{prefix} {{\"image_type\":\"metadata\",\"dataset\":null}}"
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "metadata"


# --------------------------------------------------------------------------- #
# 5. JSON missing schema fields is auto-expanded with defaults
# --------------------------------------------------------------------------- #
def test_missing_fields_expanded() -> None:
    raw = '{"image_type":"datahub_dataset","dataset_name":"dim_inventory_category"}'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["image_type"] == "datahub_dataset"
    assert result["dataset_name"] == "dim_inventory_category"
    assert result["entities"] == []
    assert result["ocr_text"] == ""
    assert result["summary"] == ""
    assert result["parse_error"] is False


def test_only_image_type_expanded() -> None:
    result = parse_vision_json('{"image_type":"dashboard"}')
    _assert_valid(result)
    assert result["image_type"] == "dashboard"
    assert result["dataset_name"] is None
    assert result["entities"] == []


# --------------------------------------------------------------------------- #
# 6) JSON with extra fields is preserved (not stripped)
# --------------------------------------------------------------------------- #
def test_extra_fields_preserved() -> None:
    raw = '{"image_type":"table","dataset":null,"detected_tables":["sales.orders"]}'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["detected_tables"] == ["sales.orders"]
    assert "detected_tables" in result


# --------------------------------------------------------------------------- #
# 7) Malformed / broken JSON
# --------------------------------------------------------------------------- #
def test_broken_json_syntax() -> None:
    raw = '{"image_type": "dashb...,,,}'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["parse_error"] is True  # no valid object, only fallback


def test_broken_but_partially_valid_object_recovers() -> None:
    raw = 'prefix {"image_type":"dashboard"} trailing'
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["parse_error"] is False
    assert result["image_type"] == "dashboard"


# --------------------------------------------------------------------------- #
# 8) Model returns pure prose (the original bug) — content must be preserved
# --------------------------------------------------------------------------- #
def test_prose_only_fallback_preserves_content() -> None:
    raw = "The user wants me to analyze the dim_inventory_category dataset screenshot."
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["parse_error"] is True
    assert result["image_type"] == "unknown"
    assert result["dataset_name"] is None
    assert raw in result["summary"]  # full content kept, not lost


def test_prose_mentioning_dataset_after_prefix() -> None:
    raw = "Answer: analyzing dim_inventory_category and fact_sales now."
    result = parse_vision_json(raw)
    _assert_valid(result)
    # no valid JSON → structured fallback carrying the raw text
    assert result["parse_error"] is True
    assert "dim_inventory_category" in result["summary"]


# --------------------------------------------------------------------------- #
# 9) Empty / whitespace responses
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw", ["", "   ", "\n\t ", None, 0])
def test_empty_response_never_returns_bare_dict(raw) -> None:
    result = parse_vision_json(raw)
    _assert_valid(result)
    assert result["parse_error"] is True


# --------------------------------------------------------------------------- #
# 10) Non-str model output (dict already) is coerced to a valid dict
# --------------------------------------------------------------------------- #
def test_dict_input_coerced() -> None:
    result = parse_vision_json({"image_type": "dashboard", "dataset_name": "x"})
    _assert_valid(result)
    assert result["image_type"] == "dashboard"


# --------------------------------------------------------------------------- #
# 11) build_result integration: prose fallback never surfaces bare "unknown"
# --------------------------------------------------------------------------- #
def test_build_result_roundtrip() -> None:
    from retrieval.visual.parser import build_result

    # Model recognised the dataset but rambled in prose (no JSON).
    raw = "The user wants me to analyze the dataset dim_inventory_category."
    result = build_result(parse_vision_json(raw))
    # Not discarded: the full prose is surfaced in notes for the evidence card.
    assert result.notes
    assert any("dim_inventory_category" in n for n in result.notes)
    assert result.raw.get("parse_error") is True
