"""Conversation Context Manager — keep Image Contexts alive for a whole conversation.

Binds uploaded images to a (user_id, conversation_id). Follow-up turns ask about
the same image without re-uploading; reopening a conversation restores the Image
Contexts from storage. Also resolves anaphora ("nó", "dataset này", "ảnh này")
to the active Image Context and disambiguates when several images are present.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image_context import ImageContext, context_from_dict
from app.services.image_upload import ImageUploadService
from database.models import ImageRecord
from database.repositories.image_repository import StorageRepository

log = structlog.get_logger()


class ConversationContextManager:
    """Registry of image contexts per conversation (in-memory + DB-backed)."""

    def __init__(
        self,
        session: AsyncSession,
        upload_service: ImageUploadService | None = None,
    ) -> None:
        self._session = session
        self._repo = StorageRepository(session)
        self._upload = upload_service or ImageUploadService(session)
        # in-memory cache: (user_id, conversation_id) -> list[ImageContext]
        self._cache: dict[tuple[str, str], list[ImageContext]] = {}

    def _key(self, user_id: str, conversation_id: str) -> tuple[str, str]:
        return (user_id, conversation_id)

    async def load(
        self, user_id: str, conversation_id: str, *, force: bool = False
    ) -> list[ImageContext]:
        """Return the Image Contexts bound to a conversation, restoring from DB.

        Never re-runs vision; uses the stored ``image_context`` JSON. When a
        record lacks a context (aged), reconstructs it from vision_result.
        """
        key = self._key(user_id, conversation_id)
        if cache := self._cache.get(key):
            if not force:
                return cache

        records = await self._repo.list_by_conversation(user_id, conversation_id)
        contexts: list[ImageContext] = []
        for rec in records:
            ctx = self._to_context(rec)
            if ctx is not None:
                contexts.append(ctx)
        self._cache[key] = contexts
        return contexts

    def _to_context(self, rec: ImageRecord) -> ImageContext | None:
        if rec.image_context:
            return context_from_dict(rec.image_context)
        if rec.vision_result:
            from app.services.image_context import ImageContextManager

            return ImageContextManager().build(
                rec.image_id, rec.user_id, rec.conversation_id, rec.filename, rec.vision_result
            )
        return None

    def bind(self, user_id: str, conversation_id: str, contexts: list[ImageContext]) -> None:
        key = self._key(user_id, conversation_id)
        self._cache[key] = contexts

    def invalidate(self, user_id: str, conversation_id: str) -> None:
        self._cache.pop(self._key(user_id, conversation_id), None)

    async def ingest(
        self,
        user_id: str,
        conversation_id: str,
        data_urls: list[str],
        image_text_hint: str = "",
        filenames: list[str] | None = None,
        vision_skill: Any = None,
    ) -> list[ImageContext]:
        """Persist + analyze each newly uploaded image and bind it to the conv.

        ``vision_skill`` optionally overrides the analysis model (used by the
        ChatService wiring / tests to inject a specific vision skill).
        """
        upload = self._upload
        if vision_skill is not None:
            from app.services.image_upload import ImageUploadService
            from app.services.vision_service import VisionService

            upload = ImageUploadService(
                self._session,
                vision_service=VisionService(self._session, skill=vision_skill),
            )
        contexts: list[ImageContext] = []
        for i, data_url in enumerate(data_urls or []):
            name = (filenames[i] if filenames and i < len(filenames) else None)
            record = await upload.upload_from_data_url(
                data_url, user_id, conversation_id,
                image_text_hint=image_text_hint, original_filename=name,
            )
            if record.image_context:
                ctx = context_from_dict(record.image_context)
                contexts.append(ctx)
        if contexts:
            self.bind(user_id, conversation_id, contexts)
        return contexts

    def resolve_active(
        self,
        question: str,
        user_id: str,
        conversation_id: str,
        default_contexts: list[ImageContext] | None = None,
    ) -> tuple[ImageContext | None, bool]:
        """Pick which Image Context a question refers to.

        Returns ``(context, needs_clarification)``. With a single image it is
        always that one. With many, we look for an explicit signal (dataset name,
        file name, OCR token); if none and the question is image-scoped we ask.
        """
        contexts = default_contexts or self._cache.get(self._key(user_id, conversation_id), [])

        active = [c for c in contexts if not c.irrelevant] or contexts
        if not active:
            return None, False
        if len(active) == 1:
            return active[0], False

        q = (question or "").lower()
        # Explicit match against dataset / file / known names.
        for c in active:
            entities = (c.detected_entities or [])
            entity_names = (str(e.get("name")) if isinstance(e, dict) else ""
                            for e in entities)
            candidates = [c.dataset_name, c.file_name]
            candidates += (c.detected_tables or [])
            candidates += list(entity_names)
            for cand in candidates:
                if cand and cand.strip().lower() in q:
                    return c, False

        # Failsafe: if the user references an image, prefer the most recent one.
        if _APHORIC_RE.search(q):
            return active[-1], False
        return None, True

    def summarize_for_reasoning(self, contexts: list[ImageContext]) -> str:
        """Build a compact, text-only recap used internally by reasoning."""
        parts: list[str] = []
        for ctx in contexts:
            lines = [f"- Image {ctx.file_name} ({ctx.image_type})"]
            if ctx.dataset_name:
                lines.append(f"  dataset: {ctx.dataset_name}")
            if ctx.detected_columns:
                lines.append("  fields: " + ", ".join(ctx.detected_columns))
            if ctx.detected_entities:
                names = [e.get("name", "") for e in ctx.detected_entities if isinstance(e, dict)]
                lines.append("  entities: " + ", ".join(n for n in names if n))
            if ctx.domain:
                lines.append(f"  domain: {ctx.domain}")
            if ctx.owner:
                lines.append(f"  owner: {ctx.owner}")
            parts.extend(lines)
        return "\n".join(parts)


_APHORIC_RE = re.compile(
    r"\b(?:nó|ấy|đó|này|đây|kia|ảnh|hình)\b", re.IGNORECASE
)
