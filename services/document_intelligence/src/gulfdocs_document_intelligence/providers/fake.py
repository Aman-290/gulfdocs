import hashlib

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
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([round(byte / 255, 6) for byte in digest[:16]])
        return vectors

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
