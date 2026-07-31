import hashlib
import re

from ..extraction import ExtractedValue, StructuredExtraction
from ..models import Citation, DocumentType, GroundedAnswer


class FakeAIProvider:
    """Deterministic local provider; it never calls an external model."""

    model_name = "fake-ai-v1"

    async def classify(self, page_text: list[str]) -> DocumentType:
        text = " ".join(page_text).casefold()
        if "purchase order" in text or "أمر شراء" in text:
            return DocumentType.PURCHASE_ORDER
        if "quotation" in text or "عرض سعر" in text:
            return DocumentType.QUOTATION
        if "contract" in text or "عقد" in text:
            return DocumentType.CONTRACT
        return DocumentType.INVOICE

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            values: list[float] = []
            for counter in range(24):
                digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
                values.extend(round((byte / 127.5) - 1, 6) for byte in digest)
            vectors.append(values)
        return vectors

    async def extract(
        self, document_type: DocumentType, page_text: list[str]
    ) -> StructuredExtraction:
        patterns = {
            "document_number": (
                r"(?:(?:invoice|quotation|purchase order|contract)\s*"
                r"(?:number|no\.?|#)?|رقم (?:الفاتورة|عرض السعر|أمر الشراء|العقد|المستند))"
                r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]+)"
            ),
            "supplier_name": r"(?:supplier|vendor|المورد|البائع)\s*[:\-]\s*([^\n]+)",
            "customer_name": r"(?:customer|client|العميل)\s*[:\-]\s*([^\n]+)",
            "buyer_name": r"(?:buyer|customer|المشتري)\s*[:\-]\s*([^\n]+)",
            "issue_date": (
                r"(?:issue date|date|تاريخ الإصدار|التاريخ)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})"
            ),
            "due_date": r"(?:due date|تاريخ الاستحقاق)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
            "effective_date": r"effective date\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
            "expiry_date": r"(?:expiry|expiration) date\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
            "requested_delivery_date": r"requested delivery date\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
            "delivery_address": r"delivery address\s*[:\-]\s*([^\n]+)",
            "currency": r"(?:currency|العملة)\s*[:\-]\s*(AED|USD|EUR)",
            "subtotal": r"(?:subtotal|المجموع الفرعي)\s*[:\-]\s*([\d,.]+)",
            "tax": r"(?:tax|vat|الضريبة)\s*[:\-]\s*([\d,.]+)",
            "total": (
                r"(?:(?<![A-Za-z])(?:grand\s+)?total(?![A-Za-z])|الإجمالي|المجموع الكلي)"
                r"\s*[:\-]\s*([\d,.]+)"
            ),
            "governing_law": r"governing law\s*[:\-]\s*([^\n]+)",
            "parties": r"parties\s*[:\-]\s*([^\n]+)",
            "title": r"(?:contract title|title)\s*[:\-]\s*([^\n]+)",
            "payment_terms": r"payment terms\s*[:\-]\s*([^\n]+)",
            "terms": r"terms\s*[:\-]\s*([^\n]+)",
            "renewal_terms": r"renewal terms\s*[:\-]\s*([^\n]+)",
            "termination_terms": r"termination terms\s*[:\-]\s*([^\n]+)",
            "obligations": r"obligations\s*[:\-]\s*([^\n]+)",
        }
        fields: dict[str, ExtractedValue] = {}
        for key, pattern in patterns.items():
            match = _find_with_page(pattern, page_text)
            if match is None:
                continue
            page, value, excerpt = match
            parsed_value: str | list[str] = value.strip()
            confidence = 0.98
            if isinstance(parsed_value, str) and parsed_value.startswith("[LOW]"):
                parsed_value = parsed_value.removeprefix("[LOW]").strip()
                confidence = 0.55
            if key == "parties":
                parsed_value = [part.strip() for part in re.split(r"[;,]", value) if part.strip()]
            fields[key] = ExtractedValue(
                value=parsed_value,
                confidence=confidence,
                citations=[Citation(page=page, excerpt=excerpt[:500])],
            )
        line_items: list[dict[str, str]] = []
        line_citations: list[Citation] = []
        for page_number, text in enumerate(page_text, start=1):
            for line_match in re.finditer(
                r"(?:ITEM|بند)\|([^|\n]+)\|([\d.]+)\|([\d,.]+)\|([\d,.]+)", text, re.I
            ):
                line_items.append(
                    {
                        "description": line_match.group(1).strip(),
                        "quantity": line_match.group(2),
                        "unit_price": line_match.group(3),
                        "line_total": line_match.group(4),
                    }
                )
                line_citations.append(Citation(page=page_number, excerpt=line_match.group(0)[:500]))
        if line_items:
            fields["line_items"] = ExtractedValue(
                value=line_items,
                confidence=0.98,
                citations=line_citations,
            )
        return StructuredExtraction(document_type=document_type, fields=fields)

    async def answer(self, question: str, context: list[tuple[int, str]]) -> GroundedAnswer:
        del question
        if not context:
            return GroundedAnswer(
                answer=(
                    "I could not find enough evidence in the selected document "
                    "to answer that question reliably."
                ),
                citations=[],
                supported=False,
                model_name=self.model_name,
                prompt_version="fake-grounding-v1",
            )
        page, excerpt = context[0]
        return GroundedAnswer(
            answer=excerpt,
            citations=[Citation(page=page, excerpt=excerpt[:500])],
            supported=True,
            model_name=self.model_name,
            prompt_version="fake-grounding-v1",
        )


def _find_with_page(pattern: str, pages: list[str]) -> tuple[int, str, str] | None:
    for page_number, text in enumerate(pages, start=1):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            line = text[match.start() :].splitlines()[0]
            return page_number, match.group(1), line
    return None
