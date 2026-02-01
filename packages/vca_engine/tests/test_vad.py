"""Tests for VAD module."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from vca_engine.exceptions import NoSpeechDetectedError
from vca_engine.vad import VoiceActivityDetector


@pytest.fixture
def vad() -> VoiceActivityDetector:
    """Create VAD instance."""
    return VoiceActivityDetector()


class TestVoiceActivityDetector:
    """Tests for VoiceActivityDetector class."""

    def test_is_speech_with_silence(
        self, vad: VoiceActivityDetector, silence_audio: np.ndarray
    ) -> None:
        """Test VAD returns False for silence."""
        assert vad.is_speech(silence_audio) is False

    def test_is_speech_with_noise(
        self, vad: VoiceActivityDetector, noise_audio: np.ndarray
    ) -> None:
        """Test VAD returns False for low-level noise."""
        assert vad.is_speech(noise_audio) is False

    def test_is_speech_with_real_audio(
        self,
        vad: VoiceActivityDetector,
        japanese_wav: Path,
    ) -> None:
        """Test VAD returns True for real speech."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, sr = sf.read(str(japanese_wav), dtype="float32")
        assert vad.is_speech(audio) is True

    def test_get_speech_segments_with_silence(
        self, vad: VoiceActivityDetector, silence_audio: np.ndarray
    ) -> None:
        """Test get_speech_segments returns empty for silence."""
        segments = vad.get_speech_segments(silence_audio)
        assert segments == []

    def test_get_speech_segments_with_real_audio(
        self,
        vad: VoiceActivityDetector,
        japanese_wav: Path,
    ) -> None:
        """Test get_speech_segments returns segments for real speech."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, sr = sf.read(str(japanese_wav), dtype="float32")
        segments = vad.get_speech_segments(audio)

        assert len(segments) > 0
        for start, end in segments:
            assert start < end
            assert start >= 0
            assert end > 0

    def test_extract_speech_with_silence_raises(
        self, vad: VoiceActivityDetector, silence_audio: np.ndarray
    ) -> None:
        """Test extract_speech raises for silence."""
        with pytest.raises(NoSpeechDetectedError):
            vad.extract_speech(silence_audio)

    def test_extract_speech_with_real_audio(
        self,
        vad: VoiceActivityDetector,
        japanese_wav: Path,
    ) -> None:
        """Test extract_speech returns audio for real speech."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, sr = sf.read(str(japanese_wav), dtype="float32")
        speech = vad.extract_speech(audio)

        assert isinstance(speech, np.ndarray)
        assert len(speech) > 0
        assert speech.dtype == np.float32
