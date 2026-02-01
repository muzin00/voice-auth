from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_auth.repositories import SpeakerRepository
from vca_auth.services import SpeakerService
from vca_infra.database import get_session


def get_speaker_service(
    session: Session = Depends(get_session),
) -> Generator[SpeakerService, None, None]:
    repository = SpeakerRepository(session)
    service = SpeakerService(repository)
    yield service
