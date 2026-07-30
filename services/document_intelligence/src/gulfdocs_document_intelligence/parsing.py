from dataclasses import dataclass
from pathlib import Path

import fitz

from .normalization import normalize_page_text


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page_number: int
    text: str
    detected_language: str


def detect_language(text: str) -> str:
    arabic = sum("\u0600" <= character <= "\u06ff" for character in text)
    latin = sum(character.isascii() and character.isalpha() for character in text)
    if arabic and latin:
        return "mixed"
    if arabic:
        return "ar"
    if latin:
        return "en"
    return "und"


def parse_pdf_pages(path: Path) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("Encrypted PDFs are not supported")
        for index, page in enumerate(document):
            text = normalize_page_text(page.get_text("text"))
            pages.append(
                ParsedPage(
                    page_number=index + 1,
                    text=text,
                    detected_language=detect_language(text),
                )
            )
    if not pages:
        raise ValueError("PDF has no pages")
    return pages


def document_language(pages: list[ParsedPage]) -> str:
    languages = {page.detected_language for page in pages if page.detected_language != "und"}
    if not languages:
        return "und"
    if languages == {"ar"}:
        return "ar"
    if languages == {"en"}:
        return "en"
    return "mixed"
