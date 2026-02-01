"""Tests for segmentation module."""

import numpy as np
import pytest
from vca_engine.exceptions import SegmentationError
from vca_engine.segmentation import (
    DigitSegment,
    cut_segment_with_padding,
    get_segment_duration,
    merge_segments,
    segment_by_timestamps,
)


class TestCutSegmentWithPadding:
    """Tests for cut_segment_with_padding function."""

    def test_basic_cut(self) -> None:
        """Test basic segment cutting."""
        audio = np.arange(16000, dtype=np.float32)  # 1 second at 16kHz
        segment = cut_segment_with_padding(audio, 16000, 0.2, 0.4, padding_sec=0.0)

        # 0.2s to 0.4s = 3200 to 6400 samples
        assert len(segment) == 3200

    def test_with_padding(self) -> None:
        """Test segment cutting with padding."""
        audio = np.arange(16000, dtype=np.float32)
        segment = cut_segment_with_padding(audio, 16000, 0.2, 0.4, padding_sec=0.05)

        # With 50ms padding: (0.2-0.05) to (0.4+0.05) = 0.15 to 0.45
        # 2400 to 7200 = 4800 samples
        assert len(segment) == 4800

    def test_padding_at_start(self) -> None:
        """Test padding doesn't go before audio start."""
        audio = np.arange(16000, dtype=np.float32)
        segment = cut_segment_with_padding(audio, 16000, 0.0, 0.2, padding_sec=0.1)

        # Should start at 0, not -0.1
        assert len(segment) == 4800  # 0 to 0.3 seconds

    def test_padding_at_end(self) -> None:
        """Test padding doesn't go past audio end."""
        audio = np.arange(16000, dtype=np.float32)
        segment = cut_segment_with_padding(audio, 16000, 0.9, 1.0, padding_sec=0.2)

        # Should end at 1.0, not 1.2
        # Start at 0.7 (0.9-0.2), end at 1.0
        assert len(segment) == 4800  # 0.7 to 1.0 seconds

    def test_next_segment_limit(self) -> None:
        """Test padding respects next segment start."""
        audio = np.arange(16000, dtype=np.float32)
        segment = cut_segment_with_padding(
            audio, 16000, 0.2, 0.3, padding_sec=0.1, next_start_sec=0.35
        )

        # End should be limited to 0.35, not 0.4
        # Start at 0.1, end at 0.35
        assert len(segment) == 4000  # 0.1 to 0.35 seconds


class TestSegmentByTimestamps:
    """Tests for segment_by_timestamps function."""

    def test_basic_segmentation(self) -> None:
        """Test basic segmentation."""
        audio = np.arange(16000, dtype=np.float32)
        timestamps = [
            ("1", 0.1, 0.2),
            ("2", 0.3, 0.4),
            ("3", 0.5, 0.6),
        ]

        segments = segment_by_timestamps(audio, timestamps, padding_sec=0.0)

        assert len(segments) == 3
        for i, segment in enumerate(segments):
            assert segment.digit == str(i + 1)
            assert isinstance(segment.audio, np.ndarray)

    def test_empty_timestamps_raises(self) -> None:
        """Test empty timestamps raises error."""
        audio = np.arange(16000, dtype=np.float32)

        with pytest.raises(SegmentationError):
            segment_by_timestamps(audio, [])


class TestMergeSegments:
    """Tests for merge_segments function."""

    def test_merge_empty(self) -> None:
        """Test merging empty list."""
        result = merge_segments([])
        assert len(result) == 0

    def test_merge_segments(self) -> None:
        """Test merging multiple segments."""
        seg1 = DigitSegment("1", np.array([1.0, 2.0], dtype=np.float32), 0.0, 0.1)
        seg2 = DigitSegment("2", np.array([3.0, 4.0], dtype=np.float32), 0.1, 0.2)

        result = merge_segments([seg1, seg2])

        assert len(result) == 4
        np.testing.assert_array_equal(result, [1.0, 2.0, 3.0, 4.0])


class TestGetSegmentDuration:
    """Tests for get_segment_duration function."""

    def test_duration(self) -> None:
        """Test duration calculation."""
        audio = np.zeros(8000, dtype=np.float32)
        segment = DigitSegment("1", audio, 0.0, 0.5)

        duration = get_segment_duration(segment, sample_rate=16000)

        assert duration == pytest.approx(0.5)
