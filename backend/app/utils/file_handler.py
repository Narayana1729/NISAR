import uuid
from typing import BinaryIO
from app.storage.local_storage import LocalStorageAdapter
from app.utils.validation import sanitize_filename, validate_file_extension, validate_file_size
from app.config import settings

class FileHandler:
    """Helper to process incoming uploads and stage them safely."""

    def __init__(self, storage_adapter: LocalStorageAdapter):
        self.storage = storage_adapter

    def save_upload(self, file_obj: BinaryIO, original_filename: str, file_size: int, subfolder: str = "staging/uploads") -> str:
        if not validate_file_extension(original_filename):
            raise ValueError(f"Unsupported file format. Allowed: {settings.ALLOWED_EXTENSIONS}")

        if not validate_file_size(file_size):
            raise ValueError(f"File size exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes.")

        clean_name = sanitize_filename(original_filename)
        unique_prefix = str(uuid.uuid4())[:8]
        relative_path = f"{subfolder}/{unique_prefix}_{clean_name}"

        return self.storage.save_file(file_obj, relative_path)
