# Data model

The schema uses UUID keys, UTC timestamps, foreign keys, constraints, and workspace-scoped indexes. Flexible model output/citations use JSONB; retrieval embeddings use 768-dimensional pgvector values and generated `tsvector` columns.

```mermaid
erDiagram
  ORGANIZATION ||--o{ MEMBERSHIP : contains
  USER ||--o{ MEMBERSHIP : joins
  ORGANIZATION ||--o{ DOCUMENT : owns
  DOCUMENT ||--|| DOCUMENT_UPLOAD : receives
  DOCUMENT ||--o{ PROCESSING_RUN : attempts
  DOCUMENT ||--o{ PAGE : parses
  DOCUMENT ||--o{ CHUNK : indexes
  DOCUMENT ||--o{ EXTRACTED_RESULT : produces
  EXTRACTED_RESULT ||--o{ EXTRACTION_FIELD : contains
  EXTRACTION_FIELD ||--o{ EXTRACTION_REVISION : changes
  DOCUMENT ||--o{ VALIDATION_ISSUE : flags
  DOCUMENT ||--o{ DOCUMENT_REVIEW : reviews
  DOCUMENT ||--o{ DOCUMENT_QUESTION : asks
  DOCUMENT_QUESTION ||--|| DOCUMENT_ANSWER : answers
  ORGANIZATION ||--o{ LLM_USAGE_EVENT : meters
  ORGANIZATION ||--o{ AUDIT_EVENT : audits
  ORGANIZATION ||--o{ SECURITY_EVENT : monitors
```

`documents.status` is constrained to the legal lifecycle. Upload idempotency is unique within a workspace; processing attempts are unique per document; fields are unique within one extraction result. Row locks prevent concurrent finalization. Repository and API predicates repeat workspace authorization rather than trusting a route-level check alone.

Content-bearing records are purged by retention cleanup while the sanitized document shell, processing metadata, and privacy-safe audit event remain. Database portability is preserved behind repository/service boundaries even though the current target is Neon PostgreSQL.
