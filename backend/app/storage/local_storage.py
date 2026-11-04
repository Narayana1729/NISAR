from pathlib import Path
import shutil
from typing import BinaryIO, Optional

class LocalStorageAdapter:
    """
    Local filesystem storage adapter.
    Operates strictly within the configured root directory to prevent path traversal.
    """

    def __init__(self, base_dir: str):
        self.base_path = Path(base_dir).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path ensuring it does not traverse outside the base directory."""
        target_path = (self.base_path / relative_path).resolve()
        if not str(target_path).startswith(str(self.base_path)):
            raise ValueError("Access denied: Path traversal detected outside storage root.")
        return target_path

    def save_file(self, file_obj: BinaryIO, relative_path: str) -> str:
        safe_path = self._resolve_safe_path(relative_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
        return relative_path

    def read_file(self, relative_path: str) -> bytes:
        safe_path = self._resolve_safe_path(relative_path)
        if not safe_path.exists() or not safe_path.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return safe_path.read_bytes()

    def exists(self, relative_path: str) -> bool:
        try:
            safe_path = self._resolve_safe_path(relative_path)
            return safe_path.exists()
        except ValueError:
            return False

    def delete_file(self, relative_path: str) -> bool:
        safe_path = self._resolve_safe_path(relative_path)
        if safe_path.exists() and safe_path.is_file():
            safe_path.unlink()
            return True
        return False
