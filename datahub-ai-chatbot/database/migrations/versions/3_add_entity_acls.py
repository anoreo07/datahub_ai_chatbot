"""Add entity_acls table

Revision ID: 3_add_entity_acls
Revises: 2_add_audit_logs
Create Date: 2026-07-22 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3_add_entity_acls"
down_revision: str | None = "2_add_audit_logs"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "entity_acls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_urn", sa.String(512), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowed_user_ids", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("allowed_groups", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("denied_user_ids", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("denied_groups", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("classification", sa.String(64), nullable=False, server_default="internal"),
        sa.Column("tenant_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entity_acls_entity_urn"), "entity_acls", ["entity_urn"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_entity_acls_entity_urn"), table_name="entity_acls")
    op.drop_table("entity_acls")
