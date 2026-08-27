"""Add image storage + vision cache tables

Revision ID: 6_add_image_storage
Revises: 5_add_rbac
Create Date: 2026-08-07 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision: str = "6_add_image_storage"
down_revision: str | None = "5_add_rbac"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "image_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("image_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("thumbnail_path", sa.String(1024), nullable=True),
        sa.Column("upload_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="uploaded"),
        sa.Column("vision_cache_id", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("image_type", sa.String(32), nullable=True),
        sa.Column("dataset_detected", sa.String(512), nullable=True),
        sa.Column("vision_result", sa.JSON(), nullable=True),
        sa.Column("image_context", sa.JSON(), nullable=True),
        sa.Column("parse_error", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_image_records_image_id"), "image_records", ["image_id"], unique=True)
    op.create_index(op.f("ix_image_records_user_id"), "image_records", ["user_id"])
    op.create_index(op.f("ix_image_records_conversation_id"), "image_records", ["conversation_id"])
    op.create_index(op.f("ix_image_records_status"), "image_records", ["status"])
    op.create_index(op.f("ix_image_records_content_hash"), "image_records", ["content_hash"])
    op.create_index(op.f("ix_image_records_is_deleted"), "image_records", ["is_deleted"])

    op.create_table(
        "vision_cache_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_id", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("vision_result", sa.JSON(), nullable=True),
        sa.Column("image_context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vision_cache_records_cache_id"), "vision_cache_records", ["cache_id"], unique=True)
    op.create_index(op.f("ix_vision_cache_records_content_hash"), "vision_cache_records", ["content_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_vision_cache_records_content_hash"), table_name="vision_cache_records")
    op.drop_index(op.f("ix_vision_cache_records_cache_id"), table_name="vision_cache_records")
    op.drop_table("vision_cache_records")
    op.drop_index(op.f("ix_image_records_is_deleted"), table_name="image_records")
    op.drop_index(op.f("ix_image_records_content_hash"), table_name="image_records")
    op.drop_index(op.f("ix_image_records_status"), table_name="image_records")
    op.drop_index(op.f("ix_image_records_conversation_id"), table_name="image_records")
    op.drop_index(op.f("ix_image_records_user_id"), table_name="image_records")
    op.drop_index(op.f("ix_image_records_image_id"), table_name="image_records")
    op.drop_table("image_records")
