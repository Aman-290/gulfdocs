# ADR 0003: Cloud Tasks over Celery and Redis

- Status: Accepted

Cloud Tasks supplies managed, low-rate, authenticated, at-least-once HTTP delivery without an always-on broker. The worker therefore implements idempotency and bounded retries. This reduces portfolio cost and operations at the expense of GCP coupling.
