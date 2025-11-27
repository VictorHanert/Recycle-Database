"""add_message_reads_table

Revision ID: c1e2f3g4h5i6
Revises: 32dead81c695
Create Date: 2025-11-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1e2f3g4h5i6'
down_revision: Union[str, None] = '32dead81c695'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add message_reads table for tracking message read status."""
    op.create_table('message_reads',
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id', 'user_id')
    )
    op.create_index('ix_message_read_user', 'message_reads', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove message_reads table."""
    op.drop_index('ix_message_read_user', table_name='message_reads')
    op.drop_table('message_reads')