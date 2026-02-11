"""VAD (Voice Activity Detection) Protocol."""

from typing import Protocol

import numpy as np


class VADProtocol(Protocol):
    """Protocol for Voice Activity Detection."""

    def load(self) -> None:
        """Load the VAD model."""
        ...

    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            True if speech is detected, False otherwise.
        """
        ...

    def get_speech_segments(self, audio: np.ndarray) -> list[tuple[float, float]]:
        """Get speech segments from audio.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            List of (start_sec, end_sec) tuples for speech segments.
        """
        ...

    def extract_speech(self, audio: np.ndarray) -> np.ndarray:
        """Extract speech segments from audio.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            Concatenated speech segments as float32 numpy array.

        Raises:
            Exception: If no speech is detected.
        """
        ...
