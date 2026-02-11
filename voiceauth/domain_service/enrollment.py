"""Enrollment service for speaker registration.

Manages the enrollment flow:
1. Generate prompts
2. Process audio for each prompt (with retries)
3. Accumulate utterance-level embeddings
4. Calculate centroid
5. Register PIN
6. Save to database
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from voiceauth.domain.prompt_generator import PromptGenerator
from voiceauth.domain.protocols import (
    EnrollmentAudioProcessorProtocol,
    EnrollmentSpeakerStoreProtocol,
)
from voiceauth.domain_service.settings import settings


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
    max_retries: int = settings.enrollment_max_retries
    # Accumulated utterance-level embeddings (one per successful prompt)
    accumulated_embeddings: list[np.ndarray] = field(default_factory=list)
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
    has_pin: bool
    status: str


class SpeakerAlreadyExistsError(Exception):
    """Raised when attempting to create a speaker that already exists."""

    pass


class EnrollmentService:
    """Service for managing speaker enrollment."""

    def __init__(
        self,
        audio_processor: EnrollmentAudioProcessorProtocol,
        speaker_store: EnrollmentSpeakerStoreProtocol,
    ) -> None:
        """Initialize enrollment service.

        Args:
            audio_processor: Audio processor for voice processing.
            speaker_store: Store for speaker database operations.
        """
        self.audio_processor = audio_processor
        self.speaker_store = speaker_store
        self._prompt_generator = PromptGenerator()

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
        if self.speaker_store.speaker_exists(speaker_id):
            raise SpeakerAlreadyExistsError(f"Speaker '{speaker_id}' already exists")

        session = EnrollmentSession(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            prompts=self._prompt_generator.generate(),
            accumulated_embeddings=[],
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

            # ASR matched - accumulate utterance embedding
            session.accumulated_embeddings.append(result.utterance_embedding)

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

    def compute_centroid(
        self,
        session: EnrollmentSession,
    ) -> np.ndarray:
        """Compute centroid embedding from accumulated utterance embeddings.

        Args:
            session: Enrollment session with accumulated embeddings.

        Returns:
            L2-normalized centroid embedding.

        Raises:
            ValueError: If no embeddings have been accumulated.
        """
        if not session.accumulated_embeddings:
            raise ValueError("No embeddings accumulated")

        centroid = np.mean(session.accumulated_embeddings, axis=0).astype(np.float32)
        # L2 normalize
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        return centroid

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

        # Compute centroid
        centroid = self.compute_centroid(session)

        # Hash PIN if provided
        pin_hash = self.register_pin(pin) if pin else None

        # Create speaker
        self.speaker_store.create_speaker(
            speaker_id=session.speaker_id,
            speaker_name=session.speaker_name,
            pin_hash=pin_hash,
        )

        # Add voiceprint
        self.speaker_store.add_voiceprint(
            speaker_id=session.speaker_id,
            embedding=centroid,
        )

        session.state = EnrollmentState.COMPLETED

        return EnrollmentResult(
            speaker_id=session.speaker_id,
            has_pin=pin_hash is not None,
            status="registered",
        )
