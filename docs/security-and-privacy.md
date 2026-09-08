# Security and privacy

The authoritative threat model and vulnerability-reporting policy are in `SECURITY.md`.

Defense in depth includes Firebase token verification, workspace filters at route and repository layers, opaque private object paths, short signed URLs, size/MIME/PDF-signature/page checks, private OIDC worker invocation, idempotent tasks, parameterized SQL, escaped UI output, safe problem responses, audit history, configurable retention, narrow IAM, and WIF deployment.

Document text is untrusted data. It never receives tools or credentials and cannot change system instructions. Suspicious phrases create reviewable security events. Answers are restricted to authorized retrieved chunks and must cite returned pages or explicitly say evidence is insufficient.

Logs contain identifiers, versions, counts, categories, durations, and hashes—not PDFs, full text, prompts/questions, tokens, signed URLs, or credentials. A portfolio deployment should accept only synthetic/non-sensitive data. GulfDocs does not claim malware protection, regulatory compliance, perfect OCR, or guaranteed prompt-injection prevention.
