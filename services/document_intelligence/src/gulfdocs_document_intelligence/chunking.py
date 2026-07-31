from dataclasses import dataclass

from .parsing import ParsedPage


@dataclass(frozen=True, slots=True)
class PageChunk:
    page_number: int
    text: str
    detected_language: str
    token_count: int
    sequence: int


def chunk_pages(
    pages: list[ParsedPage], *, max_characters: int = 1_500, overlap: int = 150
) -> list[PageChunk]:
    if max_characters < 200 or overlap < 0 or overlap >= max_characters:
        raise ValueError("Invalid chunking bounds")
    chunks: list[PageChunk] = []
    sequence = 0
    for page in pages:
        text = page.text
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + max_characters, len(text))
            if end < len(text):
                boundary = text.rfind("\n", start, end)
                if boundary > start + max_characters // 2:
                    end = boundary
            value = text[start:end].strip()
            if value:
                chunks.append(
                    PageChunk(
                        page_number=page.page_number,
                        text=value,
                        detected_language=page.detected_language,
                        token_count=max(1, len(value.split())),
                        sequence=sequence,
                    )
                )
                sequence += 1
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
