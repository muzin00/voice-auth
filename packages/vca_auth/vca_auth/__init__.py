"""VCA Auth package for voice-based authentication."""

from vca_auth.models import EMBEDDING_DIM, DigitVoiceprint, Speaker
from vca_auth.repositories import (
    SpeakerAlreadyExistsError,
    SpeakerNotFoundError,
    SpeakerRepository,
)

__all__ = [
    "Speaker",
    "DigitVoiceprint",
    "EMBEDDING_DIM",
    "SpeakerRepository",
    "SpeakerNotFoundError",
    "SpeakerAlreadyExistsError",
]
