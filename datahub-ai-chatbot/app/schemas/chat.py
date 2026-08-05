from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    filters: dict = {}
    suggested_name: str | None = None
    model: str | None = None


class Suggestion(BaseModel):
    original: str = ""
    suggested: str = ""


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


class LineageNode(BaseModel):
    name: str = ""
    urn: str = ""
    url: str | None = None
    entity_type: str = "dataset"


class LineageData(BaseModel):
    entity_name: str = ""
    entity_urn: str = ""
    entity_url: str | None = None
    upstreams: list[LineageNode] = []
    downstreams: list[LineageNode] = []


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
    suggestion: Suggestion | None = None
    lineage: LineageData | None = None
