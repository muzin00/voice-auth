from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session
from vca_core.services import SpeakerService
from vca_store.repositories import SpeakerRepository
from vca_store.session import get_session


def get_speaker_service(
    session: Session = Depends(get_session),
) -> Generator[SpeakerService, None, None]:
    repository = SpeakerRepository(session)
    service = SpeakerService(repository)
    yield service
