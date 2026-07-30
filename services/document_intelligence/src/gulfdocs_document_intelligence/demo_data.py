from datetime import UTC, datetime
from uuid import UUID

from .models import (
    Citation,
    DemoDocumentDetail,
    DocumentStatus,
    DocumentType,
    ExtractionField,
    GroundedAnswer,
    ValidationIssue,
)

DEMO_DOCUMENT_ID = UUID("10000000-0000-4000-8000-000000000001")

DEMO_DOCUMENT = DemoDocumentDetail(
    id=DEMO_DOCUMENT_ID,
    name="Northstar Office Trading — Invoice INV-GD-1042",
    document_type=DocumentType.INVOICE,
    detected_language="en",
    status=DocumentStatus.NEEDS_REVIEW,
    page_count=2,
    synthetic=True,
    updated_at=datetime(2026, 7, 30, 8, 15, tzinfo=UTC),
    fields=[
        ExtractionField(
            key="supplier_name",
            label="Supplier",
            value="Northstar Office Trading LLC",
            confidence=0.99,
            citations=[Citation(page=1, excerpt="Northstar Office Trading LLC")],
        ),
        ExtractionField(
            key="invoice_number",
            label="Invoice number",
            value="INV-GD-1042",
            confidence=0.99,
            citations=[Citation(page=1, excerpt="Invoice INV-GD-1042")],
        ),
        ExtractionField(
            key="currency",
            label="Currency",
            value="AED",
            confidence=0.99,
            citations=[Citation(page=1, excerpt="AED")],
        ),
        ExtractionField(
            key="total",
            label="Total",
            value="12862.50",
            confidence=0.98,
            citations=[Citation(page=1, excerpt="Total AED 12,862.50")],
        ),
    ],
    validation_issues=[
        ValidationIssue(
            severity="error",
            code="TOTAL_MISMATCH",
            description="Subtotal plus VAT equals AED 12,075.00, not AED 12,862.50.",
            related_fields=["subtotal", "tax_amount", "total"],
            source_page=1,
            suggested_action="Confirm the printed total with the supplier before approval.",
        )
    ],
    supported_questions=[
        "What are the payment terms?",
        "Does the printed total match the line items?",
        "What is the delivery address?",
    ],
    processing={
        "parser_version": "synthetic-seed-v1",
        "prompt_version": "precomputed-v1",
        "duration_ms": 1840,
    },
)

_ANSWERS = {
    "what are the payment terms?": GroundedAnswer(
        answer="Payment is due within 30 days of the invoice date.",
        citations=[Citation(page=2, excerpt="Payment terms: Net 30 days from invoice date.")],
        supported=True,
        model_name="precomputed-public-demo",
        prompt_version="precomputed-v1",
    ),
    "does the printed total match the line items?": GroundedAnswer(
        answer="No. The printed total is AED 12,862.50, while subtotal plus VAT is AED 12,075.00.",
        citations=[
            Citation(
                page=1, excerpt="Subtotal AED 11,500.00 · VAT AED 575.00 · Total AED 12,862.50"
            )
        ],
        supported=True,
        model_name="precomputed-public-demo",
        prompt_version="precomputed-v1",
    ),
}


def answer_demo_question(question: str) -> GroundedAnswer:
    normalized = " ".join(question.casefold().split())
    return _ANSWERS.get(
        normalized,
        GroundedAnswer(
            answer=(
                "I could not find enough evidence in the selected document "
                "to answer that question reliably."
            ),
            citations=[],
            supported=False,
            model_name="precomputed-public-demo",
            prompt_version="precomputed-v1",
        ),
    )
