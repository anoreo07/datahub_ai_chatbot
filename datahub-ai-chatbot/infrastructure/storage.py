import hashlib
from pathlib import Path

from config.settings import settings


class LocalStorage:
    def __init__(self) -> None:
        self._base = Path(settings.LOCAL_STORAGE_PATH)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, path: str, content: bytes) -> str:
        full_path = self._base / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return str(full_path)

    def read(self, path: str) -> bytes | None:
        full_path = self._base / path
        if not full_path.exists():
            return None
        return full_path.read_bytes()

    def exists(self, path: str) -> bool:
        return (self._base / path).exists()

    def delete(self, path: str) -> bool:
        full_path = self._base / path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
