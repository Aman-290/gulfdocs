# Cost controls

GulfDocs is optimized for light portfolio traffic, not guaranteed free hosting.

- App Hosting: 0–1 instances, 1 CPU, 512 MiB, concurrency 40.
- API: 0–2 instances, 1 CPU, 512 MiB, concurrency 40, 60-second timeout.
- Worker: 0–1 instances, 1 CPU, 1 GiB, concurrency 1, 600-second timeout.
- Tasks: one dispatch/second, one concurrent dispatch, three attempts, 30-minute retry duration.
- Storage/database content: 30-day default retention; incomplete multipart uploads abort after one day.
- Artifact Registry: untagged images expire after seven days while five recent versions are retained.
- Logging: 30-day default retention and content-free structured events.
- Application: 10 MiB/50-page PDFs, five daily uploads, bounded questions, context, output tokens, retries, and processing duration.

Optional Terraform budget resources are created only when both `billing_account_id` and a positive `monthly_budget_usd` are supplied. **Budget alerts notify users but do not enforce a hard spending limit.** The configuration never attaches, modifies, or creates a billing account.

Vertex/Gemini tokens, Neon compute/storage, egress, App Hosting builds, Cloud Build, retained images, logs, and cold-start behavior can all generate charges. Check the relevant provider pricing pages and billing export before increasing any limit.
