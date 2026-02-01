from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from vca_auth.shared import model_fields

if TYPE_CHECKING:
    from vca_auth.models.speaker import Speaker


class Voiceprint(SQLModel, table=True):
    """声紋モデル."""

    __tablename__ = "voiceprint"  # type: ignore[assignment]

    id: int | None = model_fields.primary_key_field()
    public_id: str = model_fields.public_id_field()
    created_at: datetime = model_fields.created_at_field()
    updated_at: datetime = model_fields.updated_at_field()
    speaker_id: int = Field(foreign_key="speaker.id", index=True)
    digit: str | None = Field(
        default=None,
        max_length=1,
        index=True,
        description="数字（0-9）。Noneの場合は全体声紋",
    )
    embedding: bytes = Field(description="声紋ベクトル（192次元）")

    # Relationships
    speaker: "Speaker" = Relationship(back_populates="voiceprints")
