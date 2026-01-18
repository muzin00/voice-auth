from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_core.interfaces.storage import StorageProtocol
from vca_core.interfaces.worker_client import WorkerClientProtocol
from vca_core.services.auth_service import AuthService
from vca_infra.repositories import (
    PassphraseRepository,
    SpeakerRepository,
    VoiceprintRepository,
    VoiceSampleRepository,
)
from vca_infra.session import get_session

from vca_api.dependencies.storage import get_storage
from vca_api.dependencies.worker import get_worker_client


def get_auth_service(
    session: Session = Depends(get_session),
    storage: StorageProtocol = Depends(get_storage),
    worker_client: WorkerClientProtocol = Depends(get_worker_client),
) -> Generator[AuthService, None, None]:
    """AuthServiceを提供する."""
    speaker_repository = SpeakerRepository(session)
    voice_sample_repository = VoiceSampleRepository(session)
    voiceprint_repository = VoiceprintRepository(session)
    passphrase_repository = PassphraseRepository(session)

    service = AuthService(
        speaker_repository=speaker_repository,
        voice_sample_repository=voice_sample_repository,
        voiceprint_repository=voiceprint_repository,
        passphrase_repository=passphrase_repository,
        storage=storage,
        worker_client=worker_client,
    )
    yield service
