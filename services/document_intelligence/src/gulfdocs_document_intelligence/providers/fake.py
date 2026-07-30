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
                r"(?:invoice|quotation|purchase order|contract)\s*"
                r"(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]+)"
            ),
            "supplier_name": r"(?:supplier|vendor)\s*[:\-]\s*([^\n]+)",
            "buyer_name": r"(?:buyer|customer)\s*[:\-]\s*([^\n]+)",
            "issue_date": r"(?:issue date|date)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
            "effective_date": r"effective date\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
            "currency": r"currency\s*[:\-]\s*(AED|USD|EUR)",
            "subtotal": r"subtotal\s*[:\-]\s*([\d,.]+)",
            "tax": r"(?:tax|vat)\s*[:\-]\s*([\d,.]+)",
            "total": r"(?:grand )?total\s*[:\-]\s*([\d,.]+)",
            "governing_law": r"governing law\s*[:\-]\s*([^\n]+)",
            "parties": r"parties\s*[:\-]\s*([^\n]+)",
        }
        fields: dict[str, ExtractedValue] = {}
        for key, pattern in patterns.items():
            match = _find_with_page(pattern, page_text)
            if match is None:
                continue
            page, value, excerpt = match
            parsed_value: str | list[str] = value.strip()
            if key == "parties":
                parsed_value = [part.strip() for part in re.split(r"[;,]", value) if part.strip()]
            fields[key] = ExtractedValue(
                value=parsed_value,
                confidence=0.98,
                citations=[Citation(page=page, excerpt=excerpt[:500])],
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
