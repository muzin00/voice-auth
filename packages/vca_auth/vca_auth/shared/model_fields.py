"""共通のモデルフィールド定義."""

from datetime import UTC, datetime

from sqlmodel import Field
from ulid import ULID


def primary_key_field() -> int | None:
    """主キーフィールド."""
    return Field(default=None, primary_key=True)


def public_id_field() -> str:
    """公開用ID（ULID）フィールド."""
    return Field(
        index=True,
        unique=True,
        max_length=26,
        default_factory=lambda: str(ULID()),
    )


def created_at_field() -> datetime:
    """作成日時フィールド（UTC）."""
    return Field(default_factory=lambda: datetime.now(UTC))


def updated_at_field() -> datetime:
    """更新日時フィールド（UTC）."""
    return Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": datetime.now(UTC)},
    )
