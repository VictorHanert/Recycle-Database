"""Add updated_at to conversations and joined_at to conversation_participants

Revision ID: b7af2c4d2f9e
Revises: c1e2f3g4h5i6
Create Date: 2025-11-26 13:21:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7af2c4d2f9e"
down_revision: Union[str, None] = "c1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_conversations_updated_at", "conversations", ["updated_at"], unique=False
    )
    op.execute(sa.text("UPDATE conversations SET updated_at = created_at"))
    op.alter_column(
        "conversations",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    op.add_column(
        "conversation_participants",
        sa.Column(
            "joined_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE conversation_participants SET joined_at = "
            "COALESCE(joined_at, CURRENT_TIMESTAMP)"
        )
    )
    op.alter_column(
        "conversation_participants",
        "joined_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    op.alter_column(
        "conversation_participants",
        "joined_at",
        server_default=None,
        existing_type=sa.DateTime(),
    )
    op.drop_column("conversation_participants", "joined_at")

    op.alter_column(
        "conversations",
        "updated_at",
        server_default=None,
        existing_type=sa.DateTime(),
    )
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_column("conversations", "updated_at")
