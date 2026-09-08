#!/usr/bin/env bash
set -euo pipefail

: "${API_BASE_URL:?Set API_BASE_URL to the deployed API origin}"
API_BASE_URL="${API_BASE_URL%/}"

curl --fail --silent --show-error --max-time 20 "${API_BASE_URL}/healthz" | grep -q '"status":"ok"'
curl --fail --silent --show-error --max-time 20 "${API_BASE_URL}/readyz" | grep -q '"status":"ready"'
curl --fail --silent --show-error --max-time 20 "${API_BASE_URL}/api/v1/demo/documents" | grep -q 'GulfDocs'
echo "Production health, readiness, and synthetic demo smoke checks passed."
