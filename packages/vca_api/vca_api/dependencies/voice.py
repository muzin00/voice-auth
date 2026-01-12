from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_core.interfaces.storage import StorageProtocol
from vca_core.services.voice_service import VoiceService
from vca_store.repositories.voice_repository import VoiceRepository
from vca_store.session import get_session
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


def get_voice_service(
    session: Session = Depends(get_session),
    storage: StorageProtocol = Depends(get_storage),
) -> Generator[VoiceService, None, None]:
    repository = VoiceRepository(session)
    service = VoiceService(repository, storage)
    yield service
