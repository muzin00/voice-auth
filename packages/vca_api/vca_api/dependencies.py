"""Dependency injection for FastAPI."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine
from vca_auth.repositories.speaker_repository import SpeakerRepository
from vca_auth.services.enrollment_service import EnrollmentService
from vca_engine.audio_processor import AudioProcessor, get_processor
from vca_infra.settings import db_settings

# Database engine (singleton)
_engine = create_engine(db_settings.database_url, echo=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    with Session(_engine) as session:
        yield session


def get_audio_processor() -> AudioProcessor:
    """Get audio processor instance."""
    return get_processor()


def get_speaker_repository(
    session: Annotated[Session, Depends(get_db)],
) -> SpeakerRepository:
    """Get speaker repository with injected session."""
    return SpeakerRepository(session)


def get_enrollment_service(
    audio_processor: Annotated[AudioProcessor, Depends(get_audio_processor)],
    speaker_repository: Annotated[SpeakerRepository, Depends(get_speaker_repository)],
) -> EnrollmentService:
    """Get enrollment service with injected dependencies."""
    return EnrollmentService(
        audio_processor=audio_processor,
        speaker_repository=speaker_repository,
    )


# Type aliases for dependency injection
DbSession = Annotated[Session, Depends(get_db)]
AudioProcessorDep = Annotated[AudioProcessor, Depends(get_audio_processor)]
SpeakerRepositoryDep = Annotated[SpeakerRepository, Depends(get_speaker_repository)]
EnrollmentServiceDep = Annotated[EnrollmentService, Depends(get_enrollment_service)]
