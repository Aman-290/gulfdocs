from datetime import date, datetime
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
    document_type: str | None = None
    detected_language: str | None = None
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


class PrivateQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class PrivateAnswerResponse(BaseModel):
    question_id: UUID
    answer: str
    citations: list[dict[str, Any]]
    supported: bool
    model_name: str
    prompt_version: str
    latency_ms: int
    created_at: datetime


class AuditEventResponse(BaseModel):
    id: UUID
    event_type: str
    safe_metadata: dict[str, Any]
    created_at: datetime


class UsageSummary(BaseModel):
    usage_date: date
    uploads_used: int
    uploads_limit: int
    questions_used: int
    questions_limit: int
    generated_tokens: int


class QualitySummary(BaseModel):
    total_documents: int
    failed_documents: int
    needs_review_documents: int
    approved_documents: int
    failure_rate: float
    needs_review_rate: float
    average_processing_ms: float | None
    median_processing_ms: float | None
    p95_processing_ms: float | None


class DailyTokenSummary(BaseModel):
    date: date
    tokens: int


class MetricsSummary(BaseModel):
    generated_at: datetime
    usage: UsageSummary
    quality: QualitySummary
    daily_tokens: list[DailyTokenSummary]
