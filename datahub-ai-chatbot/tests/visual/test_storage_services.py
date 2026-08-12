"""Tests for the image storage + upload + context services.

Covers:
  * ImageStorageService filesystem persistence / thumbnails / deletion;
  * ImageContextManager build + round-trip via context_from_dict;
  * VisionCache upsert/get-by-hash;
  * ConversationContextManager resolve_active (anaphora) + restore from DB.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.services.conversation_context import ConversationContextManager
from app.services.image_context import (
    ImageContext,
    ImageContextManager,
    context_from_dict,
)
from app.services.image_storage import (
    ImageStorageService,
    ImageTooLargeError,
    UnsupportedImageTypeError,
    compute_content_hash,
)
from app.services.image_upload import ImageUploadService
from app.services.vision_cache import VisionCache
from database.models import ImageRecord, ImageStatus


def _png_bytes(size: int = 8) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), color=(10, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _png_data_url(size: int = 8) -> str:
    import base64

    payload = _png_bytes(size)
    return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")


# --------------------------------------------------------------------------- #
# ImageStorageService
# --------------------------------------------------------------------------- #
def test_storage_save_and_read(tmp_path: Path) -> None:
    service = ImageStorageService(root=tmp_path)
    payload = _png_bytes()
    info = service.save("user1", "img1", payload, "image/png", "capture.png")
    assert info["storage_path"].endswith("original.png")
    assert info["thumbnail_path"] is not None
    assert info["thumbnail_path"].endswith("thumb.jpg")
    assert service.read_bytes(info["storage_path"]) == payload
    thumb = service.read_bytes(info["thumbnail_path"])
    assert thumb[:2] == b"\xff\xd8"  # JPEG magic


def test_storage_unsupported_type(tmp_path: Path) -> None:
    service = ImageStorageService(root=tmp_path)
    with pytest.raises(UnsupportedImageTypeError):
        service.save("u", "i", b"x" * 4, "text/plain", "f.txt")


def test_storage_too_large(tmp_path: Path) -> None:
    service = ImageStorageService(root=tmp_path)
    with pytest.raises(ImageTooLargeError):
        service.save("u", "i", b"x" * 20_000_000, "image/png", "big.png")


def test_storage_delete_and_purge(tmp_path: Path) -> None:
    service = ImageStorageService(root=tmp_path)
    info = service.save("user1", "img2", _png_bytes(), "image/png", None)
    service.delete_files([info["storage_path"], info["thumbnail_path"]])
    assert not (tmp_path / info["storage_path"]).exists()
    service.save("user1", "img3", _png_bytes(), "image/png", None)
    service.purge_directory("user1", "img3")
    assert not (tmp_path / "user1" / "img3").exists()


def test_content_hash_stable() -> None:
    payload = _png_bytes()
    assert compute_content_hash(payload) == compute_content_hash(payload)
    assert compute_content_hash(payload) != compute_content_hash(b"other")


# --------------------------------------------------------------------------- #
# ImageContextManager
# --------------------------------------------------------------------------- #
def test_context_build_maps_fields() -> None:
    mgr = ImageContextManager()
    ctx = mgr.build(
        "i1", "u1", "c1", "shot.png",
        {
            "image_type": "table",
            "ocr_text": "order_id customer_id",
            "detected_entities": [{"name": "orders", "type": "dataset"}],
            "detected_tables": ["sales.orders"],
            "detected_columns": ["order_id", "customer_id"],
            "detected_metrics": ["revenue"],
            "confidence": 0.9,
            "parse_error": False,
        },
    )
    assert ctx.image_id == "i1"
    assert ctx.image_type == "table"
    assert ctx.dataset_name == "orders"  # from dataset entity
    assert ctx.detected_columns == ["order_id", "customer_id"]
    assert ctx.confidence == 0.9


def test_context_from_dict_roundtrip() -> None:
    mgr = ImageContextManager()
    ctx = mgr.build("i2", "u2", None, "a.png", {"image_type": "dashboard"})
    restored = context_from_dict(ctx.to_dict())
    assert restored.image_id == ctx.image_id
    assert restored.image_type == ctx.image_type
    assert restored.dataset_name == ctx.dataset_name


# --------------------------------------------------------------------------- #
# VisionCache
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_vision_cache_roundtrip(db_session) -> None:
    cache = VisionCache(db_session)
    assert await cache.get("hashA") is None
    await cache.put("hashA", model_id="m1", vision_result={"ocr_text": "x"}, image_context=None)
    got = await cache.get("hashA")
    assert got is not None
    assert got["vision_result"]["ocr_text"] == "x"
    assert got["model_id"] == "m1"
    # upsert updates in place, still one row
    await cache.put("hashA", model_id="m2", vision_result={"ocr_text": "y"}, image_context=None)
    from sqlalchemy import select

    from database.models import VisionCacheRecord

    rows = list(
        (await db_session.execute(
            select(VisionCacheRecord).where(VisionCacheRecord.content_hash == "hashA")
        )).scalars().all()
    )
    assert len(rows) == 1
    assert rows[0].model_id == "m2"


# --------------------------------------------------------------------------- #
# ConversationContextManager
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_conv_context_resolve_single(db_session) -> None:
    mgr = ConversationContextManager(db_session)
    ctx = ImageContext(image_id="i1", user_id="u1", conversation_id="c1",
                       file_name="shot.png", dataset_name="sales.orders")
    mgr.bind("u1", "c1", [ctx])
    active, needs = mgr.resolve_active("dataset này dùng ở đâu?", "u1", "c1")
    assert active is not None
    assert active.image_id == "i1"
    assert needs is False


@pytest.mark.asyncio
async def test_conv_context_restore_from_db(db_session) -> None:
    rec = ImageRecord(
        image_id="i9",
        user_id="u9",
        conversation_id="c9",
        original_filename="a.png",
        filename="a.png",
        mime_type="image/png",
        size=10,
        storage_path="u9/i9/original.png",
        status=ImageStatus.ANALYZED.value,
        content_hash="h",
        image_context={
            "image_id": "i9", "user_id": "u9", "conversation_id": "c9",
            "image_type": "dashboard", "file_name": "a.png",
            "ocr_text": "revenue", "dataset_name": "finance.monthly_revenue",
        },
    )
    db_session.add(rec)
    await db_session.commit()

    mgr = ConversationContextManager(db_session)
    contexts = await mgr.load("u9", "c9")
    assert len(contexts) == 1
    assert contexts[0].dataset_name == "finance.monthly_revenue"


@pytest.mark.asyncio
async def test_upload_persists_and_analyzes_mock(db_session, tmp_path: Path, monkeypatch) -> None:
    from config.settings import settings

    monkeypatch.setattr(settings, "IMAGE_STORAGE_PATH", str(tmp_path / "images"))
    monkeypatch.setattr(settings, "FIREWORKS_API_KEY", "")
    monkeypatch.setattr(settings, "USE_MOCK_LLM", True)

    service = ImageUploadService(db_session)
    record = await service.upload_from_data_url(
        _png_data_url(), "u1", "c1", image_text_hint="orders revenue",
    )
    assert record.image_id
    assert record.status == ImageStatus.ANALYZED.value
    assert record.mime_type == "image/png"
    # context should have been built and persisted
    refetched = await service._repo.get(record.image_id)
    assert refetched is not None
    assert refetched.image_context is not None
    assert refetched.vision_result is not None
