import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .extraction import REQUIRED_FIELDS, StructuredExtraction
from .normalization import normalize_currency, parse_decimal


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
    line_items = extraction.fields.get("line_items")
    if subtotal is not None and line_items and isinstance(line_items.value, list):
        line_total = Decimal(0)
        valid_lines = 0
        for item in line_items.value:
            if isinstance(item, dict):
                value = parse_decimal(item.get("line_total", ""))
                if value is not None:
                    line_total += value
                    valid_lines += 1
        if valid_lines and abs(line_total - subtotal) > Decimal("0.01"):
            issues.append(
                DeterministicIssue(
                    code="LINE_ITEMS_SUBTOTAL_MISMATCH",
                    severity="error",
                    description="The sum of line items does not equal the subtotal.",
                    related_fields=("line_items", "subtotal"),
                    source_page=_first_page(extraction, "subtotal"),
                    suggested_action="Verify line-item amounts and the subtotal.",
                )
            )
    currency = extraction.fields.get("currency")
    if currency and isinstance(currency.value, str) and normalize_currency(currency.value) is None:
        issues.append(
            DeterministicIssue(
                code="INVALID_CURRENCY",
                severity="error",
                description="Currency is not a supported ISO currency value.",
                related_fields=("currency",),
                source_page=_first_page(extraction, "currency"),
                suggested_action="Confirm the currency shown in the document.",
            )
        )
    identifier = extraction.fields.get("document_number")
    if (
        identifier
        and isinstance(identifier.value, str)
        and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_-]{1,79}", identifier.value)
    ):
        issues.append(
            DeterministicIssue(
                code="INVALID_IDENTIFIER",
                severity="warning",
                description="Document identifier has an unexpected format.",
                related_fields=("document_number",),
                source_page=_first_page(extraction, "document_number"),
                suggested_action="Verify the identifier against the cited page.",
            )
        )
    _validate_date_order(extraction, issues, "issue_date", "due_date")
    _validate_date_order(extraction, issues, "effective_date", "expiry_date")
    return issues


def _decimal_field(extraction: StructuredExtraction, key: str) -> Decimal | None:
    field = extraction.fields.get(key)
    return parse_decimal(field.value) if field and isinstance(field.value, str) else None


def _first_page(extraction: StructuredExtraction, key: str) -> int | None:
    field = extraction.fields.get(key)
    return field.citations[0].page if field and field.citations else None


def _validate_date_order(
    extraction: StructuredExtraction,
    issues: list[DeterministicIssue],
    start_key: str,
    end_key: str,
) -> None:
    start = extraction.fields.get(start_key)
    end = extraction.fields.get(end_key)
    if not start or not end or not isinstance(start.value, str) or not isinstance(end.value, str):
        return
    try:
        start_date = date.fromisoformat(start.value)
        end_date = date.fromisoformat(end.value)
    except ValueError:
        issues.append(
            DeterministicIssue(
                code="INVALID_DATE",
                severity="error",
                description="One or more extracted dates are invalid.",
                related_fields=(start_key, end_key),
                source_page=_first_page(extraction, end_key),
                suggested_action="Enter dates in ISO YYYY-MM-DD format after checking the source.",
            )
        )
        return
    if end_date < start_date:
        issues.append(
            DeterministicIssue(
                code="DATE_ORDER_INVALID",
                severity="error",
                description=f"{end_key} occurs before {start_key}.",
                related_fields=(start_key, end_key),
                source_page=_first_page(extraction, end_key),
                suggested_action="Confirm both dates against the cited pages.",
            )
        )
