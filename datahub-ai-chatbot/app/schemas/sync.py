from datetime import datetime

from pydantic import BaseModel


class SyncTriggerRequest(BaseModel):
    entity_types: list[str] | None = None
    full: bool = False


class SyncStatusResponse(BaseModel):
    job_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
