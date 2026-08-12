import re

from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import _IMAGE_REF_RE
from app.services.image_context import ImageContext


class VisionContextService:
    """VisionContextService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def answer_from_image_context(
        self,
        context: ImageContext,
        question: str,
        history: list[tuple[str, str]],
    ) -> tuple[str, str, bool]:
        """Compose a concise, direct answer from an Image Context.

        IMAGE IS CONTEXT, NOT INTENT: the image-derived dataset is bound as the
        conversation's active entity and entity hint so the REAL DataHub function
        flows (SQL, quality, impact, lineage, schema, owner, domain, glossary…)
        execute against it. This method answers directly ONLY for questions that
        are purely about the image's own contents ("ảnh này là gì", "dataset trong
        ảnh tên gì?", "trong ảnh có những trường nào") — and even then concisely,
        grounded in the entity's real DataHub metadata (name, fields, description).
        Anything that maps to a DataHub function returns ``handled=False`` so the
        normal routing executes it at the correct priority. The internal OCR /
        entities / confidence / JSON evidence is never surfaced to the user.

        Returns ``(answer_text, confidence, handled)``.
        """
        if context.irrelevant:
            reason = context.refusal_reason or context.notes[0] if context.notes else ""
            text = (
                "Ảnh này không liên quan đến dữ liệu / metadata trong DataHub nên "
                "tôi không thể phân tích nó."
                + (f" {reason}" if reason else "")
            )
            return text, "low", True

        # The question must explicitly reference the image itself (ảnh/hình/bảng
        # này/nó/đây...). Without an image reference the image is only a context
        # hint and the question routes through the normal pipeline.
        raw = question.lower()
        image_ref = _IMAGE_REF_RE.search(raw) is not None
        if not image_ref:
            return "", "", False

        # Purely image-content question detection. Matched against the raw
        # (diacritic-preserved) lowercased question; ASCII spellings are
        # included for users who type without diacritics. Relationship questions
        # ("field nào liên kết / join với ...") are NOT pure content: they need
        # the schema/join logic, so they fall through to the normal pipeline
        # (which runs against the image-derived entity / evidence).
        fields_ask = bool(re.search(
            r"(các\s+)?trường|field|cột|column|schema|(các\s+)?truong|co |struct", raw)) \
            and not bool(re.search(
                r"liên\s+kết|lien\s+ket|join|link|liên\s+quan|lien\s+quan|khóa|khoa",
                raw,
            ))
        what_ask = bool(re.search(
            r"ảnh này là gì|đây là gì|nội dung|dataset gì|ảnh gì|mô tả|mo ta|"
            r"chứa gì|chua gi|có gì|co gi|tóm tắt|tom tat|nói về|noi ve|"
            r"tổng quan|tong quan|anh nay la gi|day la gi|tên gì|ten gi|"
            r"là\s+\w*\s*gì|la\s+\w*\s*gi", raw))

        confidence = (
            "high" if context.confidence >= 0.7
            else "medium" if context.confidence >= 0.4 else "low"
        )

        # Fetch the real DataHub entity behind the image so image-content answers
        # name the canonical dataset, not the raw OCR snapshot cached at upload.
        payload: dict = {}
        dataset_name = context.dataset_name
        if dataset_name and context.dataset_urn:
            db = await self._ctx.entity_repo.get_by_urn(context.dataset_urn)
            if db is not None:
                payload = db.payload or {}
                dataset_name = db.display_name or db.name
                context.dataset_name = dataset_name

        # Which fields are actually present in the real schema (image detection
        # is only a fallback when the real schema has no fields recorded).
        real_fields = [
            (f.get("name") or "").strip()
            for f in payload.get("schema_fields") or []
            if (f.get("name") or "").strip()
        ]
        fields = list(dict.fromkeys(
            real_fields or context.detected_columns
        ))

        if what_ask:
            bits: list[str] = []
            if dataset_name:
                bits.append(f"Trong ảnh là dataset **{dataset_name}**")
            desc = payload.get("description") or context.description
            if desc:
                bits.append(f"Mô tả: {str(desc)[:200]}")
            if context.detected_metrics:
                bits.append("Chỉ số: " + ", ".join(context.detected_metrics[:6]))
            if context.detected_tables:
                bits.append("Bảng: " + ", ".join(context.detected_tables[:6]))
            if not bits:
                return ("Tôi đã nhận được ảnh nhưng chưa nhận diện được dataset cụ thể "
                        "nào khớp với metadata DataHub. Xin hãy tải ảnh rõ hơn hoặc "
                        "hỏi trực tiếp về tên dataset bạn cần.", "low", True)
            return " · ".join(bits), confidence, True

        if fields_ask:
            if not fields:
                if dataset_name:
                    return (f"Dataset **{dataset_name}** trong ảnh hiện chưa có thông tin "
                            "về bộ trường trong metadata DataHub.", "medium", True)
                return ("Tôi chưa nhận diện được dataset cụ thể trong ảnh, nên không "
                        "thể liệt kê các trường. Bạn có thể tải lại ảnh rõ hơn "
                        "hoặc hỏi trực tiếp tên dataset.", "low", True)
            text = (
                f"Trong ảnh là dataset **{dataset_name}**, với các trường: "
                f"{', '.join(fields)}."
            )
            return text, confidence, True

        # Any other image-referencing question (lineage, owner, domain, glossary,
        # SQL, quality, impact…) is a real DataHub function — route it through the
        # normal pipeline against the image-derived entity already bound above.
        return "", "", False


    async def image_entity_identity(
        self, context: ImageContext,
    ) -> tuple[str | None, str | None]:
        """Return the canonical ``(name, urn)`` of the dataset the image identifies.

        Falls back to the raw OCR-derived name when the stored urn cannot be
        resolved against the catalog.
        """
        if context is None or not context.dataset_name:
            return None, None
        name = context.dataset_name
        urn = context.dataset_urn
        if urn:
            try:
                db = await self._ctx.entity_repo.get_by_urn(urn)
            except Exception:  # noqa: BLE001
                db = None
            if db is not None:
                return (db.display_name or db.name), (db.urn or urn)
        return name, urn
