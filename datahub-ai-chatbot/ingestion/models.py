import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OwnerType(StrEnum):
    BUSINESS_OWNER = "BUSINESS_OWNER"
    DATA_TECHNICAL_OWNER = "DATA_TECHNICAL_OWNER"
    SYSTEM_OWNER = "SYSTEM_OWNER"


class Owner(BaseModel):
    name: str
    email: str = ""
    type: str = "BUSINESS_OWNER"


class GlossaryTermRef(BaseModel):
    urn: str
    name: str = ""
    definition: str = ""
    domain_urn: str | None = None


class SchemaField(BaseModel):
    field_path: str = ""
    name: str = ""
    type: str = ""
    native_data_type: str = ""
    description: str | None = None
    nullable: bool = True
    is_primary_key: bool = False
    glossary_terms: list[str] = []
    tags: list[str] = []


class EntityRef(BaseModel):
    urn: str
    entity_type: str | None = None


class DocumentRef(BaseModel):
    title: str
    urn: str | None = None


class EntityPage(BaseModel):
    items: list[dict]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class Domain(BaseModel):
    urn: str
    name: str
    description: str = ""


class LineageEdge(BaseModel):
    upstream_urn: str
    downstream_urn: str
    edge_type: str = "UPSTREAM"
    source: str = ""
    created_at: datetime.datetime | None = None


class CanonicalEntity(BaseModel):
    urn: str
    entity_type: str
    name: str
    normalized_name: str = ""
    display_name: str | None = None
    description: str | None = None
    business_purpose: str | None = None
    platform: str | None = None
    environment: str | None = None
    domain: str | None = None
    domain_urn: str | None = None
    owners: list[Owner] = []
    schema_fields: list[SchemaField] = []
    glossary_terms: list[str] = []
    tags: list[str] = []
    upstreams: list[str] = []
    downstreams: list[str] = []
    linked_documents: list[str] = []
    certified: bool = False
    source_url: str | None = None
    raw_properties: dict = Field(default_factory=dict)
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    deleted: bool = False
    content_hash: str = ""
    raw_payload: dict | None = None

    @property
    def datahub_url(self) -> str | None:
        return self.source_url

    @datahub_url.setter
    def datahub_url(self, value: str | None) -> None:
        self.source_url = value


class Document(BaseModel):
    urn: str
    title: str
    description: str = ""
    sections: list[dict] = Field(default_factory=list)
    source_url: str | None = None
    related_entity_urns: list[str] = Field(default_factory=list)
