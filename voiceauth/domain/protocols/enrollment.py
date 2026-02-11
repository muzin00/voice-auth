"""Protocols for enrollment service."""

from typing import Protocol

import numpy as np

from voiceauth.domain.models import Speaker, Voiceprint


class EnrollmentAudioProcessorProtocol(Protocol):
    """Protocol for audio processor dependency in enrollment."""

    def process_webm(self, webm_data: bytes) -> tuple[np.ndarray, int]:
        """Convert webm audio to PCM array."""
        ...

    def process_enrollment_audio(
        self,
        audio: np.ndarray,
        expected_prompt: str,
    ) -> "ProcessingResultProtocol":
        """Process audio for enrollment."""
        ...


class ProcessingResultProtocol(Protocol):
    """Protocol for processing result."""

    @property
    def asr_text(self) -> str:
        """Get ASR text."""
        ...

    @property
    def digits(self) -> str:
        """Get recognized digits."""
        ...

    @property
    def utterance_embedding(self) -> np.ndarray:
        """Get utterance-level embedding."""
        ...


class EnrollmentSpeakerStoreProtocol(Protocol):
    """Protocol for speaker store dependency in enrollment."""

    def speaker_exists(self, speaker_id: str) -> bool:
        """Check if speaker exists."""
        ...

    def create_speaker(
        self,
        speaker_id: str,
        speaker_name: str | None = None,
        pin_hash: str | None = None,
    ) -> Speaker:
        """Create a new speaker."""
        ...

    def add_voiceprint(
        self,
        speaker_id: str,
        embedding: np.ndarray,
    ) -> Voiceprint:
        """Add or update a voiceprint."""
        ...

    def update_speaker_pin(self, speaker_id: str, pin_hash: str | None) -> Speaker:
        """Update speaker PIN."""
        ...
