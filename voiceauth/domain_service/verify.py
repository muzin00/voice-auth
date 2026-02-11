"""Verification service for speaker authentication.

Manages the verification flow:
1. Generate verification prompt
2. Process audio and compare with registered voiceprint
3. Calculate similarity score
4. Authenticate or fallback to PIN
"""

import hashlib
from dataclasses import dataclass
from enum import Enum

from voiceauth.domain.prompt_generator import generate_verification_prompt
from voiceauth.domain.protocols import (
    VerifyAudioProcessorProtocol,
    VerifySpeakerStoreProtocol,
)
from voiceauth.domain_service.settings import settings


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
        audio_processor: VerifyAudioProcessorProtocol,
        speaker_store: VerifySpeakerStoreProtocol,
    ) -> None:
        """Initialize verification service.

        Args:
            audio_processor: Audio processor for voice processing.
            speaker_store: Store for speaker database operations.
        """
        self.audio_processor = audio_processor
        self.speaker_store = speaker_store

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

        prompt = generate_verification_prompt(length=prompt_length)

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
        """Verify speaker voice against registered voiceprint.

        Args:
            session: Current verification session.
            audio_data: WebM audio bytes.

        Returns:
            VerifyResult with verification outcome.
        """
        try:
            # Get registered voiceprint
            registered_embedding = self.speaker_store.get_voiceprint(session.speaker_id)

            # Convert and process audio
            audio, _ = self.audio_processor.process_webm(audio_data)
            result = self.audio_processor.verify_audio(
                audio=audio,
                expected_prompt=session.prompt,
                registered_embedding=registered_embedding,
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
                    can_fallback_to_pin=session.can_fallback_to_pin,
                    auth_method=None,
                    message="発話内容がプロンプトと一致しません",
                )

            # ASR matched, check voice similarity
            session.voice_similarity = result.similarity_score

            if result.authenticated:
                # Voice authentication successful
                session.state = VerifyState.AUTHENTICATED
                session.auth_method = "voice"
                return VerifyResult(
                    authenticated=True,
                    speaker_id=session.speaker_id,
                    asr_result=result.asr_text,
                    asr_matched=True,
                    voice_similarity=result.similarity_score,
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
                    voice_similarity=result.similarity_score,
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
                can_fallback_to_pin=True,  # Allow retry
                auth_method=None,
                message="PINが一致しません",
            )
