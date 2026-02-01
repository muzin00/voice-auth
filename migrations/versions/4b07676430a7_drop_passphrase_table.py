# type: ignore
# ruff: noqa
"""drop_passphrase_table

Revision ID: 4b07676430a7
Revises: 808d18e27e2f
Create Date: 2026-01-25 23:28:00.330099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '4b07676430a7'
down_revision: Union[str, Sequence[str], None] = '808d18e27e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_passphrase_voice_sample_id"), table_name="passphrase")
    op.drop_index(op.f("ix_passphrase_speaker_id"), table_name="passphrase")
    op.drop_index(op.f("ix_passphrase_public_id"), table_name="passphrase")
    op.drop_table("passphrase")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "passphrase",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "public_id", sqlmodel.sql.sqltypes.AutoString(length=26), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("speaker_id", sa.Integer(), nullable=False),
        sa.Column("voice_sample_id", sa.Integer(), nullable=False),
        sa.Column(
            "phrase", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["speaker_id"],
            ["speaker.id"],
        ),
        sa.ForeignKeyConstraint(
            ["voice_sample_id"],
            ["voice_sample.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_passphrase_public_id"), "passphrase", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_passphrase_speaker_id"), "passphrase", ["speaker_id"], unique=False
    )
    op.create_index(
        op.f("ix_passphrase_voice_sample_id"),
        "passphrase",
        ["voice_sample_id"],
        unique=False,
    )
