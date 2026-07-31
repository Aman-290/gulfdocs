from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import fitz
from gulfdocs_document_intelligence.extraction import SCHEMA_VERSION, StructuredExtraction
from gulfdocs_document_intelligence.models import DocumentType
from gulfdocs_document_intelligence.normalization import parse_decimal
from gulfdocs_document_intelligence.parsing import document_language, parse_pdf_pages
from gulfdocs_document_intelligence.providers import FakeAIProvider, GeminiProvider
from gulfdocs_document_intelligence.providers.ports import AIProvider
from gulfdocs_document_intelligence.retrieval import (
    RetrievalCandidate,
    lexical_search_query,
    reciprocal_rank_fusion,
)
from gulfdocs_document_intelligence.security import detect_prompt_injection
from gulfdocs_document_intelligence.validation import validate_extraction

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evaluation" / "cases.json"
PDF_DIRECTORY = ROOT / "data" / "synthetic"
RESULTS_DIRECTORY = ROOT / "evaluation" / "results"
BASELINE_PATH = ROOT / "evaluation" / "baseline.json"
NUMERIC_FIELDS = {"subtotal", "tax", "total"}
DATE_FIELDS = {
    "issue_date",
    "due_date",
    "effective_date",
    "expiry_date",
    "requested_delivery_date",
}


def load_dataset(path: Path = DATASET_PATH) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _percentage(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 3)


def _field_matches(key: str, expected: Any, actual: Any) -> bool:
    if key in NUMERIC_FIELDS:
        return _decimal(expected) == _decimal(actual)
    if key == "line_items":
        return _normalized_line_items(expected) == _normalized_line_items(actual)
    if key == "parties":
        return sorted(str(value).casefold() for value in expected) == sorted(
            str(value).casefold() for value in actual or []
        )
    return str(expected).strip().casefold() == str(actual).strip().casefold()


def _decimal(value: Any) -> Decimal | None:
    return parse_decimal(str(value)) if value is not None else None


def _normalized_line_items(value: Any) -> list[tuple[str, Decimal | None, Decimal | None]]:
    if not isinstance(value, list):
        return []
    normalized: list[tuple[str, Decimal | None, Decimal | None]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append(
            (
                str(item.get("description", "")).strip().casefold(),
                _decimal(item.get("quantity")),
                _decimal(item.get("line_total")),
            )
        )
    return normalized


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


async def _retrieve(
    provider: AIProvider, case_id: str, pages: list[str], question: str
) -> list[Any]:
    lexical_terms = {
        term.strip().casefold()
        for term in lexical_search_query(question).split(" OR ")
        if term.strip()
    }
    lexical_scored = []
    for page_number, text in enumerate(pages, start=1):
        score = sum(term in text.casefold() for term in lexical_terms)
        if score:
            lexical_scored.append((page_number, text, float(score)))
    lexical_scored.sort(key=lambda value: (-value[2], value[0]))
    page_vectors = await provider.embed(pages)
    question_vector = (await provider.embed([question]))[0]
    semantic_scored = sorted(
        [
            (page_number, text, _cosine(question_vector, vector))
            for page_number, (text, vector) in enumerate(
                zip(pages, page_vectors, strict=True), start=1
            )
        ],
        key=lambda value: (-value[2], value[0]),
    )

    def candidates(values: list[tuple[int, str, float]], source: str) -> list[RetrievalCandidate]:
        return [
            RetrievalCandidate(
                chunk_id=uuid5(NAMESPACE_URL, f"{case_id}:page:{page_number}"),
                page_number=page_number,
                text=text,
                language=None,
                rank=rank,
                source=source,
                score=score,
            )
            for rank, (page_number, text, score) in enumerate(values, start=1)
        ]

    return reciprocal_rank_fusion(
        [candidates(lexical_scored, "fts"), candidates(semantic_scored, "vector")], limit=3
    )


def _provider(name: str) -> AIProvider:
    if name == "fake":
        return FakeAIProvider()
    if os.getenv("RUN_REAL_GEMINI_EVAL") != "1":
        raise RuntimeError("Real Gemini evaluation requires RUN_REAL_GEMINI_EVAL=1")
    return GeminiProvider(
        model_name=os.getenv("GEMINI_EXTRACTION_MODEL", "gemini-3.5-flash-lite"),
        embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        api_key=os.getenv("GEMINI_API_KEY") or None,
        project=os.getenv("GCP_PROJECT_ID") or None,
        location=os.getenv("GCP_REGION", "us-central1"),
    )


async def evaluate(provider_name: str = "fake", suite: str = "all") -> dict[str, Any]:
    dataset = load_dataset()
    cases: list[dict[str, Any]] = dataset["cases"]
    provider = _provider(provider_name)
    identifier_counts = Counter(
        case["expected_fields"].get("document_number")
        for case in cases
        if case["expected_fields"].get("document_number")
    )
    totals: Counter[str] = Counter()
    languages: dict[str, Counter[str]] = {}
    latencies: list[float] = []
    token_usage = 0
    failures: list[dict[str, Any]] = []

    for case in cases:
        case_started = perf_counter()
        pages: list[str] = case["pages"]
        expected_type = DocumentType(case["document_type"])
        actual_type = await provider.classify(pages)
        totals["classification_total"] += 1
        totals["classification_correct"] += actual_type == expected_type
        language_counts = languages.setdefault(case["language"], Counter())
        language_counts["classification_total"] += 1
        language_counts["classification_correct"] += actual_type == expected_type
        extraction: StructuredExtraction = await provider.extract(actual_type, pages)
        expected_fields: dict[str, Any] = case["expected_fields"]
        for key, expected in expected_fields.items():
            actual_field = extraction.fields.get(key)
            actual = actual_field.value if actual_field else None
            matched = _field_matches(key, expected, actual)
            totals["field_total"] += 1
            totals["field_correct"] += matched
            language_counts["field_total"] += 1
            language_counts["field_correct"] += matched
            if key == "document_number":
                totals["identifier_total"] += 1
                totals["identifier_correct"] += matched
            if key in NUMERIC_FIELDS:
                totals["numeric_total"] += 1
                totals["numeric_correct"] += matched
            if key in DATE_FIELDS:
                totals["date_total"] += 1
                totals["date_correct"] += matched
            if key == "line_items":
                totals["line_item_total"] += 1
                totals["line_item_correct"] += matched
            if not matched:
                failures.append(
                    {
                        "case_id": case["id"],
                        "metric": "field_extraction",
                        "field": key,
                        "expected": expected,
                        "actual": actual,
                    }
                )
        issue_codes = {issue.code for issue in validate_extraction(extraction)}
        issue_codes.update(
            signal.code for page in pages for signal in detect_prompt_injection(page)
        )
        identifier = expected_fields.get("document_number")
        if identifier and identifier_counts[identifier] > 1:
            issue_codes.add("DUPLICATE_IDENTIFIER")
        for expected_issue in case["expected_issue_codes"]:
            totals["issue_total"] += 1
            detected = expected_issue in issue_codes
            totals["issue_correct"] += detected
            if expected_issue == "TOTAL_MISMATCH":
                totals["arithmetic_total"] += 1
                totals["arithmetic_correct"] += detected
            if not detected:
                failures.append(
                    {
                        "case_id": case["id"],
                        "metric": "issue_detection",
                        "expected": expected_issue,
                        "actual": sorted(issue_codes),
                    }
                )

        pdf_path = PDF_DIRECTORY / f"{case['id']}.pdf"
        parsed_pages = parse_pdf_pages(pdf_path)
        totals["pdf_page_total"] += 1
        totals["pdf_page_correct"] += len(parsed_pages) == len(pages)
        totals["pdf_language_total"] += 1
        totals["pdf_language_correct"] += document_language(parsed_pages) == case["language"]

        for retrieval_case in case["retrieval"]:
            relevant_pages = set(retrieval_case["relevant_pages"])
            if relevant_pages:
                retrieved = await _retrieve(provider, case["id"], pages, retrieval_case["question"])
                retrieved_pages = {chunk.page_number for chunk in retrieved[:3]}
                recalled = bool(relevant_pages & retrieved_pages)
                totals["retrieval_total"] += 1
                totals["retrieval_correct"] += recalled
                context = [(chunk.page_number, chunk.text) for chunk in retrieved]
                answer = await provider.answer(retrieval_case["question"], context)
                citation_pages = {citation.page for citation in answer.citations}
                citations_precise = bool(citation_pages) and citation_pages.issubset(relevant_pages)
                totals["citation_total"] += 1
                totals["citation_correct"] += citations_precise
                if not recalled:
                    failures.append(
                        {
                            "case_id": case["id"],
                            "metric": "retrieval_recall_at_3",
                            "expected": sorted(relevant_pages),
                            "actual": sorted(retrieved_pages),
                        }
                    )
                if not citations_precise:
                    failures.append(
                        {
                            "case_id": case["id"],
                            "metric": "citation_precision",
                            "expected": sorted(relevant_pages),
                            "actual": sorted(citation_pages),
                        }
                    )
                token_usage += sum(len(text.split()) for _, text in context) + len(
                    answer.answer.split()
                )
            else:
                answer = await provider.answer(retrieval_case["question"], [])
                totals["unsupported_total"] += 1
                totals["unsupported_correct"] += not answer.supported and not answer.citations
        latencies.append((perf_counter() - case_started) * 1000)

    metrics = {
        "document_classification_accuracy": _percentage(
            totals["classification_correct"], totals["classification_total"]
        ),
        "field_level_extraction_accuracy": _percentage(
            totals["field_correct"], totals["field_total"]
        ),
        "identifier_exact_match": _percentage(
            totals["identifier_correct"], totals["identifier_total"]
        ),
        "normalized_numeric_accuracy": _percentage(
            totals["numeric_correct"], totals["numeric_total"]
        ),
        "normalized_date_accuracy": _percentage(totals["date_correct"], totals["date_total"]),
        "line_item_extraction_accuracy": _percentage(
            totals["line_item_correct"], totals["line_item_total"]
        ),
        "expected_issue_detection_rate": _percentage(
            totals["issue_correct"], totals["issue_total"]
        ),
        "arithmetic_error_detection_rate": _percentage(
            totals["arithmetic_correct"], totals["arithmetic_total"]
        ),
        "retrieval_recall_at_3": _percentage(
            totals["retrieval_correct"], totals["retrieval_total"]
        ),
        "citation_precision": _percentage(totals["citation_correct"], totals["citation_total"]),
        "unsupported_answer_rate": _percentage(
            totals["unsupported_correct"], totals["unsupported_total"]
        ),
        "pdf_page_count_accuracy": _percentage(
            totals["pdf_page_correct"], totals["pdf_page_total"]
        ),
        "pdf_language_detection_accuracy": _percentage(
            totals["pdf_language_correct"], totals["pdf_language_total"]
        ),
        "median_latency_ms": round(statistics.median(latencies), 3),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "measured_token_usage": token_usage,
        "estimated_api_cost_usd": 0.0 if provider_name == "fake" else None,
    }
    language_slices = {
        language: {
            "classification_accuracy": _percentage(
                counts["classification_correct"], counts["classification_total"]
            ),
            "field_extraction_accuracy": _percentage(
                counts["field_correct"], counts["field_total"]
            ),
            "case_count": counts["classification_total"],
        }
        for language, counts in sorted(languages.items())
    }
    baseline = (
        json.loads(BASELINE_PATH.read_text(encoding="utf-8")) if BASELINE_PATH.exists() else None
    )
    return {
        "report_version": "1.0",
        "dataset_version": dataset["dataset_version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "suite": suite,
        "case_count": len(cases),
        "provider": provider_name,
        "model_version": getattr(provider, "model_name", "unknown"),
        "embedding_model_version": getattr(provider, "embedding_model", "fake-sha256-768"),
        "prompt_version": "fake-grounding-v1" if provider_name == "fake" else "grounded-qa-v1",
        "parser_version": f"PyMuPDF-{fitz.version[0]}+schema-{SCHEMA_VERSION}",
        "token_measurement": "whitespace-token approximation"
        if provider_name == "fake"
        else "provider usage where available",
        "metrics": metrics,
        "language_slices": language_slices,
        "failures": failures,
        "baseline_comparison": _baseline_comparison(metrics, baseline),
        "fictional_data_only": bool(dataset["fictional_data_only"]),
    }


def _baseline_comparison(
    metrics: dict[str, Any], baseline: dict[str, Any] | None
) -> dict[str, Any]:
    if baseline is None:
        return {"available": False, "reason": "No prior measured baseline has been committed."}
    previous = baseline.get("metrics", {})
    deltas = {
        key: round(float(value) - float(previous[key]), 4)
        for key, value in metrics.items()
        if isinstance(value, int | float) and isinstance(previous.get(key), int | float)
    }
    return {
        "available": True,
        "baseline_generated_at": baseline.get("generated_at"),
        "deltas": deltas,
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# GulfDocs synthetic evaluation",
        "",
        f"Measured at `{report['generated_at']}` using `{report['model_version']}` over "
        f"{report['case_count']} fictional cases. No confidential documents were used.",
        "",
        "## Metrics",
        "",
        "| Metric | Measured value |",
        "| --- | ---: |",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines.extend(
        [
            "",
            "## Language slices",
            "",
            "| Language | Cases | Classification | Fields |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for language, values in report["language_slices"].items():
        lines.append(
            f"| {language} | {values['case_count']} | {values['classification_accuracy']} | "
            f"{values['field_extraction_accuracy']} |"
        )
    lines.extend(["", "## Per-case failures", ""])
    if report["failures"]:
        for failure in report["failures"]:
            lines.append(
                f"- `{failure['case_id']}` / `{failure['metric']}`: expected "
                f"`{failure.get('expected')}`, measured `{failure.get('actual')}`."
            )
    else:
        lines.append("No failures were measured in this run.")
    comparison = report["baseline_comparison"]
    lines.extend(["", "## Baseline comparison", ""])
    lines.append(
        "Measured deltas are included in the JSON report."
        if comparison["available"]
        else str(comparison["reason"])
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The fake provider is a deterministic local baseline, not a claim about "
            "production Gemini quality. Its zero API cost means no billable model call "
            "occurred. Token usage is explicitly an approximation for the fake path. "
            "Run the opt-in real-provider command before publishing "
            "any Gemini quality, latency, token, or cost claim.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: dict[str, Any], suite: str) -> tuple[Path, Path]:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stem = "latest" if suite == "all" else suite
    json_path = RESULTS_DIRECTORY / f"{stem}.json"
    markdown_path = RESULTS_DIRECTORY / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run measured GulfDocs synthetic evaluations")
    parser.add_argument("--provider", choices=("fake", "gemini"), default="fake")
    parser.add_argument(
        "--suite", choices=("all", "extraction", "retrieval", "grounding"), default="all"
    )
    arguments = parser.parse_args()
    report = asyncio.run(evaluate(arguments.provider, arguments.suite))
    json_path, markdown_path = write_report(report, arguments.suite)
    print(f"Measured {report['case_count']} cases; JSON: {json_path}; Markdown: {markdown_path}")


if __name__ == "__main__":
    main()
