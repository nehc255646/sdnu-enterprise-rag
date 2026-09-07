from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocTypeLiteral = Literal["resume", "jd", "internship", "kb", "other"]


class HealthResponse(BaseModel):
    status: str
    service: str
    env: str


class IngestCreateResponse(BaseModel):
    document_id: str
    status: str
    message: str


class IngestStatusResponse(BaseModel):
    document_id: str
    tenant_id: str
    filename: str
    doc_type: str
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentListItem(BaseModel):
    document_id: str
    tenant_id: str
    filename: str
    doc_type: str
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentListResponse(BaseModel):
    tenant_id: str
    total: int
    items: list[DocumentListItem]


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(5, ge=1, le=50)
    doc_type: DocTypeLiteral | None = None


class RetrieveHit(BaseModel):
    score: float
    point_id: str
    text: str
    document_id: str | None = None
    doc_type: str | None = None
    chunk_index: int | None = None
    filename: str | None = None
    tenant_id: str | None = None


class RetrieveResponse(BaseModel):
    tenant_id: str
    query: str
    hits: list[RetrieveHit]
