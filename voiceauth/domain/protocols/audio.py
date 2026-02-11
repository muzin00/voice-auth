"""Audio processing Protocol."""

from typing import Protocol

import numpy as np


class AudioConverterProtocol(Protocol):
    """Protocol for audio format conversion."""

    def webm_to_pcm(self, webm_data: bytes) -> tuple[np.ndarray, int]:
        """Convert webm audio bytes to PCM numpy array.

        Args:
            webm_data: Raw webm audio bytes.

        Returns:
            Tuple of (audio samples as float32 numpy array, sample rate).
        """
        ...

    def load_wav_file(self, file_path: str) -> tuple[np.ndarray, int]:
        """Load a WAV file and return PCM samples.

        Args:
            file_path: Path to the WAV file.

        Returns:
            Tuple of (audio samples as float32 numpy array, sample rate).
        """
        ...

    def resample_audio(
        self,
        audio: np.ndarray,
        original_sr: int,
        target_sr: int | None = None,
    ) -> np.ndarray:
        """Resample audio to target sample rate.

        Args:
            audio: Input audio samples as float32 numpy array.
            original_sr: Original sample rate.
            target_sr: Target sample rate.

        Returns:
            Resampled audio as float32 numpy array.
        """
        ...

    def ensure_mono(self, audio: np.ndarray) -> np.ndarray:
        """Ensure audio is mono (single channel).

        Args:
            audio: Input audio, possibly stereo.

        Returns:
            Mono audio as float32 numpy array.
        """
        ...
