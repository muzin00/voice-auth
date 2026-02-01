"""VCA Auth models package."""

from vca_auth.models.digit_voiceprint import EMBEDDING_DIM, DigitVoiceprint
from vca_auth.models.speaker import Speaker

__all__ = ["Speaker", "DigitVoiceprint", "EMBEDDING_DIM"]
