from pydantic import BaseModel

from app.schemas.chat import LineageData


class SchemaColumn(BaseModel):
    name: str
    type: str = ""


class SchemaCompareRequest(BaseModel):
    columns: list[SchemaColumn] = []
    preferred_query: str = ""


class SchemaMatchItem(BaseModel):
    urn: str
    name: str
    description: str = ""
    platform: str = ""
    domain: str = ""
    url: str | None = None
    similarity: float = 0.0
    matched_columns: list[str] = []
    missing_columns: list[str] = []
    additional_columns: list[str] = []


class SchemaCompareResponse(BaseModel):
    candidates: list[SchemaMatchItem] = []
    total: int = 0


class DatasetQuery(BaseModel):
    dataset: str
    columns: list[str] = []


class SqlJoin(BaseModel):
    table: str
    column: str
    reason: str = ""


class SqlResponse(BaseModel):
    dataset: str = ""
    urn: str = ""
    selected_columns: list[str] = []
    unavailable_columns: list[str] = []
    sql: str = ""
    joins: list[SqlJoin] = []
    explanation: list[str] = []
    valid: bool = False


class ImpactItem(BaseModel):
    urn: str
    name: str
    url: str | None = None
    kind: str = "dataset"


class ImpactResponse(BaseModel):
    dataset: str = ""
    urn: str = ""
    affected_datasets: list[ImpactItem] = []
    affected_dashboards: list[ImpactItem] = []
    affected_pipelines: list[ImpactItem] = []
    affected_jobs: list[ImpactItem] = []
    business_impact: list[str] = []
    risk_level: str = "low"
    valid: bool = False


class QualityDimension(BaseModel):
    key: str
    label: str
    score: int = 0
    status: str = "Missing"
    detail: str = ""


class QualityResponse(BaseModel):
    dataset: str = ""
    urn: str = ""
    dimensions: list[QualityDimension] = []
    overall_score: int = 0
    highlights: list[str] = []
    recommendations: list[str] = []
    valid: bool = False


class ReportSection(BaseModel):
    title: str
    lines: list[str] = []


class ReportAssessment(BaseModel):
    dimension: str
    score: int = 0
    rating: str = ""
    stars: int = 0


class ReportResponse(BaseModel):
    dataset: str = ""
    urn: str = ""
    sections: list[ReportSection] = []
    assessment: list[ReportAssessment] = []
    overall_score: int = 0
    overall_rating: str = ""
    recommendations: list[str] = []
    valid: bool = False