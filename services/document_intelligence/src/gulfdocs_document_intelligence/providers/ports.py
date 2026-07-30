from typing import Protocol

from ..extraction import StructuredExtraction
from ..models import DocumentType, GroundedAnswer


class AIProvider(Protocol):
    model_name: str

    async def classify(self, page_text: list[str]) -> DocumentType: ...

    async def extract(
        self, document_type: DocumentType, page_text: list[str]
    ) -> StructuredExtraction: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def answer(self, question: str, context: list[tuple[int, str]]) -> GroundedAnswer: ...
