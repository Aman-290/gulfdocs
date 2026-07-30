# ADR 0001: Firebase App Hosting owns frontend rollouts

- Status: Accepted
- Date: 2026-07-30

## Context

GulfDocs requires a Next.js frontend on Firebase App Hosting. Running a second frontend deployment from GitHub Actions would create competing releases and make frontend/backend coordination ambiguous.

## Decision

Use Firebase App Hosting’s GitHub-connected rollout as the single frontend deployment owner. Pull-request GitHub Actions will be the required quality gate. Main-branch automation will deploy the API and worker, run migrations and smoke tests, and permit the App Hosting rollout rather than deploying the frontend independently.

`apps/web/apphosting.yaml` holds conservative runtime and public environment configuration. Secrets will use supported App Hosting/Secret Manager references and will never be exposed through `NEXT_PUBLIC_` variables.

## Consequences

- Firebase manages framework-aware Next.js builds, Cloud Run serving, load balancing, and CDN integration.
- Releases need documented coordination because backend health must be ready for the frontend rollout.
- Initial backend creation and GitHub connection may require an explicit console/CLI step in the selected Firebase project.
- The project does not use Vercel or the older experimental Firebase Hosting integration.
