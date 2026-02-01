"""DigitVoiceprint model for storing voice embeddings."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel
from ulid import ULID

if TYPE_CHECKING:
    from vca_auth.models.speaker import Speaker

# Embedding dimension for CAM++ model
EMBEDDING_DIM = 512


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(ULID())


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


class DigitVoiceprint(SQLModel, table=True):
    """Model for storing digit-specific voice embeddings."""

    __tablename__ = "digit_voiceprints"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("speaker_id", "digit", name="uq_speaker_digit"),)

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(
        default_factory=_generate_ulid,
        unique=True,
        index=True,
        max_length=26,
    )
    speaker_id: int = Field(foreign_key="speakers.id", index=True)
    digit: str = Field(max_length=1)  # "0" to "9"
    embedding: bytes = Field()  # 512-dim float32 = 2048 bytes
    created_at: datetime = Field(default_factory=_utc_now)

    speaker: "Speaker" = Relationship(back_populates="voiceprints")

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
