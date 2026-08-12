"""Image Storage Service — real filesystem persistence for uploaded images.

Owns the on-disk lifecycle of image binaries and thumbnails. The database keeps
only metadata (see StorageRepository); the actual bytes live under
``settings.IMAGE_STORAGE_PATH``. This module is storage-only and knows nothing
about vision, context or conversations.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
import shutil
import uuid
from pathlib import Path

import structlog
from PIL import Image as PILImage

from config.settings import settings

log = structlog.get_logger()

_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


class ImageStorageError(Exception):
    pass


class UnsupportedImageTypeError(ImageStorageError):
    pass


class ImageTooLargeError(ImageStorageError):
    pass


def _safe_name(name: str | None) -> str:
    base = _UNSAFE_RE.sub("_", name or "image").strip("._") or "image"
    return base[:160]


def _ext_for_mime(mime: str, fallback: str = "png") -> str:
    if not mime:
        return fallback
    ext_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
        "image/svg+xml": "svg",
    }
    return ext_map.get(mime.strip().lower(), fallback)


def compute_content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def decode_data_url(data_url: str) -> tuple[str, bytes]:
    """Decode a ``data:image/png;base64,....`` URL into (mime_type, bytes)."""
    if not data_url or "," not in data_url:
        return "", b""
    header, _, b64 = data_url.partition(",")
    mime = "image/png"
    if ";" in header:
        meta = header.split(";")
        if meta[0].startswith("data:"):
            mime = meta[0][5:]
    try:
        payload = base64.b64decode(b64)
    except (binascii.Error, ValueError):
        return mime, b""
    return mime, payload


def _make_thumbnail(payload: bytes) -> bytes | None:
    """Generate a small JPEG thumbnail. Returns None on failure (non-fatal)."""
    try:
        opened = PILImage.open(io.BytesIO(payload))
        image = opened.convert("RGB")
        image.thumbnail((settings.IMAGE_THUMBNAIL_SIZE, settings.IMAGE_THUMBNAIL_SIZE))
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=settings.IMAGE_THUMBNAIL_QUALITY)
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - thumbnails never fail the upload
        log.warning("image_thumbnail_failed")
        return None


def _max_file_bytes() -> int:
    base = getattr(settings, "VISION_MAX_IMAGE_BYTES", 15 * 1024 * 1024)
    return base or (15 * 1024 * 1024)


def _validate(payload: bytes, mime: str) -> None:
    if not payload:
        raise ImageStorageError("Empty image payload")
    if len(payload) > _max_file_bytes():
        raise ImageTooLargeError("Image exceeds maximum storage size")
    if not mime.strip().lower().startswith("image/"):
        raise UnsupportedImageTypeError(f"Unsupported image type: {mime}")


class ImageStorageService:
    """Persist image binaries + thumbnails on the local filesystem.

    Layout::

        <IMAGE_STORAGE_PATH>/<user_id>/<image_id>/original.<ext>
        <IMAGE_STORAGE_PATH>/<user_id>/<image_id>/thumb.jpg
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or Path(settings.IMAGE_STORAGE_PATH)).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def _dir_for(self, user_id: str, image_id: str) -> Path:
        d = self._root / _safe_name(user_id) / image_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(
        self, user_id: str, image_id: str, payload: bytes, mime: str,
        original_filename: str | None,
    ) -> dict[str, str | None]:
        """Store the original + thumbnail; returns path metadata dict."""
        _validate(payload, mime)
        directory = self._dir_for(user_id, image_id)
        ext = _ext_for_mime(mime)
        original_name = _safe_name(original_filename) or f"image.{ext}"
        storage_name = f"original.{ext}"
        storage_path = directory / storage_name
        storage_path.write_bytes(payload)

        thumbnail_path = None
        thumb = _make_thumbnail(payload)
        if thumb:
            thumb_file = directory / "thumb.jpg"
            thumb_file.write_bytes(thumb)
            thumbnail_path = str(thumb_file.relative_to(self._root))

        return {
            "storage_path": str(storage_path.relative_to(self._root)),
            "thumbnail_path": thumbnail_path,
            "filename": original_name,
        }

    def read_bytes(self, relative_path: str) -> bytes:
        p = (self._root / relative_path).resolve()
        if not p.is_file():
            raise ImageStorageError(f"File not found: {relative_path}")
        return p.read_bytes()

    def delete_files(self, relative_paths: list[str]) -> None:
        for rel in relative_paths:
            if not rel:
                continue
            p = (self._root / rel).resolve()
            try:
                if p.is_file():
                    p.unlink()
            except OSError:  # noqa: BLE001
                log.warning("image_file_delete_failed", path=rel)

    def purge_directory(self, user_id: str, image_id: str) -> None:
        directory = self._root / _safe_name(user_id) / image_id
        try:
            if directory.is_dir():
                shutil.rmtree(directory, ignore_errors=True)
        except OSError:  # noqa: BLE001
            log.warning("image_dir_purge_failed", image_id=image_id)

    def move_to_trash(self, record_paths: list[str]) -> None:
        """Move stored files to the trash dir on soft-delete."""
        trash = (self._root / ".trash").resolve()
        trash.mkdir(parents=True, exist_ok=True)
        for rel in record_paths:
            if not rel:
                continue
            src = (self._root / rel).resolve()
            if not src.is_file():
                continue
            try:
                dst = trash / f"{uuid.uuid4().hex}_{src.name}"
                shutil.move(str(src), str(dst))
            except OSError:  # noqa: BLE001
                log.warning("image_move_to_trash_failed", path=rel)

    def restore_from_trash(self, relative_path: str) -> bool:
        """Best-effort: original path content cannot be recovered once moved, so
        this is a no-op that reports the file is unavailable."""
        return False
