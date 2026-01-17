from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_core.interfaces.storage import StorageProtocol
from vca_core.services.auth_service import AuthService
from vca_store.repositories import (
    PassphraseRepository,
    SpeakerRepository,
    VoiceprintRepository,
    VoiceSampleRepository,
)
from vca_store.session import get_session

from vca_api.dependencies.voice import get_storage


def get_auth_service(
    session: Session = Depends(get_session),
    storage: StorageProtocol = Depends(get_storage),
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
    )
    yield service
