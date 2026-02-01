"""Tests for audio processor facade module."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from vca_engine.audio_processor import (
    AudioProcessor,
    VerificationResult,
    get_processor,
)
from vca_engine.exceptions import (
    AudioTooLongError,
    AudioTooShortError,
)


@pytest.fixture
def processor() -> AudioProcessor:
    """Create processor instance."""
    return AudioProcessor()


class TestAudioProcessorValidation:
    """Tests for audio validation."""

    def test_short_audio_raises(
        self, processor: AudioProcessor, short_audio: np.ndarray
    ) -> None:
        """Test too short audio raises error."""
        with pytest.raises(AudioTooShortError):
            processor.validate_audio_duration(short_audio)

    def test_long_audio_raises(
        self, processor: AudioProcessor, long_audio: np.ndarray
    ) -> None:
        """Test too long audio raises error."""
        with pytest.raises(AudioTooLongError):
            processor.validate_audio_duration(long_audio)

    def test_valid_duration_passes(
        self, processor: AudioProcessor, sample_rate: int
    ) -> None:
        """Test valid duration passes."""
        audio = np.zeros(sample_rate * 3, dtype=np.float32)  # 3 seconds
        processor.validate_audio_duration(audio)  # Should not raise


class TestAudioProcessorSpeechDetection:
    """Tests for speech detection."""

    def test_detect_speech_silence(
        self, processor: AudioProcessor, silence_audio: np.ndarray
    ) -> None:
        """Test speech detection returns False for silence."""
        assert processor.detect_speech(silence_audio) is False

    def test_detect_speech_real_audio(
        self, processor: AudioProcessor, japanese_wav: Path
    ) -> None:
        """Test speech detection returns True for real speech."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, _ = sf.read(str(japanese_wav), dtype="float32")
        assert processor.detect_speech(audio) is True


class TestAudioProcessorRecognition:
    """Tests for speech recognition."""

    def test_recognize_real_audio(
        self, processor: AudioProcessor, japanese_wav: Path
    ) -> None:
        """Test recognition with real audio."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, _ = sf.read(str(japanese_wav), dtype="float32")
        result = processor.recognize(audio)

        assert result.text != ""


class TestAudioProcessorEmbedding:
    """Tests for speaker embedding extraction."""

    def test_extract_embedding_real_audio(
        self, processor: AudioProcessor, japanese_wav: Path
    ) -> None:
        """Test embedding extraction with real audio."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, _ = sf.read(str(japanese_wav), dtype="float32")
        embedding = processor.extract_embedding(audio)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (512,)  # CAM++ model outputs 512 dimensions


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = VerificationResult(asr_text="test", asr_matched=True)

        assert result.digit_scores == {}
        assert result.average_score == 0.0
        assert result.authenticated is False

    def test_with_values(self) -> None:
        """Test with explicit values."""
        result = VerificationResult(
            asr_text="4326",
            asr_matched=True,
            digit_scores={"4": 0.8, "3": 0.85, "2": 0.82, "6": 0.79},
            average_score=0.815,
            authenticated=True,
        )

        assert result.authenticated is True
        assert result.average_score == 0.815


class TestGetProcessor:
    """Tests for get_processor singleton."""

    def test_returns_same_instance(self) -> None:
        """Test get_processor returns same instance."""
        p1 = get_processor()
        p2 = get_processor()

        assert p1 is p2
