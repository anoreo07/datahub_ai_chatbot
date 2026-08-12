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
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
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
