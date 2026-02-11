"""ASR (Automatic Speech Recognition) Protocol."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class TokenInfo:
    """Information about a recognized token."""

    token: str
    start_time: float  # seconds
    end_time: float  # seconds


@dataclass
class ASRResult:
    """Result of automatic speech recognition."""

    text: str  # Raw recognized text
    normalized_text: str  # Normalized text (digits only)
    tokens: list[TokenInfo]  # Token information with timestamps


class ASRProtocol(Protocol):
    """Protocol for Automatic Speech Recognition."""

    def load(self) -> None:
        """Load the ASR model."""
        ...

    def recognize(
        self, audio: np.ndarray, sample_rate: int | None = None
    ) -> ASRResult:
        """Recognize speech from audio.

        Args:
            audio: Audio samples as float32 numpy array.
            sample_rate: Sample rate of audio.

        Returns:
            ASRResult with recognized text and token timestamps.
        """
        ...

    def get_digit_tokens(self, asr_result: ASRResult) -> list[TokenInfo]:
        """Extract tokens that correspond to digits.

        Args:
            asr_result: ASR result with tokens.

        Returns:
            List of TokenInfo for digit tokens only.
        """
        ...
