"""Add human_reviews and regression_candidates tables.

Revision ID: 8_human_review
Revises: 7_add_ragas_evaluation
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8_human_review"
down_revision = "7_add_ragas_evaluation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("interaction_id", sa.Integer(), sa.ForeignKey("interaction_logs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trace_id", sa.String(32), nullable=False, index=True),
        sa.Column("reviewer_id", sa.String(128), nullable=False, index=True),
        sa.Column("reviewer_name", sa.String(256), nullable=False, server_default=""),
        sa.Column("overall_label", sa.String(32), nullable=False),
        sa.Column("correctness_score", sa.Float(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("groundedness_score", sa.Float(), nullable=True),
        sa.Column("retrieval_quality", sa.Float(), nullable=True),
        sa.Column("citation_quality", sa.Float(), nullable=True),
        sa.Column("intent_correctness", sa.Boolean(), nullable=True),
        sa.Column("entity_resolution_correctness", sa.Boolean(), nullable=True),
        sa.Column("context_usage", sa.Boolean(), nullable=True),
        sa.Column("permission_correctness", sa.String(8), nullable=True),
        sa.Column("error_categories", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("failure_stage", sa.String(32), nullable=True),
        sa.Column("reviewer_confidence", sa.String(16), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("reviewed_question_snapshot", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_answer_snapshot", sa.Text(), nullable=False, server_default=""),
        sa.Column("ragas_snapshot", postgresql.JSON(), nullable=True),
        sa.Column("is_adjudication", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("adjudicator_id", sa.String(128), nullable=True),
        sa.Column("adjudicator_name", sa.String(256), nullable=True),
        sa.Column("adjudicated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_decision", sa.String(32), nullable=True),
        sa.Column("is_consensus", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_disagreement", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_human_reviews_trace_id", "human_reviews", ["trace_id"])
    op.create_index("ix_human_reviews_interaction_id", "human_reviews", ["interaction_id"])
    op.create_index("ix_human_reviews_reviewer_id", "human_reviews", ["reviewer_id"])

    op.create_table(
        "regression_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("interaction_id", sa.Integer(), sa.ForeignKey("interaction_logs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trace_id", sa.String(32), nullable=False, index=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("human_reviews.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("original_question", sa.Text(), nullable=False),
        sa.Column("actual_answer", sa.Text(), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_intent", sa.String(64), nullable=True),
        sa.Column("expected_entities", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("expected_evidence", sa.Text(), nullable=True),
        sa.Column("failure_category", sa.String(64), nullable=False),
        sa.Column("failure_stage", sa.String(32), nullable=False),
        sa.Column("creator_id", sa.String(128), nullable=False),
        sa.Column("creator_name", sa.String(256), nullable=False, server_default=""),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open", index=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_regression_candidates_trace_id", "regression_candidates", ["trace_id"])
    op.create_index("ix_regression_candidates_interaction_id", "regression_candidates", ["interaction_id"])
    op.create_index("ix_regression_candidates_review_id", "regression_candidates", ["review_id"])


def downgrade() -> None:
    op.drop_table("regression_candidates")
    op.drop_table("human_reviews")
