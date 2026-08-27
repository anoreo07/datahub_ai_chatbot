"""Add RAGAS evaluation columns and evidence_records table

Revision ID: 7_add_ragas_evaluation
Revises: 6_add_image_storage
Create Date: 2026-08-21 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision: str = "7_add_ragas_evaluation"
down_revision: str | None = "6_add_image_storage"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # --- interaction_logs: add evaluation + context columns ---
    op.add_column(
        "interaction_logs",
        sa.Column("retrieved_contexts", sa.JSON(), nullable=True),
    )
    op.add_column(
        "interaction_logs",
        sa.Column(
            "evaluation_status",
            sa.String(16),
            nullable=False,
            server_default="NOT_EVALUATED",
        ),
    )
    op.add_column(
        "interaction_logs",
        sa.Column("evaluation_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "interaction_logs",
        sa.Column("evaluation_model", sa.String(128), nullable=True),
    )
    op.add_column(
        "interaction_logs",
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "interaction_logs",
        sa.Column("human_review", sa.String(32), nullable=True),
    )
    op.add_column(
        "interaction_logs",
        sa.Column("human_review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "interaction_logs",
        sa.Column("human_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_interaction_logs_evaluation_status"),
        "interaction_logs",
        ["evaluation_status"],
    )

    # --- evidence_records ---
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("conversation_id", sa.String(128), nullable=False),
        sa.Column("evidence_id", sa.String(8), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("entity_name", sa.String(512), nullable=True),
        sa.Column("entity_urn", sa.String(512), nullable=True),
        sa.Column("entity_type", sa.String(128), nullable=True),
        sa.Column("tool_name", sa.String(64), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("structured", sa.JSON(), nullable=True),
        sa.Column("citation", sa.JSON(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_records_user_id"),
        "evidence_records",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_evidence_records_conversation_id"),
        "evidence_records",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_table("evidence_records")
    op.drop_index(op.f("ix_interaction_logs_evaluation_status"), table_name="interaction_logs")
    op.drop_column("interaction_logs", "human_reviewed_at")
    op.drop_column("interaction_logs", "human_review_note")
    op.drop_column("interaction_logs", "human_review")
    op.drop_column("interaction_logs", "evaluated_at")
    op.drop_column("interaction_logs", "evaluation_model")
    op.drop_column("interaction_logs", "evaluation_error")
    op.drop_column("interaction_logs", "evaluation_status")
    op.drop_column("interaction_logs", "retrieved_contexts")
