"""Tests for voiceprint module."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from vca_engine.voiceprint import (
    VoiceprintExtractor,
    compute_centroid,
    cosine_similarity,
    is_same_voiceprint,
)


@pytest.fixture
def extractor() -> VoiceprintExtractor:
    """Create voiceprint extractor instance."""
    return VoiceprintExtractor()


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self) -> None:
        """Test identical vectors have similarity 1.0."""
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_opposite_vectors(self) -> None:
        """Test opposite vectors have similarity -1.0."""
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(v1, v2) == pytest.approx(-1.0)

    def test_orthogonal_vectors(self) -> None:
        """Test orthogonal vectors have similarity 0.0."""
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(v1, v2) == pytest.approx(0.0)

    def test_zero_vector(self) -> None:
        """Test zero vector returns 0.0."""
        v1 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        v2 = np.zeros(3, dtype=np.float32)
        assert cosine_similarity(v1, v2) == 0.0


class TestComputeCentroid:
    """Tests for compute_centroid function."""

    def test_single_embedding(self) -> None:
        """Test centroid of single embedding is the embedding itself."""
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        centroid = compute_centroid([v])
        np.testing.assert_array_equal(centroid, v)

    def test_multiple_embeddings(self) -> None:
        """Test centroid of multiple embeddings."""
        v1 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        v2 = np.array([3.0, 2.0, 1.0], dtype=np.float32)
        centroid = compute_centroid([v1, v2])
        expected = np.array([2.0, 2.0, 2.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(centroid, expected)

    def test_empty_list_raises(self) -> None:
        """Test empty list raises ValueError."""
        with pytest.raises(ValueError):
            compute_centroid([])


class TestIsSameVoiceprint:
    """Tests for is_same_voiceprint function."""

    def test_identical_embeddings(self) -> None:
        """Test identical embeddings are same voiceprint."""
        v = np.random.randn(192).astype(np.float32)
        assert is_same_voiceprint(v, v) is True

    def test_different_embeddings(self) -> None:
        """Test very different embeddings are not same voiceprint."""
        v1 = np.array([1.0] * 192, dtype=np.float32)
        v2 = np.array([-1.0] * 192, dtype=np.float32)
        assert is_same_voiceprint(v1, v2) is False

    def test_custom_threshold(self) -> None:
        """Test custom threshold works."""
        v1 = np.random.randn(192).astype(np.float32)
        v2 = v1 * 0.5 + np.random.randn(192).astype(np.float32) * 0.1
        # With very low threshold, should pass
        assert is_same_voiceprint(v1, v2, threshold=0.0) is True


class TestVoiceprintExtractor:
    """Tests for VoiceprintExtractor class."""

    def test_embedding_dim(self, extractor: VoiceprintExtractor) -> None:
        """Test embedding dimension is 512 (CAM++ model)."""
        assert extractor.embedding_dim == 512

    def test_extract_real_audio(
        self,
        extractor: VoiceprintExtractor,
        japanese_wav: Path,
    ) -> None:
        """Test extracting embedding from real audio."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, _ = sf.read(str(japanese_wav), dtype="float32")
        embedding = extractor.extract(audio)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (512,)  # CAM++ model outputs 512 dimensions
        assert embedding.dtype == np.float32

    def test_same_audio_similar_embedding(
        self,
        extractor: VoiceprintExtractor,
        japanese_wav: Path,
    ) -> None:
        """Test same audio produces same embedding."""
        if not japanese_wav.exists():
            pytest.skip("Test WAV file not found")

        audio, _ = sf.read(str(japanese_wav), dtype="float32")
        embedding1 = extractor.extract(audio)
        embedding2 = extractor.extract(audio)

        similarity = cosine_similarity(embedding1, embedding2)
        assert similarity == pytest.approx(1.0, abs=0.01)
