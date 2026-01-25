from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from vca_core.shared import model_fields

if TYPE_CHECKING:
    from vca_core.models.speaker import Speaker
    from vca_core.models.voiceprint import Voiceprint


class VoiceSample(SQLModel, table=True):
    """音声サンプルモデル."""

    __tablename__ = "voice_sample"  # type: ignore[assignment]

    id: int | None = model_fields.primary_key_field()
    public_id: str = model_fields.public_id_field()
    created_at: datetime = model_fields.created_at_field()
    updated_at: datetime = model_fields.updated_at_field()
    speaker_id: int = Field(foreign_key="speaker.id", index=True)
    audio_file_path: str = Field(max_length=500)
    audio_format: str = Field(max_length=10)
    sample_rate: int | None = Field(default=None)
    channels: int | None = Field(default=None)

    # Relationships
    speaker: "Speaker" = Relationship(back_populates="voice_samples")
    voiceprint: Optional["Voiceprint"] = Relationship(back_populates="voice_sample")
