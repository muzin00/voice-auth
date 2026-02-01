"""Pytest fixtures for VCA Engine tests."""

from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def sample_rate() -> int:
    """Standard sample rate."""
    return 16000


@pytest.fixture
def silence_audio(sample_rate: int) -> np.ndarray:
    """Generate 1 second of silence."""
    return np.zeros(sample_rate, dtype=np.float32)


@pytest.fixture
def noise_audio(sample_rate: int) -> np.ndarray:
    """Generate 1 second of white noise."""
    rng = np.random.default_rng(42)
    return (rng.random(sample_rate) * 2 - 1).astype(np.float32) * 0.1


@pytest.fixture
def sine_wave_audio(sample_rate: int) -> np.ndarray:
    """Generate 1 second of 440Hz sine wave."""
    t = np.linspace(0, 1, sample_rate, dtype=np.float32)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.5


@pytest.fixture
def models_dir() -> Path:
    """Path to models directory."""
    # tests/conftest.py -> vca_engine/tests -> vca_engine -> packages -> vca_server
    return Path(__file__).parent.parent.parent.parent / "models"


@pytest.fixture
def test_wav_dir(models_dir: Path) -> Path:
    """Path to test wav files."""
    return (
        models_dir / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17" / "test_wavs"
    )


@pytest.fixture
def japanese_wav(test_wav_dir: Path) -> Path:
    """Path to Japanese test wav file."""
    return test_wav_dir / "ja.wav"


@pytest.fixture
def short_audio(sample_rate: int) -> np.ndarray:
    """Generate 0.5 second audio (too short)."""
    return np.zeros(sample_rate // 2, dtype=np.float32)


@pytest.fixture
def long_audio(sample_rate: int) -> np.ndarray:
    """Generate 15 second audio (too long)."""
    return np.zeros(sample_rate * 15, dtype=np.float32)
