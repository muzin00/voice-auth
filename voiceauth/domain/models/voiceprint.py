"""Voiceprint domain model for storing voice embeddings."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
from ulid import ULID

# Embedding dimension for CAM++ model
EMBEDDING_DIM = 512


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(ULID())


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


@dataclass
class Voiceprint:
    """Voiceprint entity for storing digit-specific voice embeddings."""

    speaker_id: int
    digit: str  # "0" to "9"
    embedding: bytes  # 512-dim float32 = 2048 bytes
    id: int | None = None
    public_id: str = field(default_factory=_generate_ulid)
    created_at: datetime = field(default_factory=_utc_now)

    @staticmethod
    def serialize_embedding(embedding: np.ndarray) -> bytes:
        """Convert numpy embedding array to bytes for storage.

        Args:
            embedding: numpy array of shape (512,) with float32 dtype

        Returns:
            bytes representation of the embedding
        """
        return embedding.astype(np.float32).tobytes()

    @staticmethod
    def deserialize_embedding(data: bytes) -> np.ndarray:
        """Convert stored bytes back to numpy embedding array.

        Args:
            data: bytes representation of the embedding

        Returns:
            numpy array of shape (512,) with float32 dtype
        """
        return np.frombuffer(data, dtype=np.float32)
