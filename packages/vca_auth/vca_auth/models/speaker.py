"""Speaker model for voice authentication."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel
from ulid import ULID

if TYPE_CHECKING:
    from vca_auth.models.digit_voiceprint import DigitVoiceprint


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(ULID())


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


class Speaker(SQLModel, table=True):
    """Speaker model representing a registered user for voice authentication."""

    __tablename__ = "speakers"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(
        default_factory=_generate_ulid,
        unique=True,
        index=True,
        max_length=26,
    )
    speaker_id: str = Field(unique=True, index=True, max_length=255)
    speaker_name: str | None = Field(default=None, max_length=255)
    pin_hash: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    voiceprints: list["DigitVoiceprint"] = Relationship(
        back_populates="speaker",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
