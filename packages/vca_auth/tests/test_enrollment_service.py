"""Tests for enrollment service."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import numpy as np
import pytest
from vca_auth.repositories.speaker_repository import SpeakerAlreadyExistsError
from vca_auth.services.enrollment_service import (
    EnrollmentService,
    EnrollmentState,
)


@dataclass
class MockProcessingResult:
    """Mock processing result."""

    asr_text: str
    digits: str
    digit_embeddings: dict[str, np.ndarray]


class TestEnrollmentService:
    """Tests for EnrollmentService."""

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
        repo.speaker_exists.return_value = False
        return repo

    @pytest.fixture
    def enrollment_service(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> EnrollmentService:
        """Create enrollment service with mocks."""
        return EnrollmentService(
            audio_processor=mock_audio_processor,
            speaker_repository=mock_speaker_repository,
        )

    def test_start_enrollment_creates_session(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should create a new enrollment session."""
        session = enrollment_service.start_enrollment(
            speaker_id="test_user",
            speaker_name="Test User",
        )

        assert session.speaker_id == "test_user"
        assert session.speaker_name == "Test User"
        assert session.state == EnrollmentState.PROMPTS_SENT
        assert len(session.prompts) == 5
        assert session.current_set_index == 0
        assert session.retry_count == 0

    def test_start_enrollment_generates_valid_prompts(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should generate valid prompts for enrollment."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")

        # All prompts should be 4 digits
        for prompt in session.prompts:
            assert len(prompt) == 4
            assert prompt.isdigit()

    def test_start_enrollment_raises_if_speaker_exists(
        self,
        mock_audio_processor: MagicMock,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should raise error if speaker already exists."""
        mock_speaker_repository.speaker_exists.return_value = True

        service = EnrollmentService(
            audio_processor=mock_audio_processor,
            speaker_repository=mock_speaker_repository,
        )

        with pytest.raises(SpeakerAlreadyExistsError):
            service.start_enrollment(speaker_id="existing_user")

    def test_process_audio_success(
        self,
        enrollment_service: EnrollmentService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should process audio successfully when ASR matches."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")
        prompt = session.prompts[0]

        # Mock successful processing
        mock_result = MockProcessingResult(
            asr_text=prompt,
            digits=prompt,
            digit_embeddings={
                d: np.random.randn(512).astype(np.float32) for d in prompt
            },
        )
        mock_audio_processor.process_enrollment_audio.return_value = mock_result

        result = enrollment_service.process_audio(session, b"fake_audio")

        assert result.success is True
        assert result.set_index == 0
        assert result.remaining_sets == 4
        assert session.current_set_index == 1
        assert session.retry_count == 0

    def test_process_audio_failure_increments_retry(
        self,
        enrollment_service: EnrollmentService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should increment retry count on ASR failure."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")

        # Mock failed processing
        mock_audio_processor.process_enrollment_audio.side_effect = Exception(
            "ASR mismatch"
        )

        result = enrollment_service.process_audio(session, b"fake_audio")

        assert result.success is False
        assert session.retry_count == 1
        assert session.current_set_index == 0  # Should not advance

    def test_process_audio_fails_after_max_retries(
        self,
        enrollment_service: EnrollmentService,
        mock_audio_processor: MagicMock,
    ) -> None:
        """Should fail session after max retries."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")

        # Mock failed processing
        mock_audio_processor.process_enrollment_audio.side_effect = Exception(
            "ASR mismatch"
        )

        # Exhaust retries
        for _ in range(5):
            result = enrollment_service.process_audio(session, b"fake_audio")

        assert result.success is False
        assert session.state == EnrollmentState.FAILED

    def test_compute_centroids(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should compute centroids from accumulated embeddings."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")

        # Simulate accumulated embeddings (2 samples per digit)
        for digit in "0123456789":
            session.accumulated_embeddings[digit] = [
                np.ones(512, dtype=np.float32) * int(digit),
                np.ones(512, dtype=np.float32) * int(digit) * 2,
            ]

        centroids = enrollment_service.compute_centroids(session)

        assert len(centroids) == 10
        for digit in "0123456789":
            expected_mean = (int(digit) + int(digit) * 2) / 2
            np.testing.assert_allclose(
                centroids[digit],
                np.ones(512, dtype=np.float32) * expected_mean,
            )

    def test_compute_centroids_raises_if_missing_embeddings(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should raise error if not all digits have embeddings."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")
        # Don't add any embeddings

        with pytest.raises(ValueError, match="No embeddings for digit"):
            enrollment_service.compute_centroids(session)

    def test_register_pin_hashes_correctly(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should hash PIN with SHA-256."""
        pin_hash = enrollment_service.register_pin("1234")

        # SHA-256 produces 64 character hex string
        assert len(pin_hash) == 64
        assert pin_hash.isalnum()

        # Same PIN should produce same hash
        assert enrollment_service.register_pin("1234") == pin_hash

    def test_register_pin_invalid_format(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should reject invalid PIN formats."""
        with pytest.raises(ValueError, match="4 digits"):
            enrollment_service.register_pin("123")  # Too short

        with pytest.raises(ValueError, match="4 digits"):
            enrollment_service.register_pin("12345")  # Too long

        with pytest.raises(ValueError, match="4 digits"):
            enrollment_service.register_pin("abcd")  # Not digits

    def test_verify_pin(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should verify PIN against hash."""
        pin_hash = enrollment_service.register_pin("1234")

        assert enrollment_service.verify_pin("1234", pin_hash) is True
        assert enrollment_service.verify_pin("0000", pin_hash) is False

    def test_complete_enrollment_success(
        self,
        enrollment_service: EnrollmentService,
        mock_speaker_repository: MagicMock,
    ) -> None:
        """Should complete enrollment and save to database."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")

        # Simulate accumulated embeddings
        for digit in "0123456789":
            session.accumulated_embeddings[digit] = [
                np.ones(512, dtype=np.float32),
                np.ones(512, dtype=np.float32),
            ]
        session.state = EnrollmentState.COMPLETED_VOICE

        result = enrollment_service.complete_enrollment(session, pin="1234")

        assert result.speaker_id == "test_user"
        assert len(result.registered_digits) == 10
        assert result.has_pin is True
        assert result.status == "registered"
        assert session.state == EnrollmentState.COMPLETED

        # Verify repository was called
        mock_speaker_repository.create_speaker.assert_called_once()
        mock_speaker_repository.add_voiceprints_bulk.assert_called_once()

    def test_complete_enrollment_without_pin(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should complete enrollment without PIN."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")

        # Simulate accumulated embeddings
        for digit in "0123456789":
            session.accumulated_embeddings[digit] = [
                np.ones(512, dtype=np.float32),
            ]
        session.state = EnrollmentState.COMPLETED_VOICE

        result = enrollment_service.complete_enrollment(session, pin=None)

        assert result.has_pin is False

    def test_complete_enrollment_raises_if_voice_not_complete(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Should raise error if voice enrollment is not complete."""
        session = enrollment_service.start_enrollment(speaker_id="test_user")
        # State is still PROMPTS_SENT

        with pytest.raises(ValueError, match="not complete"):
            enrollment_service.complete_enrollment(session, pin="1234")
