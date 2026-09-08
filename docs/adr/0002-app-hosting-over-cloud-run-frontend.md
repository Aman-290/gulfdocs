# ADR 0002: App Hosting over a managed frontend Cloud Run service

- Status: Accepted

Firebase App Hosting owns framework-aware Next.js builds, CDN/load-balancing integration, and rollbacks. Managing another Cloud Run frontend would duplicate that work and create competing rollout ownership. The trade-off is an initial GitHub authorization step and less low-level runtime control.
