from pathlib import Path

import pytest

from evaluation.generate_documents import OUTPUT_DIRECTORY, generate_all
from evaluation.run import evaluate, load_dataset


def test_dataset_is_fictional_and_covers_required_risk_cases() -> None:
    dataset = load_dataset()
    cases = dataset["cases"]
    assert dataset["fictional_data_only"] is True
    assert len(cases) >= 12
    assert {case["document_type"] for case in cases} == {
        "invoice",
        "quotation",
        "purchase_order",
        "contract",
    }
    assert {case["language"] for case in cases} >= {"en", "ar", "mixed"}
    issue_codes = {code for case in cases for code in case["expected_issue_codes"]}
    assert {
        "TOTAL_MISMATCH",
        "REQUIRED_FIELD_MISSING",
        "LOW_CONFIDENCE",
        "DUPLICATE_IDENTIFIER",
        "IGNORE_INSTRUCTIONS",
    }.issubset(issue_codes)
    assert any(len(case["pages"]) > 1 for case in cases)
    assert any(
        field.get("currency") == "AED" for field in (case["expected_fields"] for case in cases)
    )
    assert any(
        field.get("currency") in {"USD", "EUR"}
        for field in (case["expected_fields"] for case in cases)
    )


def test_generator_creates_parseable_page_bounded_pdfs(tmp_path: Path) -> None:
    generated = generate_all(tmp_path)
    assert len(generated) == len(load_dataset()["cases"])
    assert all(path.read_bytes().startswith(b"%PDF") for path in generated)
    assert all(path.stat().st_size > 1_000 for path in generated)


@pytest.mark.asyncio
async def test_fake_evaluation_is_measured_and_reproducible() -> None:
    if not OUTPUT_DIRECTORY.exists():
        generate_all()
    report = await evaluate("fake")
    metrics = report["metrics"]
    assert report["fictional_data_only"] is True
    assert report["provider"] == "fake"
    assert report["case_count"] >= 12
    assert metrics["document_classification_accuracy"] >= 0.9
    assert metrics["field_level_extraction_accuracy"] >= 0.85
    assert metrics["retrieval_recall_at_3"] >= 0.9
    assert metrics["citation_precision"] >= 0.9
    assert metrics["unsupported_answer_rate"] == 1.0
    assert metrics["estimated_api_cost_usd"] == 0.0
    assert metrics["measured_token_usage"] > 0
    assert report["baseline_comparison"]["available"] is True


def test_real_provider_is_explicitly_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUN_REAL_GEMINI_EVAL", raising=False)
    with pytest.raises(RuntimeError, match="RUN_REAL_GEMINI_EVAL=1"):
        from evaluation.run import _provider

        _provider("gemini")
