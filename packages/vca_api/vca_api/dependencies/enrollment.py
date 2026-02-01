"""声紋登録依存性."""

from fastapi import Depends
from sqlmodel import Session
from vca_auth.repositories import SpeakerRepository, VoiceprintRepository
from vca_auth.services import EnrollmentService
from vca_infra.database import get_session


def get_enrollment_service(
    session: Session = Depends(get_session),
) -> EnrollmentService:
    """EnrollmentServiceを提供する."""
    speaker_repository = SpeakerRepository(session)
    voiceprint_repository = VoiceprintRepository(session)

    return EnrollmentService(
        speaker_repository=speaker_repository,
        voiceprint_repository=voiceprint_repository,
    )
