# Evaluation methodology

GulfDocs evaluates deterministic local behavior with fictional business documents before any real-provider claims are made. The source of truth is [`evaluation/cases.json`](../evaluation/cases.json); generated PDFs live in [`data/synthetic`](../data/synthetic), and the latest machine-readable result is [`evaluation/results/latest.json`](../evaluation/results/latest.json).

## Corpus

Dataset `2026-07-31.1` contains 12 wholly fictional English, Arabic, and bilingual cases across invoices, a quotation, a purchase order, and a short contract. It includes AED, USD, and EUR values; line-item tables; multi-page tables; missing values; a duplicate identifier; low-confidence text; an arithmetic mismatch; a scanned-looking layout; difficult dates; and document-borne prompt-injection text.

The generator stamps non-Arabic pages and PDF metadata as synthetic. Names, identifiers, addresses, and amounts were invented for this repository. No private specification content or confidential business document is present.

## What is measured

The evaluator executes classification, schema extraction, deterministic validation/security checks, full-text plus deterministic-vector rank fusion, cited answer construction, unsupported-answer behavior, PDF parsing, and language detection. It reports:

- document classification accuracy;
- field accuracy plus exact identifier, normalized number/date, and line-item slices;
- expected validation/security issue detection and arithmetic-error detection;
- retrieval recall@3 and citation precision;
- unsupported-answer rate;
- English, Arabic, and mixed-language slices;
- PDF page-count and language detection accuracy;
- median/p95 wall-clock latency, token approximation, and estimated API cost;
- every per-case failure, implementation versions, timestamp, and measured baseline deltas.

For the fake provider, “token usage” is explicitly a whitespace-token approximation and estimated API cost is USD 0 because no external model call occurs. Those values must not be represented as Gemini billing or tokenizer measurements.

## Latest deterministic result

The committed report was produced by an actual local execution over 12 cases. It measured 100% classification, 99.07% expected-field accuracy, 100% normalized numeric and line-item accuracy, 94.74% normalized date accuracy, 100% expected-issue detection, 100% retrieval recall@3, 100% citation precision, and 100% unsupported-answer handling. The one field failure is deliberate and visible: the fake regex baseline does not normalize the dual Hijri/Gregorian difficult-date string.

These measurements characterize `fake-ai-v1`, not Gemini. They are useful as a reproducible regression baseline and are not a claim of production extraction accuracy.

## Commands

```bash
make eval
make eval-extraction
make eval-retrieval
make eval-grounding
```

Each default command is quota-free. The real-provider path is deliberately gated:

```bash
RUN_REAL_GEMINI_EVAL=1 GCP_PROJECT_ID=your-project make eval-real-gemini
```

It uses configured ADC or `GEMINI_API_KEY`, can incur quota/cost, and writes a report only after executing. Never commit credentials. Review cost and latency separately because provider/model/location and network conditions materially affect them.

## Baseline policy

[`evaluation/baseline.json`](../evaluation/baseline.json) preserves the first measured run, before the total-field boundary fix. The current JSON report contains numeric deltas from that run. Replace the baseline only after a reviewed, reproducible change; never edit it to make a regression disappear.
