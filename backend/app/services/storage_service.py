from typing import BinaryIO, Optional
from app.config import settings
from app.storage.local_storage import LocalStorageAdapter
from app.storage.object_storage import CloudObjectStorageAdapter

class StorageService:
    """
    Unified storage service interface. Defaults to LocalStorageAdapter
    and supports switching to CloudObjectStorageAdapter when configured.
    """

    def __init__(self, use_cloud: bool = False):
        self.use_cloud = use_cloud
        self.local_adapter = LocalStorageAdapter(settings.DATA_ROOT_DIR)
        self.cloud_adapter = CloudObjectStorageAdapter()

    def store_file(self, file_obj: BinaryIO, relative_path: str) -> str:
        if self.use_cloud:
            return self.cloud_adapter.upload_file(file_obj, relative_path)
        return self.local_adapter.save_file(file_obj, relative_path)

    def retrieve_file(self, relative_path: str) -> bytes:
        if self.use_cloud:
            stream = self.cloud_adapter.download_file(relative_path)
            return stream.read()
        return self.local_adapter.read_file(relative_path)

    def file_exists(self, relative_path: str) -> bool:
        if self.use_cloud:
            return False
        return self.local_adapter.exists(relative_path)

    def remove_file(self, relative_path: str) -> bool:
        if self.use_cloud:
            return self.cloud_adapter.delete_file(relative_path)
        return self.local_adapter.delete_file(relative_path)

storage_service = StorageService()
