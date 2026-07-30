from typing import Protocol

from ..models import DocumentType, GroundedAnswer


class AIProvider(Protocol):
    model_name: str

    async def classify(self, page_text: list[str]) -> DocumentType: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def answer(self, question: str, context: list[tuple[int, str]]) -> GroundedAnswer: ...
