from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    INVOICE = "invoice"
    QUOTATION = "quotation"
    PURCHASE_ORDER = "purchase_order"
    CONTRACT = "contract"


class DocumentStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    QUEUED = "queued"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    FAILED = "failed"
    DELETED = "deleted"


class Citation(BaseModel):
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1, max_length=500)


class ExtractionField(BaseModel):
    key: str
    label: str
    value: str
    confidence: float = Field(ge=0, le=1)
    citations: list[Citation]


class ValidationIssue(BaseModel):
    severity: str
    code: str
    description: str
    related_fields: list[str]
    source_page: int | None = Field(default=None, ge=1)
    suggested_action: str


class DemoDocumentSummary(BaseModel):
    id: UUID
    name: str
    document_type: DocumentType
    detected_language: str
    status: DocumentStatus
    page_count: int = Field(ge=1)
    synthetic: bool = True
    updated_at: datetime


class DemoDocumentDetail(DemoDocumentSummary):
    fields: list[ExtractionField]
    validation_issues: list[ValidationIssue]
    supported_questions: list[str]
    processing: dict[str, str | int | float]


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    supported: bool
    model_name: str
    prompt_version: str
