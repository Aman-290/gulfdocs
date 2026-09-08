#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
command -v uv >/dev/null || { echo "uv is required" >&2; exit 1; }

export DATABASE_URL
DATABASE_URL="$(gcloud secrets versions access latest --secret gulfdocs-database-url --project "${PROJECT_ID}")"
trap 'unset DATABASE_URL' EXIT

uv run alembic upgrade head
uv run python -c 'from gulfdocs_document_intelligence.demo_data import DEMO_DOCUMENT; assert DEMO_DOCUMENT.synthetic'
echo "Migrations completed and the packaged, idempotent synthetic public-demo seed was verified."
