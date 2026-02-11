"""Verification service for speaker authentication.

Manages the verification flow:
1. Generate verification prompt
2. Process audio and compare with registered voiceprints
3. Calculate similarity scores
4. Authenticate or fallback to PIN
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

import numpy as np

from voiceauth.domain.models import Speaker
from voiceauth.domain.prompt_generator import PromptGenerator
from voiceauth.domain_service.settings import settings


class AudioProcessorProtocol(Protocol):
    """Protocol for audio processor dependency."""

    def process_webm(self, webm_data: bytes) -> tuple[np.ndarray, int]:
        """Convert webm audio to PCM array."""
        ...

    def verify_audio(
        self,
        audio: np.ndarray,
        expected_prompt: str,
        registered_embeddings: dict[str, np.ndarray],
    ) -> "VerificationResultProtocol":
        """Verify audio against registered embeddings."""
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
    def digit_scores(self) -> dict[str, float]:
        """Get similarity scores per digit."""
        ...

    @property
    def average_score(self) -> float:
        """Get average similarity score."""
        ...

    @property
    def authenticated(self) -> bool:
        """Check if authentication passed."""
        ...


class SpeakerStoreProtocol(Protocol):
    """Protocol for speaker store dependency."""

    def speaker_exists(self, speaker_id: str) -> bool:
        """Check if speaker exists."""
        ...

    def get_speaker_by_id(self, speaker_id: str) -> Speaker:
        """Get speaker by ID."""
        ...

    def get_voiceprints(self, speaker_id: str) -> dict[str, np.ndarray]:
        """Get all voiceprints for speaker."""
        ...


class VerifyState(Enum):
    """States for the verification flow."""

    INITIAL = "initial"
    PROMPT_SENT = "prompt_sent"
    VOICE_VERIFIED = "voice_verified"
    VOICE_FAILED = "voice_failed"
    AWAITING_PIN = "awaiting_pin"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"


@dataclass
class VerifySession:
    """Verification session state."""

    speaker_id: str
    state: VerifyState = VerifyState.INITIAL
    prompt: str = ""
    asr_result: str = ""
    asr_matched: bool = False
    voice_similarity: float | None = None
    digit_scores: dict[str, float] = field(default_factory=dict)
    can_fallback_to_pin: bool = False
    auth_method: str | None = None
    error_message: str | None = None


@dataclass
class VerifyResult:
    """Result of verification attempt."""

    authenticated: bool
    speaker_id: str
    asr_result: str
    asr_matched: bool
    voice_similarity: float | None
    digit_scores: dict[str, float] | None
    can_fallback_to_pin: bool
    auth_method: str | None
    message: str


class SpeakerNotFoundError(Exception):
    """Raised when a speaker is not found."""

    pass


class VerifyService:
    """Service for managing speaker verification."""

    def __init__(
        self,
        audio_processor: AudioProcessorProtocol,
        speaker_store: SpeakerStoreProtocol,
    ) -> None:
        """Initialize verification service.

        Args:
            audio_processor: Audio processor for voice processing.
            speaker_store: Store for speaker database operations.
        """
        self.audio_processor = audio_processor
        self.speaker_store = speaker_store
        self._prompt_generator = PromptGenerator()

    def start_verification(
        self,
        speaker_id: str,
        prompt_length: int | None = None,
    ) -> VerifySession:
        """Start a new verification session.

        Args:
            speaker_id: Speaker to verify.
            prompt_length: Length of verification prompt (4-6 digits).

        Returns:
            New VerifySession with generated prompt.

        Raises:
            SpeakerNotFoundError: If speaker_id doesn't exist.
        """
        if prompt_length is None:
            prompt_length = settings.verification_prompt_length

        if not self.speaker_store.speaker_exists(speaker_id):
            raise SpeakerNotFoundError(f"Speaker '{speaker_id}' not found")

        # Check if speaker has PIN for fallback
        speaker = self.speaker_store.get_speaker_by_id(speaker_id)
        has_pin = speaker.pin_hash is not None

        prompt = self._prompt_generator.generate_verification_prompt(
            length=prompt_length
        )

        session = VerifySession(
            speaker_id=speaker_id,
            state=VerifyState.PROMPT_SENT,
            prompt=prompt,
            can_fallback_to_pin=has_pin,
        )

        return session

    def verify_voice(
        self,
        session: VerifySession,
        audio_data: bytes,
    ) -> VerifyResult:
        """Verify speaker voice against registered voiceprints.

        Args:
            session: Current verification session.
            audio_data: WebM audio bytes.

        Returns:
            VerifyResult with verification outcome.
        """
        try:
            # Get registered voiceprints
            registered_embeddings = self.speaker_store.get_voiceprints(
                session.speaker_id
            )

            # Convert and process audio
            audio, _ = self.audio_processor.process_webm(audio_data)
            result = self.audio_processor.verify_audio(
                audio=audio,
                expected_prompt=session.prompt,
                registered_embeddings=registered_embeddings,
            )

            # Update session state
            session.asr_result = result.asr_text
            session.asr_matched = result.asr_matched

            if not result.asr_matched:
                # ASR didn't match prompt
                session.state = VerifyState.VOICE_FAILED
                return VerifyResult(
                    authenticated=False,
                    speaker_id=session.speaker_id,
                    asr_result=result.asr_text,
                    asr_matched=False,
                    voice_similarity=None,
                    digit_scores=None,
                    can_fallback_to_pin=session.can_fallback_to_pin,
                    auth_method=None,
                    message="発話内容がプロンプトと一致しません",
                )

            # ASR matched, check voice similarity
            session.voice_similarity = result.average_score
            session.digit_scores = result.digit_scores

            if result.authenticated:
                # Voice authentication successful
                session.state = VerifyState.AUTHENTICATED
                session.auth_method = "voice"
                return VerifyResult(
                    authenticated=True,
                    speaker_id=session.speaker_id,
                    asr_result=result.asr_text,
                    asr_matched=True,
                    voice_similarity=result.average_score,
                    digit_scores=result.digit_scores,
                    can_fallback_to_pin=False,
                    auth_method="voice",
                    message="認証成功",
                )
            else:
                # Voice similarity too low
                session.state = VerifyState.VOICE_FAILED
                return VerifyResult(
                    authenticated=False,
                    speaker_id=session.speaker_id,
                    asr_result=result.asr_text,
                    asr_matched=True,
                    voice_similarity=result.average_score,
                    digit_scores=result.digit_scores,
                    can_fallback_to_pin=session.can_fallback_to_pin,
                    auth_method=None,
                    message="声紋が一致しません",
                )

        except Exception as e:
            session.state = VerifyState.FAILED
            session.error_message = str(e)
            return VerifyResult(
                authenticated=False,
                speaker_id=session.speaker_id,
                asr_result="",
                asr_matched=False,
                voice_similarity=None,
                digit_scores=None,
                can_fallback_to_pin=session.can_fallback_to_pin,
                auth_method=None,
                message=f"認証処理中にエラーが発生しました: {e}",
            )

    def verify_pin(
        self,
        session: VerifySession,
        pin: str,
    ) -> VerifyResult:
        """Verify speaker using PIN fallback.

        Args:
            session: Current verification session.
            pin: 4-digit PIN to verify.

        Returns:
            VerifyResult with PIN verification outcome.
        """
        if not session.can_fallback_to_pin:
            session.state = VerifyState.FAILED
            return VerifyResult(
                authenticated=False,
                speaker_id=session.speaker_id,
                asr_result=session.asr_result,
                asr_matched=session.asr_matched,
                voice_similarity=session.voice_similarity,
                digit_scores=session.digit_scores,
                can_fallback_to_pin=False,
                auth_method=None,
                message="PIN認証は利用できません",
            )

        # Get speaker's PIN hash
        speaker = self.speaker_store.get_speaker_by_id(session.speaker_id)

        if speaker.pin_hash is None:
            session.state = VerifyState.FAILED
            return VerifyResult(
                authenticated=False,
                speaker_id=session.speaker_id,
                asr_result=session.asr_result,
                asr_matched=session.asr_matched,
                voice_similarity=session.voice_similarity,
                digit_scores=session.digit_scores,
                can_fallback_to_pin=False,
                auth_method=None,
                message="PINが登録されていません",
            )

        # Verify PIN
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()

        if pin_hash == speaker.pin_hash:
            session.state = VerifyState.AUTHENTICATED
            session.auth_method = "pin"
            return VerifyResult(
                authenticated=True,
                speaker_id=session.speaker_id,
                asr_result=session.asr_result,
                asr_matched=session.asr_matched,
                voice_similarity=session.voice_similarity,
                digit_scores=session.digit_scores,
                can_fallback_to_pin=False,
                auth_method="pin",
                message="PIN認証成功",
            )
        else:
            # PIN doesn't match - still allow retry
            return VerifyResult(
                authenticated=False,
                speaker_id=session.speaker_id,
                asr_result=session.asr_result,
                asr_matched=session.asr_matched,
                voice_similarity=session.voice_similarity,
                digit_scores=session.digit_scores,
                can_fallback_to_pin=True,  # Allow retry
                auth_method=None,
                message="PINが一致しません",
            )
