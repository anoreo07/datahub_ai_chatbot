import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class AuthMode(StrEnum):
    MOCK = "mock"
    HEADER = "header"
    JWT = "jwt"


class UserRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    STEWARD = "steward"
    VIEWER = "viewer"
    USER = "user"


class UserContext(BaseModel):
    user_id: str
    email: str = ""
    display_name: str = ""
    groups: list[str] = []
    roles: list[str] = []
    is_admin: bool = False
    tenant_id: str | None = None
    request_id: str = ""

    @classmethod
    def anonymous(cls) -> "UserContext":
        return cls(user_id="anonymous", display_name="Anonymous")

    @classmethod
    def developer(cls) -> "UserContext":
        return cls(
            user_id="local-developer",
            email="dev@local",
            display_name="Local Developer",
            roles=["admin"],
            is_admin=True,
            request_id=uuid.uuid4().hex[:12],
        )


class EntityAcl(BaseModel):
    entity_urn: str
    is_public: bool = False
    allowed_user_ids: list[str] = []
    allowed_emails: list[str] = []
    allowed_groups: list[str] = []
    denied_user_ids: list[str] = []
    denied_groups: list[str] = []
    tenant_id: str | None = None
    classification: str = "internal"
    inherited_from_domain: bool = False


class AuditAction(StrEnum):
    VIEW_ENTITY = "view_entity"
    SEARCH = "search"
    CHAT = "chat"
    SYNC = "sync"
    ADMIN = "admin_action"


class AuditDecision(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class AuditEvent(BaseModel):
    id: str = ""
    request_id: str = ""
    user_id: str = ""
    action: str = ""
    resource_urn: str = ""
    decision: str = ""
    reason: str = ""
    timestamp: datetime | None = None
    metadata: dict = {}
