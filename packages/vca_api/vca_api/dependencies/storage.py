from vca_core.interfaces.storage import StorageProtocol
from vca_store.settings import storage_settings
from vca_store.storages import GCSStorage, LocalStorage


def get_storage() -> StorageProtocol:
    """ストレージを提供する."""
    if storage_settings.STORAGE_TYPE == "gcs":
        if not storage_settings.GCS_BUCKET_NAME:
            raise ValueError("GCS_BUCKET_NAME must be set when STORAGE_TYPE is 'gcs'")
        if not storage_settings.GCS_PROJECT_ID:
            raise ValueError("GCS_PROJECT_ID must be set when STORAGE_TYPE is 'gcs'")
        return GCSStorage(
            bucket_name=storage_settings.GCS_BUCKET_NAME,
            project_id=storage_settings.GCS_PROJECT_ID,
        )
    return LocalStorage()
