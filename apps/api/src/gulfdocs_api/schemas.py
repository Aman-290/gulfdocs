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


class ExtractionFieldResponse(BaseModel):
    key: str
    value: str | list[str] | None
    confidence: float
    citations: list[dict[str, Any]]


class ValidationIssueResponse(BaseModel):
    code: str
    severity: str
    description: str
    related_fields: list[str]
    source_page: int | None
    suggested_action: str
    resolved: bool


class ExtractionResponse(BaseModel):
    document_id: UUID
    schema_version: str
    document_type: str | None
    fields: list[ExtractionFieldResponse]
    issues: list[ValidationIssueResponse]
    approved_output: dict[str, Any] | None


class CorrectExtractionRequest(BaseModel):
    field_key: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    value: str | list[str] | None
    reason: str | None = Field(default=None, max_length=500)


class ApproveDocumentRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2_000)
