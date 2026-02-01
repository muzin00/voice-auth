"""Enrollment service for speaker registration.

Manages the enrollment flow:
1. Generate prompts
2. Process audio for each prompt (with retries)
3. Accumulate embeddings
4. Calculate centroids
5. Register PIN
6. Save to database
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol

import numpy as np

from .prompt_generator import generate_enrollment_prompts

if TYPE_CHECKING:
    from vca_auth.models import DigitVoiceprint, Speaker


class AudioProcessorProtocol(Protocol):
    """Protocol for audio processor dependency."""

    def process_webm(self, webm_data: bytes) -> tuple[np.ndarray, int]: ...

    def process_enrollment_audio(
        self,
        audio: np.ndarray,
        expected_prompt: str,
    ) -> "ProcessingResultProtocol": ...


class ProcessingResultProtocol(Protocol):
    """Protocol for processing result."""

    @property
    def asr_text(self) -> str: ...

    @property
    def digits(self) -> str: ...

    @property
    def digit_embeddings(self) -> dict[str, np.ndarray]: ...


class SpeakerRepositoryProtocol(Protocol):
    """Protocol for speaker repository dependency."""

    def speaker_exists(self, speaker_id: str) -> bool: ...

    def create_speaker(
        self,
        speaker_id: str,
        speaker_name: str | None = None,
        pin_hash: str | None = None,
    ) -> "Speaker": ...

    def add_voiceprints_bulk(
        self,
        speaker_id: str,
        embeddings: dict[str, np.ndarray],
    ) -> list["DigitVoiceprint"]: ...

    def update_speaker_pin(self, speaker_id: str, pin_hash: str | None) -> "Speaker": ...


class EnrollmentState(Enum):
    """States for the enrollment flow."""

    INITIAL = "initial"
    PROMPTS_SENT = "prompts_sent"
    RECORDING = "recording"
    COMPLETED_VOICE = "completed_voice"
    AWAITING_PIN = "awaiting_pin"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EnrollmentSession:
    """Enrollment session state."""

    speaker_id: str
    speaker_name: str | None = None
    state: EnrollmentState = EnrollmentState.INITIAL
    prompts: list[str] = field(default_factory=list)
    current_set_index: int = 0
    retry_count: int = 0
    max_retries: int = 5
    # Accumulated embeddings: digit -> list of embeddings
    accumulated_embeddings: dict[str, list[np.ndarray]] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class ASRResultInfo:
    """Information about ASR result."""

    success: bool
    asr_text: str
    expected_prompt: str
    set_index: int
    remaining_sets: int
    retry_count: int
    max_retries: int
    message: str


@dataclass
class EnrollmentResult:
    """Final enrollment result."""

    speaker_id: str
    registered_digits: list[str]
    has_pin: bool
    status: str


class EnrollmentService:
    """Service for managing speaker enrollment."""

    def __init__(
        self,
        audio_processor: AudioProcessorProtocol,
        speaker_repository: SpeakerRepositoryProtocol,
    ) -> None:
        """Initialize enrollment service.

        Args:
            audio_processor: Audio processor for voice processing.
            speaker_repository: Repository for speaker database operations.
        """
        self.audio_processor = audio_processor
        self.speaker_repository = speaker_repository

    def start_enrollment(
        self,
        speaker_id: str,
        speaker_name: str | None = None,
    ) -> EnrollmentSession:
        """Start a new enrollment session.

        Args:
            speaker_id: Unique identifier for the speaker.
            speaker_name: Optional display name.

        Returns:
            New EnrollmentSession with generated prompts.

        Raises:
            SpeakerAlreadyExistsError: If speaker_id already exists.
        """
        if self.speaker_repository.speaker_exists(speaker_id):
            from vca_auth.repositories.speaker_repository import (
                SpeakerAlreadyExistsError,
            )

            raise SpeakerAlreadyExistsError(f"Speaker '{speaker_id}' already exists")

        # Initialize embeddings dict for digits 0-9
        accumulated = {str(d): [] for d in range(10)}

        session = EnrollmentSession(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            prompts=generate_enrollment_prompts(),
            accumulated_embeddings=accumulated,
            state=EnrollmentState.PROMPTS_SENT,
        )

        return session

    def process_audio(
        self,
        session: EnrollmentSession,
        audio_data: bytes,
    ) -> ASRResultInfo:
        """Process audio for current prompt.

        Args:
            session: Current enrollment session.
            audio_data: WebM audio bytes.

        Returns:
            ASRResultInfo with processing result.
        """
        expected_prompt = session.prompts[session.current_set_index]

        try:
            # Convert and process audio
            audio, _ = self.audio_processor.process_webm(audio_data)
            result = self.audio_processor.process_enrollment_audio(
                audio, expected_prompt
            )

            # ASR matched - accumulate embeddings
            for digit, embedding in result.digit_embeddings.items():
                session.accumulated_embeddings[digit].append(embedding)

            # Move to next set
            session.current_set_index += 1
            session.retry_count = 0

            remaining = len(session.prompts) - session.current_set_index

            if session.current_set_index >= len(session.prompts):
                session.state = EnrollmentState.COMPLETED_VOICE

            return ASRResultInfo(
                success=True,
                asr_text=result.digits,
                expected_prompt=expected_prompt,
                set_index=session.current_set_index - 1,
                remaining_sets=remaining,
                retry_count=0,
                max_retries=session.max_retries,
                message="OK! 次へ進みます"
                if remaining > 0
                else "音声登録完了! PINを設定してください",
            )

        except Exception as e:
            # ASR failed - increment retry count
            session.retry_count += 1

            if session.retry_count >= session.max_retries:
                session.state = EnrollmentState.FAILED
                session.error_message = (
                    f"リトライ上限({session.max_retries}回)に達しました"
                )
                return ASRResultInfo(
                    success=False,
                    asr_text="",
                    expected_prompt=expected_prompt,
                    set_index=session.current_set_index,
                    remaining_sets=len(session.prompts) - session.current_set_index,
                    retry_count=session.retry_count,
                    max_retries=session.max_retries,
                    message=session.error_message,
                )

            return ASRResultInfo(
                success=False,
                asr_text=str(e),
                expected_prompt=expected_prompt,
                set_index=session.current_set_index,
                remaining_sets=len(session.prompts) - session.current_set_index,
                retry_count=session.retry_count,
                max_retries=session.max_retries,
                message="聞き取れませんでした。もう一度、はっきりとお願いします",
            )

    def compute_centroids(
        self,
        session: EnrollmentSession,
    ) -> dict[str, np.ndarray]:
        """Compute centroid embeddings for each digit.

        Args:
            session: Enrollment session with accumulated embeddings.

        Returns:
            Dictionary of digit -> centroid embedding.

        Raises:
            ValueError: If not all digits have samples.
        """
        centroids: dict[str, np.ndarray] = {}

        for digit, embeddings in session.accumulated_embeddings.items():
            if not embeddings:
                raise ValueError(f"No embeddings for digit '{digit}'")

            # Compute mean of embeddings
            centroid = np.mean(embeddings, axis=0).astype(np.float32)
            centroids[digit] = centroid

        return centroids

    def register_pin(self, pin: str) -> str:
        """Hash a PIN for storage.

        Args:
            pin: 4-digit PIN string.

        Returns:
            SHA-256 hash of the PIN.

        Raises:
            ValueError: If PIN is not 4 digits.
        """
        if not pin.isdigit() or len(pin) != 4:
            raise ValueError("PIN must be exactly 4 digits")

        return hashlib.sha256(pin.encode()).hexdigest()

    def verify_pin(self, pin: str, pin_hash: str) -> bool:
        """Verify a PIN against its hash.

        Args:
            pin: PIN to verify.
            pin_hash: Stored hash to verify against.

        Returns:
            True if PIN matches hash.
        """
        return hashlib.sha256(pin.encode()).hexdigest() == pin_hash

    def complete_enrollment(
        self,
        session: EnrollmentSession,
        pin: str | None = None,
    ) -> EnrollmentResult:
        """Complete enrollment by saving to database.

        Args:
            session: Enrollment session with all voice data.
            pin: Optional 4-digit PIN for backup authentication.

        Returns:
            EnrollmentResult with registration status.

        Raises:
            ValueError: If voice enrollment is not complete.
        """
        if session.state != EnrollmentState.COMPLETED_VOICE:
            raise ValueError("Voice enrollment is not complete")

        # Compute centroids
        centroids = self.compute_centroids(session)

        # Hash PIN if provided
        pin_hash = self.register_pin(pin) if pin else None

        # Create speaker
        self.speaker_repository.create_speaker(
            speaker_id=session.speaker_id,
            speaker_name=session.speaker_name,
            pin_hash=pin_hash,
        )

        # Add voiceprints
        self.speaker_repository.add_voiceprints_bulk(
            speaker_id=session.speaker_id,
            embeddings=centroids,
        )

        session.state = EnrollmentState.COMPLETED

        return EnrollmentResult(
            speaker_id=session.speaker_id,
            registered_digits=list(centroids.keys()),
            has_pin=pin_hash is not None,
            status="registered",
        )
