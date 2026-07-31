from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    entity_type: str | None = None
    page: int = 1
    page_size: int = 20


class EntityResult(BaseModel):
    urn: str
    name: str
    entity_type: str
    description: str | None = None


class SearchResponse(BaseModel):
    results: list[EntityResult]
    total: int
    page: int
    page_size: int
