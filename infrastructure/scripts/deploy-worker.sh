#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${IMAGE_TAG:?Set IMAGE_TAG to an immutable tag such as a Git commit SHA}"
: "${TASK_INVOKER_SERVICE_ACCOUNT:?Set TASK_INVOKER_SERVICE_ACCOUNT}"
REGION="${REGION:-us-central1}"
SERVICE="${WORKER_SERVICE:-gulfdocs-production-worker}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/gulfdocs/worker:${IMAGE_TAG}"

gcloud builds submit --project "${PROJECT_ID}" \
  --config infrastructure/cloudbuild/worker.yaml --substitutions "_IMAGE=${IMAGE}" .
gcloud run deploy "${SERVICE}" \
  --project "${PROJECT_ID}" --region "${REGION}" --platform managed \
  --image "${IMAGE}" --service-account "gulfdocs-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated --ingress internal --min 0 --max 1 --cpu 1 --memory 1Gi \
  --concurrency 1 --timeout 600 --port 8080 \
  --add-custom-audiences "https://worker.gulfdocs.internal" \
  --set-env-vars "APP_ENV=production,WORKER_AUTH_MODE=oidc,WORKER_PROCESSING_MODE=persistent,WORKER_OIDC_AUDIENCE=https://worker.gulfdocs.internal,WORKER_INVOKER_SERVICE_ACCOUNT=${TASK_INVOKER_SERVICE_ACCOUNT},STORAGE_PROVIDER=gcs,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCS_BUCKET=${PROJECT_ID}-gulfdocs-production-documents,AI_PROVIDER=gemini,DOCUMENT_RETENTION_DAYS=30" \
  --set-secrets "DATABASE_URL=gulfdocs-database-url:latest"

gcloud run services describe "${SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" \
  --format='table(status.url,spec.template.metadata.annotations.autoscaling\.knative\.dev/maxScale)'
