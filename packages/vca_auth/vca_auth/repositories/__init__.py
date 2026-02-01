"""VCA Auth repositories package."""

from vca_auth.repositories.speaker_repository import (
    SpeakerAlreadyExistsError,
    SpeakerNotFoundError,
    SpeakerRepository,
)

__all__ = ["SpeakerRepository", "SpeakerNotFoundError", "SpeakerAlreadyExistsError"]
