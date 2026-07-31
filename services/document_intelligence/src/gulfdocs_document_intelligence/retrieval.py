import re
from dataclasses import dataclass
from uuid import UUID

_QUESTION_STOP_WORDS = {
    "a",
    "an",
    "are",
    "did",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "ما",
    "ماذا",
    "هل",
    "هو",
    "هي",
    "في",
    "من",
    "إلى",
    "على",
    "كم",
}


def lexical_search_query(question: str) -> str:
    terms = [
        term
        for term in re.findall(r"[\w\u0600-\u06ff]+", question.casefold())
        if len(term) > 1 and term not in _QUESTION_STOP_WORDS
    ]
    return " OR ".join(terms[:12])


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    chunk_id: UUID
    page_number: int
    text: str
    language: str | None
    rank: int
    source: str
    score: float


@dataclass(frozen=True, slots=True)
class FusedChunk:
    chunk_id: UUID
    page_number: int
    text: str
    language: str | None
    score: float
    sources: tuple[str, ...]


def reciprocal_rank_fusion(
    rankings: list[list[RetrievalCandidate]], *, k: int = 60, limit: int = 8
) -> list[FusedChunk]:
    scores: dict[UUID, float] = {}
    candidates: dict[UUID, RetrievalCandidate] = {}
    sources: dict[UUID, set[str]] = {}
    for ranking in rankings:
        for candidate in ranking:
            candidates[candidate.chunk_id] = candidate
            scores[candidate.chunk_id] = scores.get(candidate.chunk_id, 0) + 1 / (
                k + candidate.rank
            )
            sources.setdefault(candidate.chunk_id, set()).add(candidate.source)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], str(chunk_id)))[:limit]
    return [
        FusedChunk(
            chunk_id=chunk_id,
            page_number=candidates[chunk_id].page_number,
            text=candidates[chunk_id].text,
            language=candidates[chunk_id].language,
            score=scores[chunk_id],
            sources=tuple(sorted(sources[chunk_id])),
        )
        for chunk_id in ordered
    ]


def bounded_page_context(
    chunks: list[FusedChunk], *, maximum_characters: int
) -> list[tuple[int, str]]:
    context: list[tuple[int, str]] = []
    remaining = maximum_characters
    for chunk in chunks:
        if remaining <= 0:
            break
        text = chunk.text[:remaining]
        if text:
            context.append((chunk.page_number, text))
            remaining -= len(text)
    return context
