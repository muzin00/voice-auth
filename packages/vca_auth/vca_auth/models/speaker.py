from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from vca_auth.shared import model_fields

if TYPE_CHECKING:
    from vca_auth.models.voiceprint import Voiceprint


class Speaker(SQLModel, table=True):
    """話者モデル."""

    __tablename__ = "speaker"  # type: ignore[assignment]

    id: int | None = model_fields.primary_key_field()
    public_id: str = model_fields.public_id_field()
    created_at: datetime = model_fields.created_at_field()
    updated_at: datetime = model_fields.updated_at_field()
    speaker_id: str = Field(index=True, unique=True, max_length=100)
    speaker_name: str | None = Field(default=None, max_length=100)
    pin_hash: str | None = Field(
        default=None, max_length=64, description="PINのハッシュ"
    )

    # Relationships
    voiceprints: list["Voiceprint"] = Relationship(back_populates="speaker")
