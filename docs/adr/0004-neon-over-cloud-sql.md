# ADR 0004: Neon over Cloud SQL

- Status: Accepted

Neon provides serverless PostgreSQL suitable for low traffic while retaining pgvector, full-text search, constraints, and transactions. A pooled URL is required for Cloud Run. The repository boundary preserves a path to Cloud SQL/AlloyDB if workload or governance changes.
