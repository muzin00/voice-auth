"""Tests for ASR module."""

from pathlib import Path

import pytest
import soundfile as sf
from vca_engine.asr import (
    DIGIT_NORMALIZATION,
    ASRResult,
    SpeechRecognizer,
    TokenInfo,
    extract_digit_timestamps,
)


@pytest.fixture
def asr() -> SpeechRecognizer:
    """Create ASR instance."""
    return SpeechRecognizer()


class TestDigitNormalization:
    """Tests for digit normalization."""

    def test_japanese_digits(self) -> None:
        """Test Japanese digit readings are in normalization dict."""
        assert "ゼロ" in DIGIT_NORMALIZATION
        assert "いち" in DIGIT_NORMALIZATION
        assert "に" in DIGIT_NORMALIZATION
        assert "さん" in DIGIT_NORMALIZATION
        assert "よん" in DIGIT_NORMALIZATION
        assert "ご" in DIGIT_NORMALIZATION
        assert "ろく" in DIGIT_NORMALIZATION
        assert "なな" in DIGIT_NORMALIZATION
        assert "はち" in DIGIT_NORMALIZATION
        assert "きゅう" in DIGIT_NORMALIZATION

    def test_alternative_readings(self) -> None:
        """Test alternative readings are handled."""
        assert DIGIT_NORMALIZATION["ゼロ"] == "0"
        assert DIGIT_NORMALIZATION["れい"] == "0"
        assert DIGIT_NORMALIZATION["まる"] == "0"
        assert DIGIT_NORMALIZATION["しち"] == "7"


class TestSpeechRecognizer:
    """Tests for SpeechRecognizer class."""

    def test_recognize_real_audio(
        self,
        asr: SpeechRecognizer,
        japanese_wav: Path,
    ) -> None:
        """Test ASR with real Japanese audio."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, sr = sf.read(str(japanese_wav), dtype="float32")
        result = asr.recognize(audio)

        assert isinstance(result, ASRResult)
        assert result.text != ""
        # Japanese audio should produce some text

    def test_recognize_returns_tokens(
        self,
        asr: SpeechRecognizer,
        japanese_wav: Path,
    ) -> None:
        """Test ASR returns token information."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, sr = sf.read(str(japanese_wav), dtype="float32")
        result = asr.recognize(audio)

        # Should have some tokens
        assert isinstance(result.tokens, list)
        for token in result.tokens:
            assert isinstance(token, TokenInfo)
            assert token.start_time >= 0
            assert token.end_time >= token.start_time


class TestExtractDigitTimestamps:
    """Tests for extract_digit_timestamps function."""

    def test_empty_digits(self) -> None:
        """Test empty normalized text returns empty list."""
        result = ASRResult(text="hello", normalized_text="", tokens=[])
        timestamps = extract_digit_timestamps(result)
        assert timestamps == []

    def test_no_tokens_estimates(self) -> None:
        """Test timestamps are estimated when no tokens available."""
        result = ASRResult(text="4326", normalized_text="4326", tokens=[])
        timestamps = extract_digit_timestamps(result)

        assert len(timestamps) == 4
        for digit, start, end in timestamps:
            assert digit in "4326"
            assert start < end

    def test_with_tokens(self) -> None:
        """Test timestamps from tokens."""
        tokens = [
            TokenInfo(token="4", start_time=0.1, end_time=0.3),
            TokenInfo(token="3", start_time=0.3, end_time=0.5),
            TokenInfo(token="2", start_time=0.5, end_time=0.7),
            TokenInfo(token="6", start_time=0.7, end_time=0.9),
        ]
        result = ASRResult(text="4326", normalized_text="4326", tokens=tokens)
        timestamps = extract_digit_timestamps(result)

        assert len(timestamps) == 4
        assert timestamps[0] == ("4", 0.1, 0.3)
        assert timestamps[1] == ("3", 0.3, 0.5)
        assert timestamps[2] == ("2", 0.5, 0.7)
        assert timestamps[3] == ("6", 0.7, 0.9)
