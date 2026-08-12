"""Image Upload Service — accept an image, persist it, analyse and record metadata.

Bridges the storage layer, vision service and image context manager:
  1. decode / validate the incoming image bytes,
  2. compute a content hash,
  3. persist the original + thumbnail via ImageStorageService,
  4. create an ImageRecord (metadata only) via StorageRepository,
  5. run VisionService (cache-aware) and store the vision result + ImageContext,
  6. auto-detect the dataset and enrich against DataHub.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image_context import ImageContextManager
from app.services.image_storage import (
    ImageStorageService,
    UnsupportedImageTypeError,
    decode_data_url,
)
from app.services.vision_service import VisionService
from database.models import ImageRecord, ImageStatus
from database.repositories.image_repository import StorageRepository

log = structlog.get_logger()


class ImageServiceError(Exception):
    pass


class ImageUploadService:
    def __init__(
        self,
        session: AsyncSession,
        image_context_builder: ImageContextManager | None = None,
        vision_service: VisionService | None = None,
    ) -> None:
        self._session = session
        self._storage = ImageStorageService()
        self._repo = StorageRepository(session)
        self._context_builder = image_context_builder or ImageContextManager()
        self._set_vision(vision_service)

    def _set_vision(self, vision_service: VisionService | None) -> None:
        self._vision = vision_service or VisionService(self._session)

    async def upload_from_data_url(
        self,
        data_url: str,
        user_id: str,
        conversation_id: str | None = None,
        image_text_hint: str = "",
        original_filename: str | None = None,
    ) -> ImageRecord:
        """Persist + analyze an image provided as a ``data:`` URL."""
        mime, payload = decode_data_url(data_url)
        if not payload:
            raise ImageServiceError("Empty or invalid image payload")
        return await self._persist_and_analyze(
            payload, mime, user_id, conversation_id,
            image_text_hint=image_text_hint, original_filename=original_filename,
        )

    async def upload_from_bytes(
        self,
        payload: bytes,
        mime: str,
        user_id: str,
        conversation_id: str | None = None,
        image_text_hint: str = "",
        original_filename: str | None = None,
    ) -> ImageRecord:
        if not payload:
            raise ImageServiceError("Empty image payload")
        if not mime.startswith("image/"):
            raise UnsupportedImageTypeError(f"Unsupported type: {mime}")
        return await self._persist_and_analyze(
            payload, mime, user_id, conversation_id,
            image_text_hint=image_text_hint, original_filename=original_filename,
        )

    async def _persist_and_analyze(
        self,
        payload: bytes,
        mime: str,
        user_id: str,
        conversation_id: str | None,
        *,
        image_text_hint: str = "",
        original_filename: str | None = None,
    ) -> ImageRecord:
        from app.services.image_storage import compute_content_hash

        content_hash = compute_content_hash(payload)
        image_id = uuid.uuid4().hex[:16]

        paths = self._storage.save(user_id, image_id, payload, mime, original_filename)
        data_url = _to_data_url(payload, mime)

        record = ImageRecord(
            image_id=image_id,
            user_id=user_id,
            conversation_id=conversation_id,
            original_filename=paths["filename"],
            filename=paths["filename"],
            mime_type=mime,
            size=len(payload),
            storage_path=paths["storage_path"],
            thumbnail_path=paths["thumbnail_path"],
            status=ImageStatus.UPLOADED.value,
            content_hash=content_hash,
        )
        record = await self._repo.create(record)

        await self._analyze(
            record, payload, mime, data_url=data_url, image_text_hint=image_text_hint,
        )
        return record

    async def _analyze(
        self,
        record: ImageRecord,
        payload: bytes,
        mime: str,
        *,
        data_url: str = "",
        image_text_hint: str = "",
    ) -> None:
        """Run vision + build context + enrichment; update the record in place."""
        await self._repo.update_fields(record.image_id, status=ImageStatus.ANALYZING.value)

        try:
            result = await self._vision.analyze(
                record.content_hash, data_url or _to_data_url(payload, mime), image_text_hint,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("image_analysis_failed", image_id=record.image_id)
            await self._repo.update_fields(record.image_id, status=ImageStatus.FAILED.value)
            raise ImageServiceError(f"Vision analysis failed: {exc}") from exc

        # Build ImageContext (internal). Enrich dataset against DataHub.
        context = self._context_builder.build(
            record.image_id, record.user_id, record.conversation_id,
            record.filename, result,
        )
        if not context.irrelevant and context.dataset_name:
            enriched = await self._vision.enrich_dataset(context.dataset_name)
            if enriched:
                context.dataset_name = enriched.get("dataset_name") or context.dataset_name
                context.dataset_urn = enriched.get("dataset_urn")
                context.domain = enriched.get("domain")
                context.owner = enriched.get("owner")
                context.description = enriched.get("description")
                context.platform = enriched.get("platform")

        await self._repo.update_fields(
            record.image_id,
            status=ImageStatus.ANALYZED.value,
            image_type=context.image_type,
            dataset_detected=context.dataset_name,
            vision_result=result,
            image_context=context.to_dict(),
            parse_error=bool(context.parse_error),
        )

    async def rerun_analysis(
        self, image_id: str, user_id: str, image_text_hint: str = ""
    ) -> ImageRecord | None:
        """Re-run vision on a stored image (bypasses cache)."""
        record = await self._repo.get(image_id)
        if record is None or record.user_id != user_id:
            return None
        try:
            payload = self._storage.read_bytes(record.storage_path)
        except Exception:  # noqa: BLE001
            log.exception("image_read_for_rerun_failed", image_id=image_id)
            return None
        await self._analyze(
            record, payload, record.mime_type,
            data_url=_to_data_url(payload, record.mime_type),
            image_text_hint=image_text_hint,
        )
        return await self._repo.get(image_id)

    async def list_for_conversation(
        self, user_id: str, conversation_id: str
    ) -> list[ImageRecord]:
        return await self._repo.list_by_conversation(user_id, conversation_id)


def _to_data_url(payload: bytes, mime: str) -> str:
    import base64

    b64 = base64.b64encode(payload).decode("ascii")
    return f"data:{mime};base64,{b64}"
