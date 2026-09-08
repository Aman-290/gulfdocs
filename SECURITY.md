# GulfDocs security policy

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private documents, or personal data. Until a dedicated security address is published, contact the repository owner through a private GitHub channel and include the minimum reproduction information. Never attach a real business document.

## Threat model and trust boundaries

GulfDocs treats the browser, uploaded bytes, PDF text, metadata, filenames, questions, and all model output as untrusted. Firebase establishes user identity; every private API query also enforces membership in the selected workspace. The public API, private Storage bucket, OIDC-authenticated task boundary, private worker, PostgreSQL, Gemini, and deployment identity are separate trust zones.

Primary threats include cross-workspace identifier substitution, forged Firebase or task tokens, signed-URL reuse, malicious PDFs, prompt injection, duplicate task delivery, model hallucination, credential disclosure, over-broad IAM, public storage, supply-chain compromise, denial of service, and data surviving its retention period.

## Implemented controls

- Firebase Admin verifies deployed ID tokens; deterministic development auth is accepted only in development/test. Repository queries scope every private document operation to the authenticated workspace, with cross-workspace denial tests.
- Direct uploads use opaque object keys, short-lived signed URLs, expected size/type metadata, PDF magic-byte checks, a 10 MiB limit, and a 50-page limit. The GCS design enforces uniform bucket access and public-access prevention.
- Cloud Tasks carries identifiers only. The worker rejects anonymous calls, validates a Google-signed OIDC token against a dedicated custom audience, and requires the dedicated invoker email. Processing is row-locked, idempotent, bounded, and atomically finalized.
- Queries use SQLAlchemy parameter binding. Pydantic validates request/response shapes. Browser content is escaped by React. Errors use RFC 9457-style safe details and opaque error/request IDs without stack traces.
- Public demo answers are precomputed from fictional documents and are rate-limited per API instance. Authenticated uploads/questions also have persistent daily and per-document limits.
- Extraction is not trusted. Deterministic validation, citations, review-required states, revision history, explicit approval, unsupported-answer behavior, and audit/security events constrain model output.
- Prompts label document instructions as data and provide no shell, URL, filesystem, email, calendar, database, or cloud-management tools. Obvious injection language creates a review signal; detection is not a malware verdict.
- Structured logs include bounded identifiers, durations, categories, model versions, token counts, and correlation IDs. They exclude PDF/text bodies, complete prompts/questions, tokens, signed URLs, database URLs, API keys, and unnecessary personal data.
- Scheduled retention deletes expired objects and content-bearing database rows, sanitizes document metadata, and preserves only privacy-safe audit/processing metadata. GCS lifecycle rules provide a second deletion boundary.
- CI checks formatting, linting, types, migrations, OpenAPI drift, tests, browser journeys, container builds, Terraform, dependency vulnerabilities, and Git history with Gitleaks. Deployment uses GitHub OIDC/WIF and never service-account JSON keys.
- Response headers include MIME sniffing, framing, referrer, permissions, and production HSTS controls. The frontend owns its CSP and HTTPS policy through Next.js/App Hosting.

## IAM and secrets

Runtime, task invocation, and deployment identities are separate. The API can manage objects, enqueue Tasks, sign its own GCS URLs, and read only its two secrets. The worker can read/delete document objects, invoke Vertex AI, and read only the database secret. The invoker can invoke only the worker. The GitHub identity can deploy services, push images, impersonate runtime service accounts, access migration state/database secret, and has no document-object or Vertex permissions. Exact bindings are documented in `docs/gcp-iam.md`.

Secret Manager resources intentionally contain no Terraform-managed secret values. Operators add versions out of band. Frontend `NEXT_PUBLIC_` variables may contain only public Firebase/App/API configuration.

## Privacy and deletion

Do not upload confidential, personal, legally sensitive, or commercially sensitive material to a portfolio/free-tier deployment. Delete is workspace-authorized and storage-aware. Scheduled retention is configurable (30 days by default). Cloud backups, provider logs, and model-provider retention may follow separate provider policies and must be reviewed before real organizational use.

## Known limitations

- GulfDocs does not implement antivirus or sandboxed malware scanning; it validates structure and processes PDFs with maintained libraries. Password-protected, damaged, handwritten, rotated, low-resolution, and unusual-font documents may fail.
- Per-instance public rate limiting is a low-cost abuse control, not a distributed WAF. A production service should add Cloud Armor/API Gateway or a shared limiter.
- Prompt-injection detection and citation checks reduce risk but cannot guarantee safe or correct model output.
- This project has no compliance, legal, privacy, security, or extraction-accuracy certification.
- Budget alerts are notifications and do not enforce a hard spending cap.
- Live Neon, Gemini, Cloud Run/Tasks/Storage, Firebase sign-in providers, and App Hosting rollout must be smoke-tested before any production claim.
