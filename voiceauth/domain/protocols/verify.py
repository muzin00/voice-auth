"""Protocols for verification service."""

from typing import Protocol

import numpy as np

from voiceauth.domain.models import Speaker


class VerifyAudioProcessorProtocol(Protocol):
    """Protocol for audio processor dependency in verification."""

    def process_webm(self, webm_data: bytes) -> tuple[np.ndarray, int]:
        """Convert webm audio to PCM array."""
        ...

    def verify_audio(
        self,
        audio: np.ndarray,
        expected_prompt: str,
        registered_embedding: np.ndarray,
    ) -> "VerificationResultProtocol":
        """Verify audio against registered embedding."""
        ...


class VerificationResultProtocol(Protocol):
    """Protocol for verification result from audio processor."""

    @property
    def asr_text(self) -> str:
        """Get ASR text."""
        ...

    @property
    def asr_matched(self) -> bool:
        """Check if ASR matched expected prompt."""
        ...

    @property
    def similarity_score(self) -> float:
        """Get similarity score."""
        ...

    @property
    def authenticated(self) -> bool:
        """Check if authentication passed."""
        ...


class VerifySpeakerStoreProtocol(Protocol):
    """Protocol for speaker store dependency in verification."""

    def speaker_exists(self, speaker_id: str) -> bool:
        """Check if speaker exists."""
        ...

    def get_speaker_by_id(self, speaker_id: str) -> Speaker:
        """Get speaker by ID."""
        ...

    def get_voiceprint(self, speaker_id: str) -> np.ndarray:
        """Get voiceprint embedding for speaker."""
        ...
