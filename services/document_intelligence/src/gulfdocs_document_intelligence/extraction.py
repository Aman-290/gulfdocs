from typing import Any

from pydantic import BaseModel, Field

from .models import Citation, DocumentType

SCHEMA_VERSION = "2026-07-30.1"

REQUIRED_FIELDS: dict[DocumentType, frozenset[str]] = {
    DocumentType.INVOICE: frozenset(
        {"document_number", "supplier_name", "issue_date", "currency", "total"}
    ),
    DocumentType.QUOTATION: frozenset(
        {"document_number", "supplier_name", "issue_date", "currency", "total"}
    ),
    DocumentType.PURCHASE_ORDER: frozenset(
        {"document_number", "buyer_name", "issue_date", "currency", "total"}
    ),
    DocumentType.CONTRACT: frozenset(
        {"document_number", "effective_date", "parties", "governing_law"}
    ),
}


class ExtractedValue(BaseModel):
    value: str | list[str] | None
    confidence: float = Field(ge=0, le=1)
    citations: list[Citation]


class StructuredExtraction(BaseModel):
    schema_version: str = SCHEMA_VERSION
    document_type: DocumentType
    fields: dict[str, ExtractedValue]
    raw_provider_metadata: dict[str, Any] = Field(default_factory=dict)
