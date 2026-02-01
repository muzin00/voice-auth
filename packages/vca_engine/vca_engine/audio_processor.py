"""Audio processor facade."""

from dataclasses import dataclass, field

import numpy as np

from .asr import ASRResult, extract_digit_timestamps
from .audio_converter import webm_to_pcm
from .exceptions import (
    ASRError,
    AudioTooLongError,
    AudioTooShortError,
    NoSpeechDetectedError,
    VCAEngineError,
)
from .model_loader import get_asr, get_vad, get_voiceprint_extractor
from .segmentation import DigitSegment, segment_by_timestamps
from .settings import settings
from .voiceprint import cosine_similarity


@dataclass
class ProcessingResult:
    """Result of processing enrollment audio."""

    asr_text: str  # Raw ASR text
    digits: str  # Normalized digit string
    digit_embeddings: dict[str, np.ndarray]  # digit -> 192-dim vector
    segments: list[DigitSegment]


@dataclass
class VerificationResult:
    """Result of voice verification."""

    asr_text: str
    asr_matched: bool
    digit_scores: dict[str, float] = field(default_factory=dict)
    average_score: float = 0.0
    authenticated: bool = False


class AudioProcessor:
    """Facade for audio processing pipeline.

    This class provides a unified interface for:
    - WebM to PCM conversion
    - Voice Activity Detection
    - Automatic Speech Recognition
    - Speaker Embedding Extraction
    - Audio Segmentation
    """

    def process_webm(self, webm_data: bytes) -> tuple[np.ndarray, int]:
        """Convert WebM audio to PCM numpy array.

        Args:
            webm_data: Raw WebM audio bytes.

        Returns:
            Tuple of (audio samples as float32 numpy array, sample rate).
        """
        return webm_to_pcm(webm_data)

    def detect_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            True if speech is detected, False otherwise.
        """
        return get_vad().is_speech(audio)

    def recognize(self, audio: np.ndarray) -> ASRResult:
        """Recognize speech from audio.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            ASRResult with text and token timestamps.
        """
        return get_asr().recognize(audio)

    def extract_embedding(self, audio: np.ndarray) -> np.ndarray:
        """Extract speaker embedding from audio.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            Speaker embedding as float32 numpy array (192 dimensions).
        """
        return get_voiceprint_extractor().extract(audio)

    def validate_audio_duration(self, audio: np.ndarray) -> None:
        """Validate audio duration.

        Args:
            audio: Audio samples as numpy array.

        Raises:
            AudioTooShortError: If audio is shorter than minimum duration.
            AudioTooLongError: If audio is longer than maximum duration.
        """
        duration = len(audio) / settings.target_sample_rate

        if duration < settings.min_audio_duration:
            raise AudioTooShortError(
                f"Audio duration ({duration:.2f}s) is less than minimum "
                f"({settings.min_audio_duration}s)"
            )

        if duration > settings.max_audio_duration:
            raise AudioTooLongError(
                f"Audio duration ({duration:.2f}s) exceeds maximum "
                f"({settings.max_audio_duration}s)"
            )

    def process_enrollment_audio(
        self,
        audio: np.ndarray,
        expected_prompt: str,
    ) -> ProcessingResult:
        """Process audio for enrollment.

        This method:
        1. Validates audio duration
        2. Checks for speech presence
        3. Performs ASR
        4. Validates ASR result matches expected prompt
        5. Segments audio by digit timestamps
        6. Extracts speaker embeddings for each digit

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).
            expected_prompt: Expected digit string (e.g., "4326").

        Returns:
            ProcessingResult with ASR text, digits, and embeddings.

        Raises:
            AudioTooShortError: If audio is too short.
            AudioTooLongError: If audio is too long.
            NoSpeechDetectedError: If no speech is detected.
            ASRError: If ASR result doesn't match expected prompt.
        """
        # Validate duration
        self.validate_audio_duration(audio)

        # Check for speech
        if not self.detect_speech(audio):
            raise NoSpeechDetectedError("No speech detected in audio")

        # Perform ASR
        asr_result = self.recognize(audio)

        # Validate ASR matches prompt
        if asr_result.normalized_text != expected_prompt:
            raise ASRError(
                f"ASR result '{asr_result.normalized_text}' does not match "
                f"expected prompt '{expected_prompt}'"
            )

        # Extract digit timestamps
        timestamps = extract_digit_timestamps(asr_result)

        # Segment audio
        segments = segment_by_timestamps(audio, timestamps)

        # Extract embeddings for each digit
        digit_embeddings: dict[str, np.ndarray] = {}
        for segment in segments:
            embedding = self.extract_embedding(segment.audio)
            digit_embeddings[segment.digit] = embedding

        return ProcessingResult(
            asr_text=asr_result.text,
            digits=asr_result.normalized_text,
            digit_embeddings=digit_embeddings,
            segments=segments,
        )

    def verify_audio(
        self,
        audio: np.ndarray,
        expected_prompt: str,
        registered_embeddings: dict[str, np.ndarray],
    ) -> VerificationResult:
        """Verify audio against registered speaker embeddings.

        This method:
        1. Validates audio duration
        2. Checks for speech presence
        3. Performs ASR
        4. Validates ASR result matches expected prompt
        5. Segments audio by digit timestamps
        6. Compares each digit's embedding with registered embeddings
        7. Calculates average similarity score

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).
            expected_prompt: Expected digit string (e.g., "4326").
            registered_embeddings: Dictionary of digit -> registered embedding.

        Returns:
            VerificationResult with authentication result.
        """
        try:
            # Validate duration
            self.validate_audio_duration(audio)

            # Check for speech
            if not self.detect_speech(audio):
                return VerificationResult(
                    asr_text="",
                    asr_matched=False,
                )

            # Perform ASR
            asr_result = self.recognize(audio)

            # Check ASR match
            if asr_result.normalized_text != expected_prompt:
                return VerificationResult(
                    asr_text=asr_result.text,
                    asr_matched=False,
                )

            # Extract digit timestamps
            timestamps = extract_digit_timestamps(asr_result)

            # Segment audio
            segments = segment_by_timestamps(audio, timestamps)

            # Compare embeddings
            digit_scores: dict[str, float] = {}
            for segment in segments:
                if segment.digit not in registered_embeddings:
                    continue

                embedding = self.extract_embedding(segment.audio)
                registered = registered_embeddings[segment.digit]
                score = cosine_similarity(embedding, registered)
                digit_scores[segment.digit] = score

            # Calculate average score
            if digit_scores:
                average_score = sum(digit_scores.values()) / len(digit_scores)
            else:
                average_score = 0.0

            # Determine authentication result
            authenticated = (
                len(digit_scores) == len(expected_prompt)
                and average_score >= settings.speaker_similarity_threshold
            )

            return VerificationResult(
                asr_text=asr_result.text,
                asr_matched=True,
                digit_scores=digit_scores,
                average_score=average_score,
                authenticated=authenticated,
            )

        except VCAEngineError:
            raise
        except Exception:
            return VerificationResult(
                asr_text="",
                asr_matched=False,
            )


# Global processor instance
_processor: AudioProcessor | None = None


def get_processor() -> AudioProcessor:
    """Get the global audio processor instance."""
    global _processor
    if _processor is None:
        _processor = AudioProcessor()
    return _processor
