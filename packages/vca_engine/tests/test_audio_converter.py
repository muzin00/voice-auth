"""Tests for audio converter module."""

from pathlib import Path

import numpy as np
import pytest
from vca_engine.audio_converter import (
    ensure_mono,
    load_wav_file,
    resample_audio,
)
from vca_engine.exceptions import AudioConversionError


class TestLoadWavFile:
    """Tests for load_wav_file function."""

    def test_load_valid_wav(self, japanese_wav: Path) -> None:
        """Test loading a valid WAV file."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, sr = load_wav_file(str(japanese_wav))

        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert sr == 16000
        assert len(audio) > 0
        # Check normalized range
        assert audio.min() >= -1.0
        assert audio.max() <= 1.0

    def test_load_nonexistent_file(self) -> None:
        """Test loading a non-existent file raises error."""
        with pytest.raises(AudioConversionError):
            load_wav_file("/nonexistent/path/to/file.wav")


class TestResampleAudio:
    """Tests for resample_audio function."""

    def test_resample_same_rate(self, sine_wave_audio: np.ndarray) -> None:
        """Test resampling with same rate returns same audio."""
        result = resample_audio(sine_wave_audio, 16000, 16000)
        np.testing.assert_array_equal(result, sine_wave_audio)

    def test_resample_downsample(self, sample_rate: int) -> None:
        """Test downsampling audio."""
        audio = np.ones(sample_rate, dtype=np.float32)
        result = resample_audio(audio, sample_rate, sample_rate // 2)

        assert len(result) == sample_rate // 2
        assert result.dtype == np.float32

    def test_resample_upsample(self, sample_rate: int) -> None:
        """Test upsampling audio."""
        audio = np.ones(sample_rate, dtype=np.float32)
        result = resample_audio(audio, sample_rate, sample_rate * 2)

        assert len(result) == sample_rate * 2
        assert result.dtype == np.float32


class TestEnsureMono:
    """Tests for ensure_mono function."""

    def test_mono_unchanged(self, sine_wave_audio: np.ndarray) -> None:
        """Test mono audio is unchanged."""
        result = ensure_mono(sine_wave_audio)
        np.testing.assert_array_equal(result, sine_wave_audio)

    def test_stereo_to_mono(self) -> None:
        """Test stereo audio is converted to mono."""
        stereo = np.array([[1.0, 0.5], [0.5, 1.0]], dtype=np.float32)
        result = ensure_mono(stereo)

        assert result.ndim == 1
        assert result.dtype == np.float32

    def test_invalid_shape_raises(self) -> None:
        """Test invalid audio shape raises error."""
        audio_3d = np.zeros((2, 3, 4), dtype=np.float32)

        with pytest.raises(AudioConversionError):
            ensure_mono(audio_3d)
