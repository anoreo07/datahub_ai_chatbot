"""Visual Understanding Skill — the independent image-analysis orchestrator.

This skill is callable *before* the existing skills / router. It reads a
data-related image via the vision model (Qwen2.5-VL through Fireworks), classifies
the image, extracts OCR + structured signals, and resolves the detected signals
against DataHub metadata — returning a normalised :class:`VisionResult` plus a
DataHub-grounded markdown evidence summary.

Key contract (per the product requirements):
  * The vision output is never answered to the user directly — it becomes
    structured evidence the router / downstream skills reuse.
  * Low-quality images (blurry / cropped / too-small text) are reported with a
    low-confidence signal and a suggestion to re-send a clearer image.
  * Irrelevant (non-data) images are refused politely — never guessed at.
  * Ambiguous signals are returned as candidate lists, not auto-selected.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from retrieval.entity_resolver import EntityResolver
from retrieval.visual.client import (
    VisionClient,
    create_vision_client,
    parse_data_url,
)
from retrieval.visual.models import (
    VisionEntity,
    VisionImageType,
    VisionQuality,
    VisionResult,
)
from retrieval.visual.parser import build_result, parse_vision_json

log = structlog.get_logger()

# Skills the router may dispatch to, per recognised image type. The model may
# also suggest its own set; this deterministic map is the safety net so routing
# always has a sensible default.
_SKILL_BY_TYPE: dict[VisionImageType, list[str]] = {
    VisionImageType.DASHBOARD: ["search_dataset", "metadata_summary", "glossary_search"],
    VisionImageType.ERD: ["search_dataset", "schema_analysis", "dataset_compare"],
    VisionImageType.SQL: ["generate_sql", "schema_analysis", "metadata_summary"],
    VisionImageType.SQL_ERROR: ["generate_sql", "metadata_summary", "lineage"],
    VisionImageType.ERROR: ["metadata_summary", "lineage", "impact_analysis"],
    VisionImageType.METADATA: ["metadata_summary", "glossary_search", "search_dataset"],
    VisionImageType.REQUIREMENT: ["search_dataset", "generate_sql", "glossary_search"],
    VisionImageType.TABLE: ["search_dataset", "schema_analysis", "dataset_compare"],
    VisionImageType.LINEAGE: ["lineage", "impact_analysis", "metadata_summary"],
    VisionImageType.WORKFLOW: ["lineage", "impact_analysis", "metadata_summary"],
    VisionImageType.ACCESS_PERMISSION: ["metadata_summary", "glossary_search"],
    VisionImageType.IRRELEVANT: [],
    VisionImageType.UNKNOWN: [],
}

_DISPLAY_TYPE: dict[VisionImageType, str] = {
    VisionImageType.DASHBOARD: "dashboard screenshot",
    VisionImageType.ERD: "ERD / data-model diagram",
    VisionImageType.SQL: "SQL / query screenshot",
    VisionImageType.SQL_ERROR: "SQL error screenshot",
    VisionImageType.ERROR: "error / exception screenshot",
    VisionImageType.METADATA: "metadata / catalog screenshot",
    VisionImageType.REQUIREMENT: "requirement / data-dictionary screenshot",
    VisionImageType.TABLE: "table / spreadsheet screenshot",
    VisionImageType.LINEAGE: "lineage / dependency screenshot",
    VisionImageType.WORKFLOW: "business-process / workflow screenshot",
    VisionImageType.ACCESS_PERMISSION: "access / permission / governance screenshot",
    VisionImageType.IRRELEVANT: "non-data image",
    VisionImageType.UNKNOWN: "unrecognised image",
}


class VisualUnderstandingSkill:
    """Independent image-analysis layer feeding the router with structured evidence."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        client: VisionClient | None = None,
        resolver: EntityResolver | None = None,
    ) -> None:
        self._client = client or create_vision_client()
        self._resolver = resolver
        if session is not None:
            self._resolver = self._resolver or EntityResolver(session)

    async def analyze(
        self,
        image_data_url: str,
        image_text_hint: str = "",
    ) -> VisionResult:
        """Analyze a single image; returns the normalised, structured result."""
        if not image_data_url:
            return self._reject("No image data was provided.")
        mime, payload = parse_data_url(image_data_url)
        if not mime or not payload:
            return self._reject(
                "The attachment is not a valid data URL or is empty."
            )
        if not str(mime).startswith("image/"):
            return self._reject(
                f"The attachment type '{mime}' is not a supported image."
            )
        if len(image_data_url) > settings.VISION_MAX_IMAGE_BYTES:
            return self._reject(
                "The image is too large. Please send a smaller / compressed image."
            )

        try:
            raw = await self._client.analyze(image_data_url, image_text_hint)
        except Exception as exc:  # noqa: BLE001
            log.exception("vision_analysis_failed", error=str(exc)[:200])
            if self._client.__class__.__name__ == "FireworksVisionClient":
                log.warning(
                    "vision_fallback_mock",
                    error=str(exc)[:200],
                )
                from retrieval.visual.client import MockVisionClient

                mock = MockVisionClient()
                mock_raw = await mock.analyze(image_data_url, image_text_hint)
                result = build_result(
                    parse_vision_json(_serialize(mock_raw))
                )
                result.notes.insert(
                    0,
                    "Vision model thật không khả dụng (404 / không có quyền "
                    "truy cập model vision) — đang dùng chế độ mock để chạy thử. "
                    "Để phân tích ảnh thật, hãy cấu hình API key Fireworks có "
                    "quyền truy cập model vision (ví dụ qwen2-vl / qwen2.5-vl).",
                )
                self._apply_type_routing(result)
                await self._resolve_signals(result)
                return result
            return self._reject(
                "Could not run the visual analysis right now. Please try again."
            )

        result = build_result(parse_vision_json(_serialize(raw)))
        self._apply_type_routing(result)
        await self._resolve_signals(result)
        return result

    # ------------------------------------------------------------------ #
    async def analyze_many(
        self,
        images: list[str],
        image_text_hint: str = "",
        limit: int | None = None,
    ) -> list[VisionResult]:
        """Analyze up to ``limit`` images concurrently, preserving order."""
        cap = limit or settings.VISION_MAX_IMAGES
        batch = (images or [])[:cap]
        results = await asyncio.gather(
            *(self.analyze(img, image_text_hint) for img in batch)
        )
        return list(results)

    # ------------------------------------------------------------------ #
    def _apply_type_routing(self, result: VisionResult) -> None:
        defaults = _SKILL_BY_TYPE.get(result.image_type, [])
        merged = list(dict.fromkeys((result.recommended_skills or []) + defaults))
        result.recommended_skills = merged

    # ------------------------------------------------------------------ #
    async def _resolve_signals(self, result: VisionResult) -> None:
        if not result.readable or self._resolver is None:
            return
        for name in result.all_mentioned():
            try:
                res = await self._resolver.resolve(name)
            except Exception:  # noqa: BLE001
                continue
            if not res.candidates:
                continue
            best = res.resolved or res.candidates[0]
            already = {c.name for c in result.detected_entities}
            if best and best.name not in already:
                result.detected_entities.append(
                    VisionEntity(
                        name=best.name,
                        type=best.entity_type,
                        confidence=best.score,
                    )
                )

    # ------------------------------------------------------------------ #
    def _reject(self, reason: str) -> VisionResult:
        return VisionResult(
            image_type=VisionImageType.UNKNOWN,
            ocr_text="",
            confidence=0.0,
            quality=VisionQuality.UNKNOWN,
            irrelevant=True,
            refusal_reason=reason,
            notes=[reason],
        )

    # ------------------------------------------------------------------ #
    def render_evidence(self, result: VisionResult) -> str:
        """Turn a vision result into a DataHub-grounded evidence summary (markdown)."""
        if result.irrelevant:
            return self._render_refusal(result)
        if result.quality in (VisionQuality.BLURRY, VisionQuality.TOO_SMALL,
                              VisionQuality.CROPPED, VisionQuality.LOW_CONTRAST):
            return self._render_low_quality(result)

        display = _DISPLAY_TYPE.get(result.image_type, "image")
        lines: list[str] = [
            f"### Visual Understanding — {display}",
            "",
        ]
        if result.ocr_text.strip():
            snippet = _trim(result.ocr_text, 500)
            lines += ["**OCR trích xuất:**", "```text", snippet, "```", ""]

        secs: list[tuple[str, list[str]]] = [
            ("Entities", [e.name for e in result.detected_entities]),
            ("Metrics", result.detected_metrics),
            ("Tables / datasets", result.detected_tables),
            ("Columns / fields", result.detected_columns),
            ("Relationships", result.detected_relationships),
            ("Questions", result.detected_questions),
        ]
        for title, items in secs:
            if items:
                lines.append(f"**{title}:** " + ", ".join(dict.fromkeys(items)))
                lines.append("")

        if result.detected_errors:
            lines.append("**Detected errors:**")
            for err in result.detected_errors:
                msg = err.get("message") or ""
                code = err.get("code") or ""
                hint = err.get("hint") or ""
                lines.append(f"- {msg} {f'({code})' if code else ''}")
                if hint:
                    lines.append(f"  - Gợi ý nguyên nhân: {hint}")
            lines.append("")

        if result.candidates:
            lines.append("**Candidates (chưa chốt — cần xác nhận):**")
            for cand in result.candidates:
                names = ", ".join(
                    f"{c.name} ({c.confidence:.0%})" for c in cand.candidates
                ) or "chưa rõ"
                lines.append(f"- {cand.detected} → {names}")
            lines.append("")

        if result.confidence:
            lines.append(f"**Độ tin cậy:** {result.confidence:.0%}")
            lines.append("")
        if result.recommended_skills:
            lines.append(
                "**Kỹ năng gợi ý:** " + ", ".join(result.recommended_skills)
            )
            lines.append("")
        if result.notes:
            lines.append("**Ghi chú:**")
            for n in result.notes:
                lines.append(f"- {n}")
            lines.append("")

        lines.append(
            "Tôi đã trích xuất thông tin trên từ ảnh. Hỏi tôi chi tiết hơn "
            "(ví dụ: “dashboard này dùng dataset nào?”, “chỉ số này nghĩa là gì?”, "
            "“bảng nào là fact/dim?”, “lỗi này do đâu?”) để tôi đối chiếu với "
            "metadata trong DataHub."
        )
        return "\n".join(lines)

    def _render_refusal(self, result: VisionResult) -> str:
        reason = result.refusal_reason or (result.notes[0] if result.notes else "")
        return (
            "### Visual Understanding\n\n"
            f"{reason or 'Ảnh này không liên quan đến dữ liệu / metadata.'}\n\n"
            "Tôi chỉ hỗ trợ các ảnh liên quan đến dữ liệu, metadata, dashboard, "
            "schema, SQL, lineage, quality, requirement và tài liệu nghiệp vụ "
            "trong DataHub."
        )

    def _render_low_quality(self, result: VisionResult) -> str:
        labels = {
            VisionQuality.BLURRY: "Ảnh bị mờ",
            VisionQuality.TOO_SMALL: "Chữ trong ảnh quá nhỏ",
            VisionQuality.CROPPED: "Ảnh bị cắt / thiếu phần nội dung",
            VisionQuality.LOW_CONTRAST: "Độ tương phản thấp",
        }
        why = labels.get(result.quality, "Chất lượng ảnh thấp")
        notes = " ".join(result.notes) if result.notes else ""
        return (
            "### Visual Understanding — ảnh chưa đọc rõ\n\n"
            f"**{why}.** Tôi chưa thể trích xuất thông tin tin cậy từ ảnh "
            f"(confidence ~{result.confidence:.0%}).\n\n"
            f"{notes}\n\n"
            "Bạn vui lòng gửi lại ảnh rõ hơn: nét chữ sắc nét, không cắt xén "
            "nội dung, và đủ độ phân giải để đọc text."
        )


def _serialize(raw: Any) -> str:
    """Coerce the client output (dict or str) into JSON text for the parser."""
    import json

    if isinstance(raw, dict):
        return json.dumps(raw, ensure_ascii=False)
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, ensure_ascii=False)


def _trim(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"
