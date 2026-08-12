"""Add RBAC roles, role-domain mapping, users and user-role mapping

Revision ID: 5_add_rbac
Revises: 4_conversation_meta
Create Date: 2026-08-06 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5_add_rbac"
down_revision: str | None = "4_conversation_meta"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("group_names", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rbac_roles_name"), "rbac_roles", ["name"], unique=True)

    op.create_table(
        "rbac_role_domains",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["role_id"], ["rbac_roles.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_rbac_role_domains_role_id"), "rbac_role_domains", ["role_id"])

    op.create_table(
        "rbac_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("email", sa.String(256), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("password_hash", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rbac_users_user_id"), "rbac_users", ["user_id"], unique=True)
    op.create_index(op.f("ix_rbac_users_username"), "rbac_users", ["username"], unique=True)

    op.create_table(
        "rbac_user_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["role_id"], ["rbac_roles.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_rbac_user_roles_user_id"), "rbac_user_roles", ["user_id"])
    op.create_index(op.f("ix_rbac_user_roles_role_id"), "rbac_user_roles", ["role_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_rbac_user_roles_role_id"), table_name="rbac_user_roles")
    op.drop_index(op.f("ix_rbac_user_roles_user_id"), table_name="rbac_user_roles")
    op.drop_table("rbac_user_roles")
    op.drop_index(op.f("ix_rbac_users_username"), table_name="rbac_users")
    op.drop_index(op.f("ix_rbac_users_user_id"), table_name="rbac_users")
    op.drop_table("rbac_users")
    op.drop_index(op.f("ix_rbac_role_domains_role_id"), table_name="rbac_role_domains")
    op.drop_table("rbac_role_domains")
    op.drop_index(op.f("ix_rbac_roles_name"), table_name="rbac_roles")
    op.drop_table("rbac_roles")
