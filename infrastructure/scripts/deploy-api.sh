#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${IMAGE_TAG:?Set IMAGE_TAG to an immutable tag such as a Git commit SHA}"
: "${ALLOWED_ORIGINS:?Set ALLOWED_ORIGINS to a JSON array of exact HTTPS origins}"
: "${WORKER_URL:?Set WORKER_URL to the private worker service URL}"
: "${TASK_INVOKER_SERVICE_ACCOUNT:?Set TASK_INVOKER_SERVICE_ACCOUNT}"
REGION="${REGION:-us-central1}"
SERVICE="${API_SERVICE:-gulfdocs-production-api}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/gulfdocs/api:${IMAGE_TAG}"

gcloud builds submit --project "${PROJECT_ID}" \
  --config infrastructure/cloudbuild/api.yaml --substitutions "_IMAGE=${IMAGE}" .
gcloud run deploy "${SERVICE}" \
  --project "${PROJECT_ID}" --region "${REGION}" --platform managed \
  --image "${IMAGE}" --service-account "gulfdocs-api@${PROJECT_ID}.iam.gserviceaccount.com" \
  --allow-unauthenticated --min 0 --max 2 --cpu 1 --memory 512Mi \
  --concurrency 40 --timeout 60 --port 8080 \
  --set-env-vars "^@^APP_ENV=production@AUTH_PROVIDER=firebase@STORAGE_PROVIDER=gcs@TASK_QUEUE_PROVIDER=cloud_tasks@GCP_PROJECT_ID=${PROJECT_ID}@GCP_REGION=${REGION}@GCS_BUCKET=${PROJECT_ID}-gulfdocs-production-documents@CLOUD_TASKS_QUEUE=gulfdocs-production-documents@CLOUD_TASKS_WORKER_URL=${WORKER_URL}/internal/tasks/process-document@CLOUD_TASKS_OIDC_AUDIENCE=https://worker.gulfdocs.internal@CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT=${TASK_INVOKER_SERVICE_ACCOUNT}@ALLOWED_ORIGINS=${ALLOWED_ORIGINS}" \
  --set-secrets "DATABASE_URL=gulfdocs-database-url:latest,LOCAL_UPLOAD_SIGNING_SECRET=gulfdocs-upload-signing-secret:latest"

gcloud run services describe "${SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" \
  --format='table(status.url,spec.template.metadata.annotations.autoscaling\.knative\.dev/maxScale)'
