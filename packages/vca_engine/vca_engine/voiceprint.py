"""Voiceprint extraction using CAM++."""

import numpy as np
import sherpa_onnx

from .exceptions import ModelNotLoadedError, SpeakerEmbeddingError
from .settings import settings


class VoiceprintExtractor:
    """Voiceprint extractor using CAM++."""

    def __init__(self, model_path: str | None = None) -> None:
        """Initialize voiceprint extractor.

        Args:
            model_path: Path to CAM++ model. Defaults to settings path.
        """
        self._extractor: sherpa_onnx.SpeakerEmbeddingExtractor | None = None
        self._model_path = model_path or str(settings.speaker_model_path)

    def _ensure_loaded(self) -> sherpa_onnx.SpeakerEmbeddingExtractor:
        """Ensure voiceprint model is loaded."""
        if self._extractor is None:
            self.load()
        if self._extractor is None:
            raise ModelNotLoadedError("Voiceprint model not loaded")
        return self._extractor

    def load(self) -> None:
        """Load the voiceprint model."""
        try:
            config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=self._model_path,
                num_threads=settings.speaker_num_threads,
                debug=False,
            )
            self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        except Exception as e:
            raise SpeakerEmbeddingError(f"Failed to load voiceprint model: {e}") from e

    @property
    def embedding_dim(self) -> int:
        """Get the dimension of voiceprint embeddings."""
        extractor = self._ensure_loaded()
        return extractor.dim

    def extract(
        self,
        audio: np.ndarray,
        sample_rate: int | None = None,
    ) -> np.ndarray:
        """Extract voiceprint from audio.

        Args:
            audio: Audio samples as float32 numpy array.
            sample_rate: Sample rate of audio. Defaults to settings.target_sample_rate.

        Returns:
            Voiceprint as float32 numpy array (512 dimensions for CAM++ model).

        Raises:
            SpeakerEmbeddingError: If extraction fails.
        """
        extractor = self._ensure_loaded()

        if sample_rate is None:
            sample_rate = settings.target_sample_rate

        try:
            stream = extractor.create_stream()
            stream.accept_waveform(sample_rate, audio.astype(np.float32))

            if not extractor.is_ready(stream):
                raise SpeakerEmbeddingError(
                    "Voiceprint extraction not ready - audio may be too short"
                )

            embedding = np.array(extractor.compute(stream), dtype=np.float32)
            return embedding

        except SpeakerEmbeddingError:
            raise
        except Exception as e:
            raise SpeakerEmbeddingError(f"Voiceprint extraction failed: {e}") from e


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings.

    Args:
        embedding1: First embedding vector.
        embedding2: Second embedding vector.

    Returns:
        Cosine similarity score in range [-1, 1].
    """
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(np.dot(embedding1, embedding2) / (norm1 * norm2))


def compute_centroid(embeddings: list[np.ndarray]) -> np.ndarray:
    """Compute centroid (mean) of multiple embeddings.

    Args:
        embeddings: List of embedding vectors.

    Returns:
        Centroid embedding as float32 numpy array.

    Raises:
        ValueError: If embeddings list is empty.
    """
    if not embeddings:
        raise ValueError("Cannot compute centroid of empty embeddings list")

    return np.mean(embeddings, axis=0).astype(np.float32)


def is_same_voiceprint(
    embedding1: np.ndarray,
    embedding2: np.ndarray,
    threshold: float | None = None,
) -> bool:
    """Check if two embeddings belong to the same voiceprint.

    Args:
        embedding1: First embedding vector.
        embedding2: Second embedding vector.
        threshold: Similarity threshold. Defaults to settings.speaker_similarity_threshold.

    Returns:
        True if similarity is above threshold, False otherwise.
    """
    if threshold is None:
        threshold = settings.speaker_similarity_threshold

    similarity = cosine_similarity(embedding1, embedding2)
    return similarity >= threshold
