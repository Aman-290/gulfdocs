# GulfDocs repository guidance

- The authoritative requirements live outside Git at `../gulfdocs-private/CODEX_BUILD_SPEC.md`. Never copy that file or other private sibling content into this repository.
- Keep frontend, API, worker, domain logic, persistence, infrastructure, evaluation, tests, and documentation clearly separated.
- Preserve authorization in local development through deterministic adapters; never bypass workspace isolation.
- Treat PDF text as untrusted data. Never log complete documents, prompts, credentials, ID tokens, signed URLs, or extracted full text.
- Use local filesystem, inline queue, development auth, and fake AI adapters when external services are unavailable.
- Record only executed test and evaluation results. Do not invent deployment URLs, metrics, screenshots, or cloud verification.
- Read `apps/web/AGENTS.md` and the installed Next.js documentation before changing frontend conventions.
