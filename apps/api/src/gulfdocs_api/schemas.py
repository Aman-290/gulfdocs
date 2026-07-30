from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    error_id: str
    request_id: str
    extensions: dict[str, Any] = Field(default_factory=dict)


class PresignUploadRequest(BaseModel):
    filename: str = Field(min_length=5, max_length=255)
    size_bytes: int = Field(gt=0)
    content_type: str = Field(pattern=r"^application/pdf$")


class PresignUploadResponse(BaseModel):
    document_id: UUID
    upload_url: str
    method: str = "PUT"
    expires_at: datetime
    required_headers: dict[str, str]


class CompleteUploadRequest(BaseModel):
    document_id: UUID


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    size_bytes: int | None
    page_count: int | None
    content_type: str | None
    created_at: datetime
    updated_at: datetime
