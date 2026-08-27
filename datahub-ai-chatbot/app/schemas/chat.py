from pydantic import BaseModel

from app.schemas.quality import QualityReport


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    filters: dict = {}
    suggested_name: str | None = None
    model: str | None = None
    # Optional selected "+" menu action (e.g. "search", "sql", "impact", "lineage",
    # "quality", "report"). Treated as an intent hint by the semantic intent
    # resolver — never a mandatory execution path.
    selected_action: str | None = None
    # Optional data-related image attachments as `data:` URLs (base64). When
    # present, the Visual Understanding layer runs first and feeds the router.
    images: list[str] = []
    # When false, skip the fire-and-forget RAGAS evaluation to save Gemini API quota.
    ragas_enabled: bool = True


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
    entity_type: str | None = None
    platform: str | None = None
    domain: str | None = None
    description: str | None = None
    environment: str | None = None


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
    # Which pipeline produced the answer ("evidence_context", "field_property",
    # "thinking", "hybrid_search", "structured", ...) — orthogonal to `intent`,
    # which is the standard taxonomy label of what the question ASKS.
    answer_path: str | None = None
    entities: list[EntityItem] = []
    citations: list[CitationItem] = []
    confidence: str = "low"
    ambiguous: bool = False
    insufficient_context: bool = False
    trace_id: str = ""
    conversation_id: str | None = None
    suggestion: Suggestion | None = None
    lineage: LineageData | None = None
    quality_report: QualityReport | None = None
    # Structured vision-extraction result (present only for image requests).
    vision: dict | None = None
    selected_action: str | None = None
    response_time_ms: int | None = None

