"""Automatic Speech Recognition using SenseVoice."""

from dataclasses import dataclass

import numpy as np
import sherpa_onnx

from .exceptions import ASRError, ModelNotLoadedError
from .settings import settings

# Mapping for normalizing Japanese digit readings to numeric characters
DIGIT_NORMALIZATION = {
    # Japanese readings for digits
    "ゼロ": "0",
    "れい": "0",
    "レイ": "0",
    "零": "0",
    "まる": "0",
    "マル": "0",
    "いち": "1",
    "イチ": "1",
    "一": "1",
    "に": "2",
    "ニ": "2",
    "二": "2",
    "さん": "3",
    "サン": "3",
    "三": "3",
    "よん": "4",
    "ヨン": "4",
    "し": "4",
    "シ": "4",
    "四": "4",
    "ご": "5",
    "ゴ": "5",
    "五": "5",
    "ろく": "6",
    "ロク": "6",
    "六": "6",
    "なな": "7",
    "ナナ": "7",
    "しち": "7",
    "シチ": "7",
    "七": "7",
    "はち": "8",
    "ハチ": "8",
    "八": "8",
    "きゅう": "9",
    "キュウ": "9",
    "く": "9",
    "ク": "9",
    "九": "9",
    # English readings
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}


@dataclass
class TokenInfo:
    """Information about a recognized token."""

    token: str
    start_time: float  # seconds
    end_time: float  # seconds


@dataclass
class ASRResult:
    """Result of automatic speech recognition."""

    text: str  # Raw recognized text
    normalized_text: str  # Normalized text (digits only)
    tokens: list[TokenInfo]  # Token information with timestamps


class SpeechRecognizer:
    """Speech recognizer using SenseVoice."""

    def __init__(
        self,
        model_path: str | None = None,
        tokens_path: str | None = None,
    ) -> None:
        """Initialize ASR.

        Args:
            model_path: Path to SenseVoice model. Defaults to settings path.
            tokens_path: Path to tokens file. Defaults to settings path.
        """
        self._recognizer: sherpa_onnx.OfflineRecognizer | None = None
        self._model_path = model_path or str(settings.sensevoice_model_path)
        self._tokens_path = tokens_path or str(settings.sensevoice_tokens_path)

    def _ensure_loaded(self) -> sherpa_onnx.OfflineRecognizer:
        """Ensure ASR model is loaded."""
        if self._recognizer is None:
            self.load()
        if self._recognizer is None:
            raise ModelNotLoadedError("ASR model not loaded")
        return self._recognizer

    def load(self) -> None:
        """Load the ASR model."""
        try:
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=self._model_path,
                tokens=self._tokens_path,
                num_threads=settings.asr_num_threads,
                use_itn=settings.asr_use_itn,
                debug=False,
            )
        except Exception as e:
            raise ASRError(f"Failed to load ASR model: {e}") from e

    def recognize(self, audio: np.ndarray, sample_rate: int | None = None) -> ASRResult:
        """Recognize speech from audio.

        Args:
            audio: Audio samples as float32 numpy array.
            sample_rate: Sample rate of audio. Defaults to settings.target_sample_rate.

        Returns:
            ASRResult with recognized text and token timestamps.

        Raises:
            ASRError: If recognition fails.
        """
        recognizer = self._ensure_loaded()

        if sample_rate is None:
            sample_rate = settings.target_sample_rate

        try:
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, audio.astype(np.float32))
            recognizer.decode_stream(stream)

            result = stream.result
            raw_text = result.text.strip()

            # Extract tokens and timestamps
            tokens: list[TokenInfo] = []
            if hasattr(result, "tokens") and hasattr(result, "timestamps"):
                result_tokens = result.tokens
                result_timestamps = result.timestamps

                for i, token in enumerate(result_tokens):
                    start_time = (
                        result_timestamps[i] if i < len(result_timestamps) else 0.0
                    )
                    # End time is start of next token, or estimate from duration
                    if i + 1 < len(result_timestamps):
                        end_time = result_timestamps[i + 1]
                    else:
                        # Estimate end time (add 0.3s for last token)
                        end_time = start_time + 0.3

                    tokens.append(
                        TokenInfo(
                            token=token,
                            start_time=start_time,
                            end_time=end_time,
                        )
                    )

            # Normalize text to extract digits
            normalized = self._normalize_to_digits(raw_text)

            return ASRResult(
                text=raw_text,
                normalized_text=normalized,
                tokens=tokens,
            )

        except Exception as e:
            raise ASRError(f"Speech recognition failed: {e}") from e

    def _normalize_to_digits(self, text: str) -> str:
        """Normalize text to extract digit characters.

        Args:
            text: Raw recognized text.

        Returns:
            String containing only digit characters.
        """
        result = text

        # Replace known digit readings with numeric characters
        # Sort by length (longest first) to handle overlapping patterns
        for reading, digit in sorted(
            DIGIT_NORMALIZATION.items(), key=lambda x: len(x[0]), reverse=True
        ):
            result = result.replace(reading, digit)

        # Keep only digits
        return "".join(c for c in result if c.isdigit())

    def get_digit_tokens(self, asr_result: ASRResult) -> list[TokenInfo]:
        """Extract tokens that correspond to digits.

        Args:
            asr_result: ASR result with tokens.

        Returns:
            List of TokenInfo for digit tokens only.
        """
        digit_tokens: list[TokenInfo] = []

        for token in asr_result.tokens:
            # Check if token is a digit or digit reading
            normalized = self._normalize_to_digits(token.token)
            if normalized:
                # Create new token with normalized digit
                digit_tokens.append(
                    TokenInfo(
                        token=normalized,
                        start_time=token.start_time,
                        end_time=token.end_time,
                    )
                )

        return digit_tokens


def extract_digit_timestamps(
    asr_result: ASRResult,
) -> list[tuple[str, float, float]]:
    """Extract digit timestamps from ASR result.

    This function analyzes tokens to find digit boundaries.

    Args:
        asr_result: ASR result with tokens.

    Returns:
        List of (digit, start_time, end_time) tuples.
    """
    digits_in_text = list(asr_result.normalized_text)

    if not digits_in_text:
        return []

    if not asr_result.tokens:
        # If no tokens, estimate timestamps based on text length
        # Assume uniform distribution (0.3s per digit)
        return [(d, i * 0.3, (i + 1) * 0.3) for i, d in enumerate(digits_in_text)]

    # Try to match digits with tokens
    result: list[tuple[str, float, float]] = []
    digit_idx = 0

    for token in asr_result.tokens:
        token_normalized = ""
        for reading, digit in sorted(
            DIGIT_NORMALIZATION.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if reading in token.token:
                token_normalized += digit
                break
        else:
            # Check for direct digit
            for c in token.token:
                if c.isdigit():
                    token_normalized += c

        if token_normalized and digit_idx < len(digits_in_text):
            for d in token_normalized:
                if digit_idx < len(digits_in_text) and d == digits_in_text[digit_idx]:
                    result.append((d, token.start_time, token.end_time))
                    digit_idx += 1

    # If we couldn't match all digits, fill in with estimates
    if len(result) < len(digits_in_text):
        # Use whatever we have and estimate the rest
        if result:
            last_end = result[-1][2]
        else:
            last_end = 0.0

        for i in range(len(result), len(digits_in_text)):
            start = last_end + (i - len(result)) * 0.3
            end = start + 0.3
            result.append((digits_in_text[i], start, end))

    return result
