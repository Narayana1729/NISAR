from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

class ObjectStorageInterface(ABC):
    """
    Abstract interface for object storage operations (e.g., S3, GCS, Azure Blob).
    Allows future cloud storage integration without changing downstream services.
    """

    @abstractmethod
    def upload_file(self, file_obj: BinaryIO, destination_key: str, content_type: Optional[str] = None) -> str:
        """Upload a file stream to cloud object storage."""
        pass

    @abstractmethod
    def download_file(self, source_key: str) -> BinaryIO:
        """Download a file stream from cloud object storage."""
        pass

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """Delete an object by key."""
        pass

    @abstractmethod
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a temporary pre-signed URL for direct access."""
        pass


class CloudObjectStorageAdapter(ObjectStorageInterface):
    """Placeholder adapter for future cloud object storage integration."""

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or "nisar-default-bucket"

    def upload_file(self, file_obj: BinaryIO, destination_key: str, content_type: Optional[str] = None) -> str:
        raise NotImplementedError("Cloud object storage is not configured yet. Use LocalStorageAdapter.")

    def download_file(self, source_key: str) -> BinaryIO:
        raise NotImplementedError("Cloud object storage is not configured yet. Use LocalStorageAdapter.")

    def delete_file(self, key: str) -> bool:
        raise NotImplementedError("Cloud object storage is not configured yet. Use LocalStorageAdapter.")

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("Cloud object storage is not configured yet. Use LocalStorageAdapter.")
