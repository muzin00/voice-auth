from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_core.interfaces.storage import StorageProtocol
from vca_core.services.auth_service import AuthService
from vca_infra.model_loader import get_speaker_extractor
from vca_infra.repositories import (
    SpeakerRepository,
    VoiceprintRepository,
    VoiceSampleRepository,
)
from vca_infra.services import VoiceprintService
from vca_infra.session import get_session
from vca_infra.settings import voiceprint_settings

from vca_api.dependencies.storage import get_storage


def get_auth_service(
    session: Session = Depends(get_session),
    storage: StorageProtocol = Depends(get_storage),
) -> Generator[AuthService, None, None]:
    """AuthServiceを提供する."""
    speaker_repository = SpeakerRepository(session)
    voice_sample_repository = VoiceSampleRepository(session)
    voiceprint_repository = VoiceprintRepository(session)

    # サービスを直接生成
    speaker_extractor = get_speaker_extractor()
    voiceprint_service = VoiceprintService(speaker_extractor)

    service = AuthService(
        speaker_repository=speaker_repository,
        voice_sample_repository=voice_sample_repository,
        voiceprint_repository=voiceprint_repository,
        storage=storage,
        voiceprint_service=voiceprint_service,
        voice_similarity_threshold=voiceprint_settings.VOICEPRINT_SIMILARITY_THRESHOLD,
    )
    yield service
