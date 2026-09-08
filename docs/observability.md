# Observability

API and worker logs are JSON and carry request, correlation, document, task, and processing-run identifiers where applicable. Durations, retry attempts, failure categories, model/prompt/parser versions, and token usage are recorded without content bodies. `X-Request-ID` is accepted only from a bounded character set, returned to the browser, copied into task payloads, and bound into structured logs.

`GET /healthz` is a process liveness check. API `GET /readyz` verifies database reachability. The private worker exposes health only behind Cloud Run IAM. `GET /api/v1/metrics/summary` is authenticated and workspace-scoped; it returns daily upload/question/token usage, document failure and review rates, approved count, and average/median/p95 processing latency.

FastAPI OpenTelemetry instrumentation is always trace-context compatible. Setting `OTEL_EXPORTER_OTLP_ENDPOINT` enables batched OTLP/HTTP span export; leaving it empty creates no external exporter or paid-platform dependency. The endpoint must be trusted because traces contain route and timing metadata.

The Terraform default Logging bucket retains logs for 30 days. Repeated payloads and document text are deliberately omitted because logs affect both privacy and cost. Alert policies are an operator follow-up after deployed traffic establishes a truthful baseline; recommended signals are readiness failures, worker 5xx, task retry exhaustion, processing p95, failure rate, and abnormal token volume.
