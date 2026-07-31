from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation" / "cases.json"
OUTPUT_DIRECTORY = ROOT / "data" / "synthetic"


def locate_unicode_font() -> Path:
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(
        "A Unicode font (Arial, Tahoma, DejaVu Sans, or Noto Sans Arabic) is required"
    )


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["cases"])


def generate_pdf(case: dict[str, Any], destination: Path) -> None:
    document = fitz.open()
    font_path = locate_unicode_font()
    for page_number, page_text in enumerate(case["pages"], start=1):
        page = document.new_page(width=595, height=842)
        page.draw_rect(page.rect, color=(0.86, 0.88, 0.85), fill=(0.99, 0.985, 0.96))
        if case["language"] != "ar":
            page.insert_text(
                fitz.Point(44, 40),
                "GULFDOCS SYNTHETIC EVALUATION FIXTURE",
                fontsize=8,
                color=(0.04, 0.42, 0.39),
            )
        remaining = page.insert_textbox(
            fitz.Rect(44, 70, 551, 775),
            page_text,
            fontname="fixture",
            fontfile=str(font_path),
            fontsize=12,
            lineheight=1.7,
            color=(0.06, 0.16, 0.17),
            align=fitz.TEXT_ALIGN_RIGHT if case["language"] == "ar" else fitz.TEXT_ALIGN_LEFT,
        )
        if remaining < 0:
            raise RuntimeError(f"Synthetic case {case['id']} did not fit on its page")
        if case["language"] != "ar":
            page.insert_text(
                fitz.Point(44, 814),
                f"Fictional data only · {case['id']} · page {page_number}/{len(case['pages'])}",
                fontsize=8,
                color=(0.38, 0.43, 0.42),
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    document.set_metadata(
        {
            "title": str(case["title"]),
            "author": "GulfDocs synthetic evaluation generator",
            "subject": "Fictional portfolio evaluation data only",
            "keywords": "synthetic,fictional,evaluation",
        }
    )
    document.save(destination, garbage=4, deflate=True)
    document.close()


def generate_all(output_directory: Path = OUTPUT_DIRECTORY) -> list[Path]:
    generated: list[Path] = []
    for case in load_cases():
        destination = output_directory / f"{case['id']}.pdf"
        generate_pdf(case, destination)
        generated.append(destination)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fictional GulfDocs evaluation PDFs")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIRECTORY)
    arguments = parser.parse_args()
    generated = generate_all(arguments.output)
    print(f"Generated {len(generated)} synthetic PDF fixtures in {arguments.output}")


if __name__ == "__main__":
    main()
