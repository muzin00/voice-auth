"""Tests for verify service."""

from dataclasses import dataclass
from unittest.mock import MagicMock, PropertyMock

import numpy as np
import pytest

from vca_auth.repositories.speaker_repository import SpeakerNotFoundError
from vca_auth.services.verify_service import (
    VerifyService,
    VerifyState,
)


@dataclass
class MockVerificationResult:
    """Mock verification result from audio processor."""

    asr_text: str
    asr_matched: bool
    digit_scores: dict[str, float]
    average_score: float
    authenticated: bool


class MockSpeaker:
    """Mock Speaker model."""

    def __init__(self, pin_hash: str | None = None) -> None:
        self.pin_hash = pin_hash


class TestVerifyService:
    """Tests for VerifyService."""

    @pytest.fixture
    def mock_audio_processor(self) -> MagicMock:
        """Create mock audio processor."""
        processor = MagicMock()
        processor.process_webm.return_value = (np.zeros(16000), 16000)
        return processor

    @pytest.fixture
    def mock_speaker_repository(self) -> MagicMock:
        """Create mock speaker repository."""
        repo = MagicMock()
        repo.speaker_exists.return_value = True
        repo.get_speaker_by_id.return_value = MockSpeaker(
            pin_hash="5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"  # hash of "12345" -> wrong, use "1234"
        )
        repo.get_voiceprints.return_value = {
            str(d): np.random.randn(512).astype(np.float32) for d in range(10)
        }
        return repo

    @pytest.fixture
    def verify_service(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> VerifyService:
        """Create verify service with mocks."""
        return VerifyService(
            audio_processor=mock_audio_processor,
            speaker_repository=mock_speaker_repository,
        )

    def test_start_verification_creates_session(
        self,
        verify_service: VerifyService,
    ) -> None:
        """Should create a new verification session."""
        session = verify_service.start_verification(speaker_id="test_user")

        assert session.speaker_id == "test_user"
        assert session.state == VerifyState.PROMPT_SENT
        assert len(session.prompt) == 4
        assert session.prompt.isdigit()

    def test_start_verification_custom_prompt_length(
        self,
        verify_service: VerifyService,
    ) -> None:
        """Should support custom prompt lengths."""
        session = verify_service.start_verification(
            speaker_id="test_user", prompt_length=6
        )

        assert len(session.prompt) == 6

    def test_start_verification_raises_if_speaker_not_found(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should raise error if speaker doesn't exist."""
        mock_speaker_repository.speaker_exists.return_value = False

        service = VerifyService(
            audio_processor=mock_audio_processor,
            speaker_repository=mock_speaker_repository,
        )

        with pytest.raises(SpeakerNotFoundError):
            service.start_verification(speaker_id="nonexistent_user")

    def test_start_verification_sets_pin_fallback_availability(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should set can_fallback_to_pin based on speaker's PIN."""
        # With PIN
        mock_speaker_repository.get_speaker_by_id.return_value = MockSpeaker(
            pin_hash="somehash"
        )
        service = VerifyService(mock_audio_processor, mock_speaker_repository)
        session = service.start_verification(speaker_id="test_user")
        assert session.can_fallback_to_pin is True

        # Without PIN
        mock_speaker_repository.get_speaker_by_id.return_value = MockSpeaker(
            pin_hash=None
        )
        session = service.start_verification(speaker_id="test_user")
        assert session.can_fallback_to_pin is False

    def test_verify_voice_success(
        self,
        verify_service: VerifyService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should authenticate when voice matches."""
        session = verify_service.start_verification(speaker_id="test_user")

        # Mock successful verification
        mock_result = MockVerificationResult(
            asr_text=session.prompt,
            asr_matched=True,
            digit_scores={d: 0.85 for d in session.prompt},
            average_score=0.85,
            authenticated=True,
        )
        mock_audio_processor.verify_audio.return_value = mock_result

        result = verify_service.verify_voice(session, b"fake_audio")

        assert result.authenticated is True
        assert result.asr_matched is True
        assert result.voice_similarity == 0.85
        assert result.auth_method == "voice"
        assert session.state == VerifyState.AUTHENTICATED

    def test_verify_voice_asr_mismatch(
        self,
        verify_service: VerifyService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should fail when ASR doesn't match prompt."""
        session = verify_service.start_verification(speaker_id="test_user")

        # Mock ASR mismatch
        mock_result = MockVerificationResult(
            asr_text="9999",
            asr_matched=False,
            digit_scores={},
            average_score=0.0,
            authenticated=False,
        )
        mock_audio_processor.verify_audio.return_value = mock_result

        result = verify_service.verify_voice(session, b"fake_audio")

        assert result.authenticated is False
        assert result.asr_matched is False
        assert result.voice_similarity is None
        assert session.state == VerifyState.VOICE_FAILED

    def test_verify_voice_low_similarity(
        self,
        verify_service: VerifyService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should fail when voice similarity is too low."""
        session = verify_service.start_verification(speaker_id="test_user")

        # Mock low similarity
        mock_result = MockVerificationResult(
            asr_text=session.prompt,
            asr_matched=True,
            digit_scores={d: 0.50 for d in session.prompt},
            average_score=0.50,
            authenticated=False,
        )
        mock_audio_processor.verify_audio.return_value = mock_result

        result = verify_service.verify_voice(session, b"fake_audio")

        assert result.authenticated is False
        assert result.asr_matched is True
        assert result.voice_similarity == 0.50
        assert result.can_fallback_to_pin is True
        assert session.state == VerifyState.VOICE_FAILED

    def test_verify_voice_handles_exception(
        self,
        verify_service: VerifyService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should handle exceptions gracefully."""
        session = verify_service.start_verification(speaker_id="test_user")

        mock_audio_processor.verify_audio.side_effect = Exception("Processing error")

        result = verify_service.verify_voice(session, b"fake_audio")

        assert result.authenticated is False
        assert "エラー" in result.message
        assert session.state == VerifyState.FAILED

    def test_verify_pin_success(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should authenticate with correct PIN."""
        # Set up speaker with known PIN hash (SHA-256 of "1234")
        import hashlib

        pin_hash = hashlib.sha256("1234".encode()).hexdigest()
        mock_speaker_repository.get_speaker_by_id.return_value = MockSpeaker(
            pin_hash=pin_hash
        )

        service = VerifyService(mock_audio_processor, mock_speaker_repository)
        session = service.start_verification(speaker_id="test_user")

        # Simulate voice verification failed
        session.state = VerifyState.VOICE_FAILED

        result = service.verify_pin(session, "1234")

        assert result.authenticated is True
        assert result.auth_method == "pin"
        assert session.state == VerifyState.AUTHENTICATED

    def test_verify_pin_wrong_pin(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should fail with incorrect PIN."""
        import hashlib

        pin_hash = hashlib.sha256("1234".encode()).hexdigest()
        mock_speaker_repository.get_speaker_by_id.return_value = MockSpeaker(
            pin_hash=pin_hash
        )

        service = VerifyService(mock_audio_processor, mock_speaker_repository)
        session = service.start_verification(speaker_id="test_user")
        session.state = VerifyState.VOICE_FAILED

        result = service.verify_pin(session, "0000")

        assert result.authenticated is False
        assert result.can_fallback_to_pin is True  # Can retry
        assert "一致しません" in result.message

    def test_verify_pin_not_available(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should fail when PIN fallback is not available."""
        mock_speaker_repository.get_speaker_by_id.return_value = MockSpeaker(
            pin_hash=None
        )

        service = VerifyService(mock_audio_processor, mock_speaker_repository)
        session = service.start_verification(speaker_id="test_user")
        session.state = VerifyState.VOICE_FAILED

        result = service.verify_pin(session, "1234")

        assert result.authenticated is False
        assert result.can_fallback_to_pin is False
