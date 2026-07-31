from typing import Any

from pydantic import BaseModel, Field

from .models import Citation, DocumentType

SCHEMA_VERSION = "2026-07-30.1"

SUPPORTED_FIELDS: dict[DocumentType, frozenset[str]] = {
    DocumentType.INVOICE: frozenset(
        {
            "supplier_name",
            "customer_name",
            "document_number",
            "issue_date",
            "due_date",
            "currency",
            "subtotal",
            "tax",
            "total",
            "supplier_registration_id",
            "customer_registration_id",
            "line_items",
            "payment_terms",
            "detected_language",
        }
    ),
    DocumentType.QUOTATION: frozenset(
        {
            "supplier_name",
            "customer_name",
            "document_number",
            "issue_date",
            "expiry_date",
            "currency",
            "subtotal",
            "tax",
            "total",
            "line_items",
            "terms",
        }
    ),
    DocumentType.PURCHASE_ORDER: frozenset(
        {
            "buyer_name",
            "supplier_name",
            "document_number",
            "issue_date",
            "requested_delivery_date",
            "delivery_address",
            "currency",
            "subtotal",
            "tax",
            "total",
            "line_items",
            "terms",
        }
    ),
    DocumentType.CONTRACT: frozenset(
        {
            "title",
            "parties",
            "effective_date",
            "expiry_date",
            "renewal_terms",
            "termination_terms",
            "payment_terms",
            "obligations",
            "monetary_values",
            "important_dates",
            "governing_law",
        }
    ),
}

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
    DocumentType.CONTRACT: frozenset({"title", "effective_date", "parties"}),
}


class ExtractedValue(BaseModel):
    value: str | list[str] | list[dict[str, str]] | None
    confidence: float = Field(ge=0, le=1)
    citations: list[Citation]


class StructuredExtraction(BaseModel):
    schema_version: str = SCHEMA_VERSION
    document_type: DocumentType
    fields: dict[str, ExtractedValue]
    raw_provider_metadata: dict[str, Any] = Field(default_factory=dict)
