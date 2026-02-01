"""Audio format converter using PyAV."""

import io

import av
import numpy as np

from .exceptions import AudioConversionError
from .settings import settings


def webm_to_pcm(webm_data: bytes) -> tuple[np.ndarray, int]:
    """Convert webm audio bytes to PCM numpy array.

    Args:
        webm_data: Raw webm audio bytes.

    Returns:
        Tuple of (audio samples as float32 numpy array, sample rate).

    Raises:
        AudioConversionError: If conversion fails.
    """
    try:
        container = av.open(io.BytesIO(webm_data))
        audio_stream = next((s for s in container.streams if s.type == "audio"), None)
        if audio_stream is None:
            raise AudioConversionError("No audio stream found in webm data")

        # Create resampler to target sample rate
        resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=settings.target_sample_rate,
        )

        samples_list: list[np.ndarray] = []

        for frame in container.decode(audio=0):
            resampled_frames = resampler.resample(frame)
            for resampled in resampled_frames:
                # Convert to numpy array
                arr = resampled.to_ndarray()
                samples_list.append(arr.flatten())

        container.close()

        if not samples_list:
            raise AudioConversionError("No audio samples decoded from webm data")

        # Concatenate all samples
        samples = np.concatenate(samples_list)

        # Convert from int16 to float32 normalized to [-1, 1]
        samples = samples.astype(np.float32) / 32768.0

        return samples, settings.target_sample_rate

    except AudioConversionError:
        raise
    except Exception as e:
        raise AudioConversionError(f"Failed to convert webm to PCM: {e}") from e


def load_wav_file(file_path: str) -> tuple[np.ndarray, int]:
    """Load a WAV file and return PCM samples.

    Args:
        file_path: Path to the WAV file.

    Returns:
        Tuple of (audio samples as float32 numpy array, sample rate).

    Raises:
        AudioConversionError: If loading fails.
    """
    try:
        container = av.open(file_path)
        audio_stream = next((s for s in container.streams if s.type == "audio"), None)
        if audio_stream is None:
            raise AudioConversionError(f"No audio stream found in {file_path}")

        # Create resampler to target sample rate
        resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=settings.target_sample_rate,
        )

        samples_list: list[np.ndarray] = []

        for frame in container.decode(audio=0):
            resampled_frames = resampler.resample(frame)
            for resampled in resampled_frames:
                arr = resampled.to_ndarray()
                samples_list.append(arr.flatten())

        container.close()

        if not samples_list:
            raise AudioConversionError(f"No audio samples decoded from {file_path}")

        samples = np.concatenate(samples_list)
        samples = samples.astype(np.float32) / 32768.0

        return samples, settings.target_sample_rate

    except AudioConversionError:
        raise
    except Exception as e:
        raise AudioConversionError(f"Failed to load WAV file: {e}") from e


def resample_audio(
    audio: np.ndarray,
    original_sr: int,
    target_sr: int | None = None,
) -> np.ndarray:
    """Resample audio to target sample rate.

    Args:
        audio: Input audio samples as float32 numpy array.
        original_sr: Original sample rate.
        target_sr: Target sample rate. Defaults to settings.target_sample_rate.

    Returns:
        Resampled audio as float32 numpy array.
    """
    if target_sr is None:
        target_sr = settings.target_sample_rate

    if original_sr == target_sr:
        return audio

    # Simple linear interpolation resampling
    ratio = target_sr / original_sr
    new_length = int(len(audio) * ratio)

    indices = np.linspace(0, len(audio) - 1, new_length)
    resampled = np.interp(indices, np.arange(len(audio)), audio)

    return resampled.astype(np.float32)


def ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Ensure audio is mono (single channel).

    Args:
        audio: Input audio, possibly stereo.

    Returns:
        Mono audio as float32 numpy array.
    """
    if audio.ndim == 1:
        return audio

    # Average channels for stereo
    if audio.ndim == 2:
        return np.mean(audio, axis=0 if audio.shape[0] <= 2 else 1).astype(np.float32)

    raise AudioConversionError(f"Unexpected audio shape: {audio.shape}")
