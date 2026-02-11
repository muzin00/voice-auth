"""Voiceprint extraction Protocol."""

from typing import Protocol

import numpy as np


class VoiceprintProtocol(Protocol):
    """Protocol for Voiceprint extraction."""

    def load(self) -> None:
        """Load the voiceprint model."""
        ...

    @property
    def embedding_dim(self) -> int:
        """Get the dimension of voiceprint embeddings."""
        ...

    def extract(
        self,
        audio: np.ndarray,
        sample_rate: int | None = None,
    ) -> np.ndarray:
        """Extract voiceprint from audio.

        Args:
            audio: Audio samples as float32 numpy array.
            sample_rate: Sample rate of audio.

        Returns:
            Voiceprint as float32 numpy array.
        """
        ...
