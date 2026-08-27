"""Add render_state JSON and updated_at to conversation_history.

Revision ID: 9_render_state
Revises: 8_add_human_review
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "9_render_state"
down_revision = "8_human_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_history",
        sa.Column("render_state", sa.JSON(), nullable=True),
    )
    op.add_column(
        "conversation_history",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversation_history", "updated_at")
    op.drop_column("conversation_history", "render_state")
