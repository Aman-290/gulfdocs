# GulfDocs synthetic evaluation

Measured at `2026-07-31T14:19:49.945337+00:00` using `fake-ai-v1` over 12 fictional cases. No confidential documents were used.

## Metrics

| Metric | Measured value |
| --- | ---: |
| document classification accuracy | 1.0 |
| field level extraction accuracy | 0.9907 |
| identifier exact match | 1.0 |
| normalized numeric accuracy | 1.0 |
| normalized date accuracy | 0.9474 |
| line item extraction accuracy | 1.0 |
| expected issue detection rate | 1.0 |
| arithmetic error detection rate | 1.0 |
| retrieval recall at 3 | 1.0 |
| citation precision | 1.0 |
| unsupported answer rate | 1.0 |
| pdf page count accuracy | 1.0 |
| pdf language detection accuracy | 1.0 |
| median latency ms | 31.922 |
| p95 latency ms | 85.014 |
| measured token usage | 1037 |
| estimated api cost usd | 0.0 |

## Language slices

| Language | Cases | Classification | Fields |
| --- | ---: | ---: | ---: |
| ar | 1 | 1.0 | 1.0 |
| en | 9 | 1.0 | 0.9875 |
| mixed | 2 | 1.0 | 1.0 |

## Per-case failures

- `difficult-date-format` / `field_extraction`: expected `2026-11-24`, measured `None`.

## Baseline comparison

Measured deltas are included in the JSON report.

## Interpretation

The fake provider is a deterministic local baseline, not a claim about production Gemini quality. Its zero API cost means no billable model call occurred. Token usage is explicitly an approximation for the fake path. Run the opt-in real-provider command before publishing any Gemini quality, latency, token, or cost claim.
