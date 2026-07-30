# GulfDocs security policy

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private documents, or personal data. Until a private reporting address is configured, contact the repository owner through a private GitHub channel and include only the minimum reproduction details.

## Phase 1 security model

- Public demo content is fictional and precomputed; it cannot upload documents or invoke a live AI model.
- The worker rejects unauthenticated task requests. Development uses a deterministic local bearer adapter; deployed OIDC verification is a tracked requirement.
- Request IDs are bounded and propagated. API errors use safe problem responses without stack traces.
- Structured logs contain identifiers and timings, not full documents, prompts, tokens, signed URLs, credentials, or extracted full text.
- PDF contents are always untrusted input. Obvious instruction-injection phrases create review signals rather than automatically declaring a document malicious.
- Local storage uses opaque object names and confines resolved paths below its configured root.

## Trust boundaries

The browser, uploaded PDFs, document text, and user questions are untrusted. The public API authenticates end users and authorizes workspace access. Cloud Tasks crosses into a separate private worker identity. Storage objects remain private. Database and AI credentials are backend-only secrets.

## Known limitations

Firebase token verification, persistent workspace authorization, signed Cloud Storage uploads, malware scanning, Cloud Tasks OIDC validation, full rate limiting, deletion, and least-privilege cloud IAM are not complete in Phase 1. GulfDocs does not claim compliance certification, perfect extraction, complete malware protection, or guaranteed prompt-injection prevention.

Do not upload confidential, personal, legally sensitive, or commercially sensitive material when using a free AI API tier.
