import datetime
import enum

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SyncStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class IndexJobStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    urn: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(128), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    datahub_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EntityChunk(Base):
    __tablename__ = "entity_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    entity_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    chunk_type: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    indexed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SyncCheckpoint(Base):
    __tablename__ = "sync_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    cursor: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_success_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    checkpoint_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EntityAclDB(Base):
    __tablename__ = "entity_acls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_urn: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_user_ids: Mapped[list] = mapped_column(postgresql.ARRAY(String), nullable=False, default=list)
    allowed_groups: Mapped[list] = mapped_column(postgresql.ARRAY(String), nullable=False, default=list)
    denied_user_ids: Mapped[list] = mapped_column(postgresql.ARRAY(String), nullable=False, default=list)
    denied_groups: Mapped[list] = mapped_column(postgresql.ARRAY(String), nullable=False, default=list)
    classification: Mapped[str] = mapped_column(String(64), nullable=False, default="internal")
    tenant_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    render_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RbacRoleDB(Base):
    __tablename__ = "rbac_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # All-domain role flag (e.g. the built-in admin role).
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Legacy fallback: role derived from a user's group membership.
    group_names: Mapped[list[str]] = mapped_column(
        postgresql.ARRAY(String), nullable=False, default=list
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RbacRoleDomainDB(Base):
    __tablename__ = "rbac_role_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rbac_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserAccount(Base):
    __tablename__ = "rbac_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RbacUserRole(Base):
    __tablename__ = "rbac_user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rbac_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_urn: Mapped[str] = mapped_column(String(512), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImageStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class ImageRecord(Base):
    """Metadata for an uploaded image. Binary payload lives on storage, not here."""

    __tablename__ = "image_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    upload_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ImageStatus.UPLOADED.value, index=True
    )
    vision_cache_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Soft-delete support.
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Vision / Image Context results (JSON payload, cached after re-run).
    image_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dataset_detected: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vision_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parse_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class VisionCacheRecord(Base):
    """Cached vision analysis result keyed by image content hash."""

    __tablename__ = "vision_cache_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    vision_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class JobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Job(Base):
    """Generic background job tracking model.

    Tracks any background operation (sync, evaluation, index rebuild, etc.).
    Notifications are linked to jobs via job_id.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=JobStatus.PENDING, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    entity_urn: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Notification(Base):
    """User notification linked to a background job.

    Each notification is associated with a job_id and a user.
    Status reflects the job status (PENDING/RUNNING/SUCCESS/FAILED).
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=JobStatus.PENDING, index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    job_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InteractionLog(Base):
    """Admin response log — every chat interaction for audit and RAGAS evaluation."""

    __tablename__ = "interaction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Request
    question: Mapped[str] = mapped_column(Text, nullable=False)
    selected_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Intent resolution
    intent: Mapped[str] = mapped_column(String(64), nullable=False)
    message_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    routing_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    chosen_tool: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Entity resolution
    entity_hint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entity_resolved_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entity_resolved_urn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    resolution_state: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Response
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    insufficient_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Quality metrics
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_score: Mapped[float | None] = mapped_column(nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Retrieved context snapshot for RAGAS evaluation (JSON array of context strings)
    retrieved_contexts: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # RAGAS scores (computed async)
    evaluation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="NOT_EVALUATED"
    )  # NOT_EVALUATED | PENDING | RUNNING | COMPLETED | FAILED
    evaluation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evaluated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    faithfulness: Mapped[float | None] = mapped_column(nullable=True)
    faithfulness_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    answer_relevancy: Mapped[float | None] = mapped_column(nullable=True)
    answer_relevancy_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    context_precision: Mapped[float | None] = mapped_column(nullable=True)
    context_precision_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    context_recall: Mapped[float | None] = mapped_column(nullable=True)
    context_recall_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Human review (separate from RAGAS machine evaluation)
    human_review: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # accepted | needs_review | incorrect | hallucination | insufficient_evidence
    human_review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HumanReview(Base):
    """Human quality review — each reviewer gets their own record per interaction."""

    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interaction_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reviewer_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")

    # Core review fields
    overall_label: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # accepted | needs_review | incorrect | hallucination | insufficient_evidence
    correctness_score: Mapped[float | None] = mapped_column(nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(nullable=True)
    groundedness_score: Mapped[float | None] = mapped_column(nullable=True)
    retrieval_quality: Mapped[float | None] = mapped_column(nullable=True)
    citation_quality: Mapped[float | None] = mapped_column(nullable=True)

    # Stage-specific correctness
    intent_correctness: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    entity_resolution_correctness: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    context_usage: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    permission_correctness: Mapped[str | None] = mapped_column(
        String(8), nullable=True
    )  # PASS | FAIL | N/A

    # Taxonomy
    error_categories: Mapped[list] = mapped_column(
        postgresql.ARRAY(String), nullable=False, default=list
    )
    failure_stage: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # INTENT | ENTITY_RESOLUTION | RETRIEVAL | TOOL | CONTEXT | GENERATION | CITATION | PERMISSION | UI | UNKNOWN

    # Confidence and notes
    reviewer_confidence: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )  # high | medium | low
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Snapshots at review time (avoid duplication with interaction_logs)
    reviewed_question_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_answer_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ragas_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Adjudication support
    is_adjudication: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    adjudicator_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    adjudicator_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    adjudicated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Consensus tracking
    is_consensus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_disagreement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Version for optimistic concurrency
    review_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Metadata
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RegressionCandidate(Base):
    """Regression test candidate created from a reviewed interaction."""

    __tablename__ = "regression_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interaction_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("human_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Original question and answer snapshots
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    actual_answer: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_entities: Mapped[list] = mapped_column(
        postgresql.ARRAY(String), nullable=False, default=list
    )
    expected_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Failure classification
    failure_category: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_stage: Mapped[str] = mapped_column(String(32), nullable=False)

    # Source tracking
    creator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    creator_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status lifecycle
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open", index=True
    )  # open | in_progress | resolved | wont_fix

    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvidenceRecordDB(Base):
    """Persisted evidence records for context propagation across restarts/workers."""

    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(8), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entity_urn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    citation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
