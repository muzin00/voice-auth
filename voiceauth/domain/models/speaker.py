"""Speaker domain model for voice authentication."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ulid import ULID


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(ULID())


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


@dataclass
class Speaker:
    """Speaker entity representing a registered user for voice authentication."""

    speaker_id: str
    speaker_name: str | None = None
    pin_hash: str | None = None
    id: int | None = None
    public_id: str = field(default_factory=_generate_ulid)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
