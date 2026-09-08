# ADR 0011: Separate API and worker services

- Status: Accepted

The API stays latency-focused and public; the worker is private, memory-heavier, concurrency-one, and allowed longer requests. Separation limits permissions, scaling, and failure blast radius, with Cloud Tasks providing the boundary.
