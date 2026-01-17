from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from vca_core.shared import model_fields

if TYPE_CHECKING:
    from vca_core.models.passphrase import Passphrase
    from vca_core.models.voice_sample import VoiceSample
    from vca_core.models.voiceprint import Voiceprint


class Speaker(SQLModel, table=True):
    """話者モデル."""

    __tablename__ = "speaker"  # type: ignore[assignment]

    id: int | None = model_fields.primary_key_field()
    public_id: str = model_fields.public_id_field()
    created_at: datetime = model_fields.created_at_field()
    updated_at: datetime = model_fields.updated_at_field()
    speaker_id: str = Field(index=True, unique=True, max_length=100)
    speaker_name: str | None = Field(default=None, max_length=100)

    # Relationships
    voice_samples: list["VoiceSample"] = Relationship(back_populates="speaker")
    voiceprints: list["Voiceprint"] = Relationship(back_populates="speaker")
    passphrases: list["Passphrase"] = Relationship(back_populates="speaker")
