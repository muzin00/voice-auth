"""Voice Activity Detection using Silero VAD."""

import numpy as np
import sherpa_onnx

from voiceauth.engine.exceptions import (
    ModelNotLoadedError,
    NoSpeechDetectedError,
    VADError,
)
from voiceauth.engine.settings import settings


class SileroVAD:
    """Voice Activity Detector using Silero VAD.

    Implements VADProtocol from voiceauth.domain.protocols.vad.
    """

    def __init__(self, model_path: str | None = None) -> None:
        """Initialize VAD.

        Args:
            model_path: Path to Silero VAD model. Defaults to settings path.
        """
        self._vad: sherpa_onnx.VoiceActivityDetector | None = None
        self._model_path = model_path or str(settings.vad_model_path)

    def _ensure_loaded(self) -> sherpa_onnx.VoiceActivityDetector:
        """Ensure VAD model is loaded."""
        if self._vad is None:
            self.load()
        if self._vad is None:
            raise ModelNotLoadedError("VAD model not loaded")
        return self._vad

    def load(self) -> None:
        """Load the VAD model."""
        try:
            config = sherpa_onnx.VadModelConfig(
                silero_vad=sherpa_onnx.SileroVadModelConfig(
                    model=self._model_path,
                    threshold=settings.vad_threshold,
                    min_silence_duration=settings.vad_min_silence_duration,
                    min_speech_duration=settings.vad_min_speech_duration,
                ),
                sample_rate=settings.target_sample_rate,
                num_threads=1,
            )
            self._vad = sherpa_onnx.VoiceActivityDetector(
                config,
                buffer_size_in_seconds=settings.vad_buffer_size_seconds,
            )
        except Exception as e:
            raise VADError(f"Failed to load VAD model: {e}") from e

    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            True if speech is detected, False otherwise.
        """
        vad = self._ensure_loaded()

        # Reset VAD state
        vad.reset()

        # Process audio in chunks (window_size samples = 512 for 16kHz)
        window_size = 512
        samples = audio.astype(np.float32)

        for i in range(0, len(samples), window_size):
            chunk = samples[i : i + window_size]
            if len(chunk) < window_size:
                # Pad last chunk with zeros
                chunk = np.pad(chunk, (0, window_size - len(chunk)))
            vad.accept_waveform(chunk)

        # Check if any speech segments were detected
        vad.flush()
        return not vad.empty()

    def get_speech_segments(self, audio: np.ndarray) -> list[tuple[float, float]]:
        """Get speech segments from audio.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            List of (start_sec, end_sec) tuples for speech segments.
        """
        vad = self._ensure_loaded()

        # Reset VAD state
        vad.reset()

        window_size = 512
        samples = audio.astype(np.float32)

        for i in range(0, len(samples), window_size):
            chunk = samples[i : i + window_size]
            if len(chunk) < window_size:
                chunk = np.pad(chunk, (0, window_size - len(chunk)))
            vad.accept_waveform(chunk)

        vad.flush()

        segments: list[tuple[float, float]] = []
        while not vad.empty():
            segment = vad.front
            start_sec = segment.start / settings.target_sample_rate
            end_sec = (
                segment.start + len(segment.samples)
            ) / settings.target_sample_rate
            segments.append((start_sec, end_sec))
            vad.pop()

        return segments

    def extract_speech(self, audio: np.ndarray) -> np.ndarray:
        """Extract speech segments from audio.

        Args:
            audio: Audio samples as float32 numpy array (16kHz mono).

        Returns:
            Concatenated speech segments as float32 numpy array.

        Raises:
            NoSpeechDetectedError: If no speech is detected.
        """
        vad = self._ensure_loaded()

        # Reset VAD state
        vad.reset()

        window_size = 512
        samples = audio.astype(np.float32)

        for i in range(0, len(samples), window_size):
            chunk = samples[i : i + window_size]
            if len(chunk) < window_size:
                chunk = np.pad(chunk, (0, window_size - len(chunk)))
            vad.accept_waveform(chunk)

        vad.flush()

        if vad.empty():
            raise NoSpeechDetectedError("No speech detected in audio")

        speech_samples: list[np.ndarray] = []
        while not vad.empty():
            segment = vad.front
            speech_samples.append(np.array(segment.samples, dtype=np.float32))
            vad.pop()

        return np.concatenate(speech_samples)
