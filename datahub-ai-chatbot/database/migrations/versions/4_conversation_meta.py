"""Add title/pinned/favorite to conversation_history

Revision ID: 4_conversation_meta
Revises: 3_add_entity_acls
Create Date: 2026-08-06 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision: str = "4_conversation_meta"
down_revision: str | None = "3_add_entity_acls"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("conversation_history", sa.Column("title", sa.String(512), nullable=True))
    op.add_column(
        "conversation_history",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "conversation_history",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("conversation_history", "is_favorite")
    op.drop_column("conversation_history", "is_pinned")
    op.drop_column("conversation_history", "title")
