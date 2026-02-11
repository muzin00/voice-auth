"""Domain models."""

from voiceauth.domain.models.speaker import Speaker
from voiceauth.domain.models.voiceprint import EMBEDDING_DIM, Voiceprint

__all__ = ["Speaker", "Voiceprint", "EMBEDDING_DIM"]
