from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_auth.repositories import SpeakerRepository, VoiceprintRepository
from vca_auth.services import AuthService
from vca_auth.settings import auth_settings
from vca_engine import VoiceprintService, get_speaker_extractor
from vca_infra.database import get_session


def get_auth_service(
    session: Session = Depends(get_session),
) -> Generator[AuthService, None, None]:
    """AuthServiceを提供する."""
    speaker_repository = SpeakerRepository(session)
    voiceprint_repository = VoiceprintRepository(session)

    # サービスを直接生成
    speaker_extractor = get_speaker_extractor()
    voiceprint_service = VoiceprintService(speaker_extractor)

    service = AuthService(
        speaker_repository=speaker_repository,
        voiceprint_repository=voiceprint_repository,
        voiceprint_engine=voiceprint_service,
        voice_similarity_threshold=auth_settings.VOICE_SIMILARITY_THRESHOLD,
    )
    yield service
