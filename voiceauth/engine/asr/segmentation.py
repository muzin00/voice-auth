"""Audio segmentation based on timestamps."""

from dataclasses import dataclass

import numpy as np

from voiceauth.engine.exceptions import SegmentationError
from voiceauth.engine.settings import settings


@dataclass
class DigitSegment:
    """A segment of audio corresponding to a digit."""

    digit: str
    audio: np.ndarray
    start_time: float  # seconds
    end_time: float  # seconds


def cut_segment_with_padding(
    audio: np.ndarray,
    sample_rate: int,
    start_sec: float,
    end_sec: float,
    padding_sec: float | None = None,
    next_start_sec: float | None = None,
) -> np.ndarray:
    """Cut audio segment with padding.

    Args:
        audio: Audio samples as numpy array.
        sample_rate: Sample rate of audio.
        start_sec: Start time in seconds.
        end_sec: End time in seconds.
        padding_sec: Padding to add before and after. Defaults to settings value.
        next_start_sec: Start time of next segment (to avoid overlap).

    Returns:
        Cut audio segment as numpy array.
    """
    if padding_sec is None:
        padding_sec = settings.segment_padding_seconds

    # Convert to sample indices
    start_idx = int(start_sec * sample_rate)
    end_idx = int(end_sec * sample_rate)
    pad_samples = int(padding_sec * sample_rate)

    # Apply padding
    new_start = max(0, start_idx - pad_samples)

    # Ensure we don't overlap with next segment
    if next_start_sec is not None:
        max_end = int(next_start_sec * sample_rate)
        new_end = min(len(audio), end_idx + pad_samples, max_end)
    else:
        new_end = min(len(audio), end_idx + pad_samples)

    return audio[new_start:new_end].copy()


def segment_by_timestamps(
    audio: np.ndarray,
    timestamps: list[tuple[str, float, float]],
    sample_rate: int | None = None,
    padding_sec: float | None = None,
) -> list[DigitSegment]:
    """Segment audio by digit timestamps.

    Args:
        audio: Audio samples as numpy array.
        timestamps: List of (digit, start_sec, end_sec) tuples.
        sample_rate: Sample rate of audio. Defaults to settings value.
        padding_sec: Padding to add before and after each segment.

    Returns:
        List of DigitSegment objects.

    Raises:
        SegmentationError: If segmentation fails.
    """
    if sample_rate is None:
        sample_rate = settings.target_sample_rate

    if padding_sec is None:
        padding_sec = settings.segment_padding_seconds

    if not timestamps:
        raise SegmentationError("No timestamps provided for segmentation")

    segments: list[DigitSegment] = []

    for i, (digit, start_sec, end_sec) in enumerate(timestamps):
        # Get next start time if available
        next_start = timestamps[i + 1][1] if i + 1 < len(timestamps) else None

        try:
            segment_audio = cut_segment_with_padding(
                audio=audio,
                sample_rate=sample_rate,
                start_sec=start_sec,
                end_sec=end_sec,
                padding_sec=padding_sec,
                next_start_sec=next_start,
            )

            if len(segment_audio) == 0:
                raise SegmentationError(
                    f"Empty segment for digit '{digit}' at {start_sec:.3f}-{end_sec:.3f}s"
                )

            segments.append(
                DigitSegment(
                    digit=digit,
                    audio=segment_audio,
                    start_time=start_sec,
                    end_time=end_sec,
                )
            )

        except SegmentationError:
            raise
        except Exception as e:
            raise SegmentationError(f"Failed to segment digit '{digit}': {e}") from e

    return segments


def merge_segments(segments: list[DigitSegment]) -> np.ndarray:
    """Merge multiple segments into a single audio array.

    Args:
        segments: List of DigitSegment objects.

    Returns:
        Merged audio as numpy array.
    """
    if not segments:
        return np.array([], dtype=np.float32)

    return np.concatenate([s.audio for s in segments])


def get_segment_duration(
    segment: DigitSegment, sample_rate: int | None = None
) -> float:
    """Get duration of a segment in seconds.

    Args:
        segment: DigitSegment object.
        sample_rate: Sample rate of audio. Defaults to settings value.

    Returns:
        Duration in seconds.
    """
    if sample_rate is None:
        sample_rate = settings.target_sample_rate

    return len(segment.audio) / sample_rate
