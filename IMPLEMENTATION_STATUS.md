# GulfDocs implementation status

This temporary file tracks delivery against `../gulfdocs-private/CODEX_BUILD_SPEC.md` without copying the private specification into the repository. It must be converted into final project documentation or removed before the project is declared complete.

Status legend: `[x]` complete and verified, `[ ]` not complete, `[~]` implemented in part, `[!]` externally blocked.

## Phase 0 — Environment and repository safety

- [x] Read the complete authoritative specification (2,345 lines).
- [x] Inspect the project directory and confirm it contains no unrelated files.
- [x] Inspect Git state; the directory was not a Git repository.
- [x] Audit required CLIs and versions without exposing secret values.
- [x] Detect authenticated GitHub, Google Cloud, and Firebase accounts.
- [x] Refuse to reuse the unrelated active GCP project `solarsaas-ff521`.
- [x] Install Terraform CLI 1.15.8 and validate the version-pinned configuration with Google provider 7.42.0.
- [x] Select and verify a dedicated billing-enabled GCP project and set it as the active CLI project without committing its identifiers.
- [x] Register the selected GCP project with Firebase, create the Web app, and initialize secure email/password Authentication.
- [!] No deployed PostgreSQL connection is configured.

## Phase 1 — Monorepo foundation and local vertical slice

- [x] Initialize Git on branch `feat/gulfdocs-platform`.
- [x] Add root workspace, formatting, linting, test, build, and developer-command configuration.
- [x] Scaffold a strict TypeScript Next.js App Router frontend.
- [x] Add Firebase App Hosting configuration with conservative runtime limits.
- [x] Scaffold FastAPI API and private worker services on Python 3.12.
- [x] Create the shared document-intelligence Python package and cloud/local adapter boundaries.
- [x] Implement structured logging, correlation IDs, safe errors, `/healthz`, and `/readyz`.
- [x] Add initial public-demo API data and prevent anonymous upload routes.
- [x] Add a bilingual, responsive public landing/demo shell with English LTR and Arabic RTL support.
- [x] Add deterministic backend and frontend tests with meaningful assertions.
- [x] Add Dockerfiles and local PostgreSQL/pgvector Docker Compose service.
- [x] Run lint, type checks, tests, production builds, browser tests, container checks, and local smoke checks.
- [x] Commit the coherent tested foundation.

## Phase 2 — Database, authentication, authorization, and upload lifecycle

- [x] Model users, organizations/workspaces, memberships, documents, uploads, processing runs, pages, chunks, extraction data, reviews, questions/answers, usage, audit, and security events.
- [x] Add PostgreSQL constraints, indexes, pgvector, full-text search, UTC timestamps, and Alembic migrations.
- [x] Verify empty-database initialization and repository integration tests.
- [x] Implement Firebase ID-token verification and deterministic development-auth adapter.
- [x] Enforce workspace authorization in API and repository queries with cross-workspace denial tests.
- [x] Implement legal document status transitions and transactional upload idempotency.
- [x] Implement local filesystem and Cloud Storage adapters with opaque object paths and signed upload/download abstractions. Local behavior is tested; live GCS execution remains externally blocked.
- [x] Implement local queue and Cloud Tasks OIDC adapters with identifier-only payloads, deterministic task IDs, persistent dispatch state, and fail-closed worker OIDC verification. Live delivery remains externally blocked.
- [x] Implement presign/complete/download/delete/retry endpoints, PDF magic-byte checks, size/page limits, usage limits, polling states, and audit events.

## Phase 3 — Deterministic processing, extraction, validation, and review

- [x] Implement the deterministic LangGraph workflow, row-locked idempotent worker processing, bounded task attempts, atomic result finalization, safe temporary cleanup, and failure persistence.
- [x] Parse PDFs with PyMuPDF while preserving page boundaries and Arabic text.
- [x] Implement language detection, document classification, schema selection, normalization, prompt-injection detection, and persisted security events.
- [x] Implement stable-model `GeminiProvider` and deterministic `FakeAIProvider` for classification, structured extraction, 768-dimension embeddings, and grounded responses. Live Gemini verification is deferred to the cloud phase.
- [x] Implement versioned invoice, quotation, purchase-order, and contract field profiles with page citations, explicit unavailable values, and per-field confidence.
- [x] Implement required-field, arithmetic, line-item, date-order, currency, identifier, duplicate-workspace identifier, confidence, and contract validation rules.
- [x] Implement workspace-authorized extraction correction, revision history, blocking approval rules, approved output, reviews, and audit events.
- [x] Cover idempotent worker replay, retries, arithmetic/provider-path failures, Arabic preservation, legal transitions, correction, approval, and audit persistence with tests.

## Phase 4 — Hybrid retrieval and grounded Q&A

- [x] Implement page-aware chunking and 768-dimension embedding persistence.
- [x] Implement workspace/document-filtered PostgreSQL full-text and pgvector cosine retrieval.
- [x] Implement reciprocal-rank fusion with deterministic tests and documented bilingual limitations.
- [x] Build bounded grounded-answer context containing only retrieved page chunks.
- [x] Return evidence-backed answers with verified page citations/excerpts or the explicit unsupported response.
- [x] Add per-document/per-user question limits, latency/model/prompt/token/retrieval metadata, hashed questions, and privacy-safe logging.
- [x] Add precomputed public-demo answers to keep the anonymous demo useful without Gemini quota.

## Phase 5 — Complete bilingual product experience

- [x] Complete recruiter landing, architecture, evaluation, sign-in, and public-demo routes.
- [x] Implement Firebase Google/email auth, secure logout, ID-token forwarding, protected routes, and isolated local test auth.
- [x] Build dashboard lists, filename search, status/type/language/approval filters, retry states, bounded polling, limits, and quality metrics.
- [x] Build responsive split authenticated browser-PDF/detail view with fields, issues, grounded Q&A, processing, and workspace-scoped audit tabs.
- [x] Add correction/approval workflows, citation navigation, loading/empty/error/retry states, keyboard navigation, visible focus, and accessible contrast.
- [x] Verify production compilation plus desktop and mobile browser journeys, English LTR, Arabic RTL direction, and horizontal-overflow behavior.

## Phase 6 — Synthetic data, evaluation, and comprehensive tests

- [x] Generate 12 fictional English, Arabic, and bilingual invoice, quotation, purchase-order, and short-contract PDFs from versioned source cases.
- [x] Include multi-page tables, scanned-looking layout, malformed/missing/low-confidence values, duplicate identifiers, injection text, difficult dates, AED, USD, and EUR cases.
- [x] Keep the public demo on processed synthetic values/precomputed answers and add expected JSON without confidential or real personal data.
- [x] Implement opt-in-provider extraction, retrieval, grounding, validation/security, language-sliced, latency, token, and estimated-cost evaluation; fake remains the default.
- [x] Emit measured JSON/Markdown reports with model/prompt/parser/dataset versions, timestamps, actual baseline deltas, and per-case failures.
- [x] Add evaluation/backend tests, frontend auth/retry components, and full Playwright upload/process/correct/approve/audit/isolation journeys.
- [x] Meet frontend coverage thresholds at 86.67% statements/lines, 76% functions, and 69.44% branches; publish only executed fake-provider measurements with explicit caveats.

## Phase 7 — Cloud infrastructure, security, observability, and delivery

- [x] Author Terraform for APIs, least-privilege service accounts/IAM, Artifact Registry, private Storage, Tasks, Run, secrets, WIF, limits, cleanup, logging, and optional budget alerts.
- [x] Add idempotent bootstrap/deploy/configure/seed/smoke scripts and App Hosting manual fallback instructions.
- [x] Define API (0–2 instances, 512 MiB) and private worker (0–1 instances, 1 GiB, concurrency 1), guarded until immutable images and a Neon secret exist.
- [x] Provision remote state, private bucket lifecycle/CORS/uniform access, low-rate OIDC Tasks retries, and image cleanup.
- [x] Add structured telemetry, correlation, health/readiness, workspace usage/quality summaries, daily token totals, and optional OpenTelemetry export.
- [x] Add secure headers/CSP/CORS/rate limits/safe errors, PII-aware logging, dependency/secret scanning, retention cleanup, and threat documentation.
- [x] Add PR CI, WIF-backed main backend deployment, migration/OpenAPI/Docker/Terraform/E2E gates, actionlint validation, and Dependabot.
- [~] Select Firebase App Hosting GitHub integration as the single frontend rollout owner; connecting it requires an approved GitHub repository remote.

## Phase 8 — Documentation, private guide, deployment, and completion audit

- [x] Complete recruiter README, Mermaid architecture/sequences, screenshots only when real, and all required operational/architecture documents.
- [x] Add all 12 architecture decision records, IAM role rationale, cost caveats, deployment instructions, and operations runbook.
- [x] Create `../gulfdocs-private/GULFDOCS_LEARNING_GUIDE.md` from the actual implementation and verify it is outside the repository.
- [x] Install Terraform 1.15.8 and validate the pinned Terraform configuration locally.
- [x] Obtain explicit selection/approval for the dedicated billing-enabled GCP project.
- [~] Configure a deployed PostgreSQL service and verify Vertex AI Gemini for real-provider/database/cloud smoke tests; local adapters remain the deterministic fallback.
- [~] Provision the cloud foundation and immutable images only after local quality gates pass; runtime privacy, OIDC delivery, scaling, logs, and deployed synthetic E2E remain blocked on Neon.
- [~] Record verified resources, test/coverage/evaluation results, costs/risks, limitations, resume bullets, and walkthrough; real URLs remain intentionally absent until smoke tests pass.
- [ ] Confirm no secrets/private-spec files are tracked, clean Git status, and remove or convert this temporary file.

## Blocker log

| Blocker                                    | Exact impact                                                                              | Local continuation                                                                                          |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Neon connection string not supplied        | Deployed Neon repository behavior cannot be smoke-tested.                                 | Test against local PostgreSQL with pgvector and keep repositories database-portable.                        |
| Gemini live configuration not yet verified | Real extraction, embeddings, Q&A, quota, latency, and cost metrics are not yet measured.  | Use Vertex AI ADC in the selected project and retain the deterministic fake as the default evaluation path. |
| GitHub remote not configured               | WIF repository binding and Firebase App Hosting's GitHub rollout cannot be activated yet. | Create a private repository now; make it public only with explicit approval.                                |
| Google sign-in provider not configured     | Email/password works, but Google OAuth still needs Firebase provider authorization.       | Keep the implemented Google client flow and finish provider authorization with the live frontend.           |

## Verified command log

Only real results belong here.

| Date       | Command/check              | Result                                                                                                                                                                                         |
| ---------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-07-30 | Private specification read | Passed: complete 2,345-line file read from outside repository.                                                                                                                                 |
| 2026-07-30 | Project directory audit    | Passed: empty, no unrelated files.                                                                                                                                                             |
| 2026-07-30 | Git audit                  | Initialized on `feat/gulfdocs-platform`; no remote configured.                                                                                                                                 |
| 2026-07-30 | Tool audit                 | Git 2.39.1, GitHub CLI 2.93.0, gcloud 548.0.0, Firebase CLI 15.24.0, Node 22.18.0, pnpm 10.6.5, uv 0.9.18, Docker 29.4.3; Terraform missing.                                                   |
| 2026-07-30 | Formatting and lint        | Passed: Prettier, Ruff format/check, and ESLint with zero warnings.                                                                                                                            |
| 2026-07-30 | Type checks                | Passed: strict TypeScript and strict mypy across API, worker, and domain sources.                                                                                                              |
| 2026-07-30 | Backend tests              | Passed: 19 tests; 94% combined statement coverage. One upstream TestClient deprecation warning remains.                                                                                        |
| 2026-07-30 | Frontend unit tests        | Passed: 3 tests; 100% statements/lines/functions and 90.9% branches on the measured Phase 1 component/data surface.                                                                            |
| 2026-07-30 | Browser test               | Passed: 1 Chromium recruiter journey through landing page, demo question, answer, and page citation.                                                                                           |
| 2026-07-30 | Next.js production build   | Passed: seven application routes plus not-found page compiled and statically prerendered.                                                                                                      |
| 2026-07-30 | Container builds/runtime   | Passed: non-root API and worker images built; health checks, unauthenticated rejection, and authenticated task processing verified.                                                            |
| 2026-07-30 | PostgreSQL/pgvector        | Passed: PostgreSQL 17 container became healthy and pgvector 0.8.6 extension loaded; container stopped after verification.                                                                      |
| 2026-07-30 | Local smoke                | Passed: API health and seeded synthetic public-demo listing.                                                                                                                                   |
| 2026-07-30 | Alembic schema             | Passed: clean downgrade/upgrade, pgvector initialization, and `alembic check` with no drift.                                                                                                   |
| 2026-07-30 | Authenticated upload tests | Passed: 3 PostgreSQL integration journeys covering idempotency, PDF validation, completion/queueing, and cross-workspace denial.                                                               |
| 2026-07-30 | Backend tests (Phase 2)    | Passed: 25 tests total with strict Ruff and mypy checks; one upstream TestClient deprecation warning remains.                                                                                  |
| 2026-07-30 | Phase 3 domain tests       | Passed: 20 document-intelligence tests covering page boundaries, bilingual detection, citations, arithmetic mismatch, injection signals, and 768-dimension embeddings.                         |
| 2026-07-31 | Dedicated GCP selection    | Passed: the user-selected project is active, billing-enabled, selected in gcloud, and owned by the authenticated development account; identifiers are intentionally untracked.                 |
| 2026-07-31 | Phase 3 complete           | Passed: 36 backend tests including persistent worker processing/replay/failure, pgvector indexing, corrections, approval, revisions, and audits; Ruff, mypy, and Alembic drift checks passed.  |
| 2026-07-31 | Phase 4 complete           | Passed: 37 backend tests including RRF ordering, bounded context, PostgreSQL FTS/pgvector retrieval, cited answers, unsupported answers, history, and cross-workspace Q&A denial.              |
| 2026-07-31 | Phase 5 frontend gates     | Passed: strict TypeScript, ESLint with zero warnings, Prettier, Next.js production build, 9 Vitest tests at 78.28% statements/lines and 66.49% branches, and authenticated component journeys. |
| 2026-07-31 | Phase 5 backend gates      | Passed: 37 tests including workspace-scoped audit history and cross-workspace denial; strict Ruff and mypy checks pass. Two upstream deprecation warnings remain.                              |
| 2026-07-31 | Phase 5 browser gates      | Passed: 4 serial Chromium journeys covering signed-out protection, authenticated review/evidence/audit, public demo, mobile RTL, tablet responsiveness, and horizontal-overflow assertions.    |
| 2026-07-31 | Phase 6 measured eval      | Passed: 12 fictional PDFs; fake-ai-v1 measured 100% classification, 99.07% fields, 100% recall@3/citation precision/unsupported handling, and one disclosed difficult-date failure.            |
| 2026-07-31 | Phase 6 test gates         | Passed: 41 Python tests, 13 Vitest tests at 86.67% statements/lines and 69.44% branches, strict Ruff/mypy/TypeScript/ESLint, Prettier, and Next.js production build.                           |
| 2026-07-31 | Phase 6 browser gates      | Passed: 5 serial Chromium journeys including fixture upload, signed-upload handshake, processing, correction, approval, audit, and simulated cross-workspace 404.                              |
| 2026-09-08 | Phase 7 targeted backend   | Passed: 12 API/worker tests covering authenticated metrics, usage/tokens, retention purge/audit, OIDC fail-closed behavior, and existing upload/processing flows.                              |
| 2026-09-08 | Phase 7 frontend gates     | Passed: 13 Vitest tests at 86.96% statements/lines and 70.99% branches, strict TypeScript/ESLint, formatting, production build, and 5 Chromium journeys.                                       |
| 2026-09-08 | Security/dependency gates  | Passed: npm and Python audits show no known vulnerabilities after patched overrides; actionlint, Ruff, strict mypy, OpenAPI drift, and Terraform validation pass.                              |
| 2026-09-08 | GCP foundation             | Passed: 42 Terraform-managed resources created and corrected to zero drift; private bucket, low-rate queue, image cleanup, secret containers, IAM, state, and log retention verified.          |
| 2026-09-08 | Firebase Authentication    | Passed: Firebase/Web app registered; Identity Platform initialized; email/password and improved email privacy enabled. Google provider remains an explicit OAuth configuration step.           |
| 2026-09-08 | Immutable cloud images     | Passed: Cloud Build produced and pushed successful API and worker images to the private regional Artifact Registry repository.                                                                 |
| 2026-09-08 | Phase 8 documentation      | Passed: recruiter README, all required technical/operational documents, 12 ADRs, and the private out-of-repository learning guide were completed; no fake URL or screenshot was published.     |
