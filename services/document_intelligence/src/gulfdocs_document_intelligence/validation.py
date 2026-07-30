from dataclasses import dataclass
from decimal import Decimal

from .extraction import REQUIRED_FIELDS, StructuredExtraction
from .normalization import parse_decimal


@dataclass(frozen=True, slots=True)
class DeterministicIssue:
    code: str
    severity: str
    description: str
    related_fields: tuple[str, ...]
    source_page: int | None
    suggested_action: str


def validate_extraction(extraction: StructuredExtraction) -> list[DeterministicIssue]:
    issues: list[DeterministicIssue] = []
    for key in sorted(REQUIRED_FIELDS[extraction.document_type]):
        field = extraction.fields.get(key)
        if field is None or field.value is None or field.value == "":
            issues.append(
                DeterministicIssue(
                    code="REQUIRED_FIELD_MISSING",
                    severity="error",
                    description=f"Required field '{key}' was not extracted.",
                    related_fields=(key,),
                    source_page=None,
                    suggested_action="Review the source document and enter the value manually.",
                )
            )
        elif field.confidence < 0.7:
            issues.append(
                DeterministicIssue(
                    code="LOW_CONFIDENCE",
                    severity="warning",
                    description=f"Field '{key}' has low extraction confidence.",
                    related_fields=(key,),
                    source_page=field.citations[0].page if field.citations else None,
                    suggested_action="Confirm the value against the cited page.",
                )
            )
    subtotal = _decimal_field(extraction, "subtotal")
    tax = _decimal_field(extraction, "tax") or Decimal(0)
    total = _decimal_field(extraction, "total")
    if (
        subtotal is not None
        and total is not None
        and abs((subtotal + tax) - total) > Decimal("0.01")
    ):
        issues.append(
            DeterministicIssue(
                code="TOTAL_MISMATCH",
                severity="error",
                description="Subtotal plus tax does not equal the extracted total.",
                related_fields=("subtotal", "tax", "total"),
                source_page=_first_page(extraction, "total"),
                suggested_action="Verify line totals, tax, discounts, and the final total.",
            )
        )
    return issues


def _decimal_field(extraction: StructuredExtraction, key: str) -> Decimal | None:
    field = extraction.fields.get(key)
    return parse_decimal(field.value) if field and isinstance(field.value, str) else None


def _first_page(extraction: StructuredExtraction, key: str) -> int | None:
    field = extraction.fields.get(key)
    return field.citations[0].page if field and field.citations else None
