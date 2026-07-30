# GulfDocs

GulfDocs is a bilingual Arabic–English document-intelligence platform that extracts structured business data, validates financial and contractual fields, supports human review, and answers questions with page-level evidence.

This repository is under active phased development. Phase 1 is complete, and Phase 2 now includes the core PostgreSQL/pgvector schema, Alembic migrations, Firebase and deterministic development authentication boundaries, persistent workspace authorization, capability-token PDF uploads, and Cloud Storage/Cloud Tasks adapters. Full document processing, review, retrieval, cloud verification, and deployment are tracked in [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md).

> Public data is synthetic. Anonymous uploads are disabled. Do not use the project with confidential, personal, legally sensitive, or commercially sensitive material when it is configured with a free AI API tier.

## Live demo

Not deployed yet. A dedicated GulfDocs GCP/Firebase project has not been selected, and the unrelated active local GCP project will not be reused.

## Why this is not a basic PDF chatbot

- Asynchronous, identifier-only processing is designed for at-least-once Cloud Tasks delivery.
- Typed extraction is followed by deterministic date, currency, arithmetic, confidence, and contract validation.
- Reviewers will correct fields, preserve revisions, and explicitly approve records.
- Retrieval combines PostgreSQL full-text search and pgvector under strict workspace/document filters.
- Answers must cite retrieved pages or return an explicit unsupported result.
- Provider, storage, authentication, queue, and repository boundaries keep local tests deterministic and cloud adapters replaceable.

## Architecture

```mermaid
flowchart TD
    User["Public visitor or authenticated user"] --> Web["Firebase App Hosting · Next.js"]
    Web --> Auth["Firebase Authentication"]
    Web --> API["Cloud Run · FastAPI API"]
    API --> Storage["Private Cloud Storage"]
    API --> Tasks["Cloud Tasks · OIDC"]
    Tasks --> Worker["Private Cloud Run worker"]
    Worker --> Gemini["Gemini provider"]
    API --> DB["Neon PostgreSQL · FTS + pgvector"]
    Worker --> DB
```

Local development substitutes deterministic development auth, local filesystem storage, an inline task queue, a fake AI provider, and PostgreSQL with pgvector while preserving the same domain interfaces.

## Repository map

```text
apps/web                         Next.js App Router frontend
apps/api                         Public FastAPI API
apps/worker                      Private document-processing service
services/document_intelligence   Provider-neutral domain and local adapters
tests                            Cross-service smoke tests
docs                             Architecture decisions and guides
infrastructure                   Added in the infrastructure phase
evaluation                       Added with synthetic evaluation fixtures
```

## Local setup

Prerequisites: Node.js 22+, pnpm 10+, uv, Docker, and Git. The workspace pins Python 3.12, which `uv` can install automatically.

```bash
cp .env.example .env
pnpm install --frozen-lockfile
uv sync --all-packages
docker compose up -d postgres
uv run alembic upgrade head
```

Start the services in separate terminals:

```bash
pnpm --filter @gulfdocs/web dev
uv run uvicorn gulfdocs_api.main:app --app-dir apps/api/src --reload --port 8000
uv run uvicorn gulfdocs_worker.main:app --app-dir apps/worker/src --reload --port 8001
```

The web app is served at `http://localhost:3000`; API health is at `http://localhost:8000/healthz`. The worker requires its local bearer token even in development.

## Quality commands

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm --filter @gulfdocs/web test:e2e
uv run ruff check .
uv run mypy apps/api/src apps/worker/src services/document_intelligence/src services/persistence/src
uv run pytest -m "not integration" --cov=gulfdocs_api --cov=gulfdocs_worker --cov=gulfdocs_document_intelligence
uv run pytest -m integration
```

Equivalent Make targets are provided for Linux, macOS, and WSL workflows. Tests report only executed results; no benchmark, deployment, customer, uptime, or cost claims are fabricated.

## Firebase App Hosting

[`apps/web/apphosting.yaml`](./apps/web/apphosting.yaml) uses the currently documented `runConfig` schema with zero minimum instances, one maximum instance, one CPU, 512 MiB memory, and conservative concurrency. The intended frontend rollout owner is Firebase App Hosting’s GitHub integration; GitHub Actions will remain the quality gate to avoid competing frontend deploy pipelines.

## Current limitations

- The public demo uses seeded HTML and precomputed safe answers; synthetic PDF fixtures arrive in the evaluation phase.
- Download/delete/retry APIs, processing orchestration, review, retrieval, and live cloud-adapter verification are not yet complete.
- Cloud deployment is blocked until a dedicated GulfDocs project is explicitly selected and external Neon/Gemini configuration is supplied.
- Free-tier optimization does not guarantee permanently zero cost. Budget alerts notify; they do not enforce a hard spending limit.

## License

[MIT](./LICENSE)
