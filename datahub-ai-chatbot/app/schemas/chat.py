from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    filters: dict = {}


class CitationItem(BaseModel):
    id: str
    source_type: str = "datahub_entity"
    entity_urn: str = ""
    entity_name: str = ""
    url: str | None = None
    page: int | None = None
    section: str | None = None


class EntityItem(BaseModel):
    urn: str = ""
    name: str = ""
    url: str | None = None


class ChatResponse(BaseModel):
    answer: str = ""
    intent: str = "GENERAL"
    entities: list[EntityItem] = []
    citations: list[CitationItem] = []
    confidence: str = "low"
    ambiguous: bool = False
    insufficient_context: bool = False
    trace_id: str = ""
    conversation_id: str | None = None
