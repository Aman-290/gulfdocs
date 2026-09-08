#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to the dedicated GulfDocs GCP project}"
REGION="${REGION:-us-central1}"

active_project="$(gcloud config get-value project 2>/dev/null)"
if [[ "${active_project}" != "${PROJECT_ID}" ]]; then
  echo "Refusing to continue: active gcloud project is '${active_project}', expected '${PROJECT_ID}'." >&2
  exit 1
fi

gcloud billing projects describe "${PROJECT_ID}" --format='value(billingEnabled)' | grep -qx True || {
  echo "Billing is not enabled. This script never creates or changes billing configuration." >&2
  exit 1
}

gcloud services enable \
  aiplatform.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com cloudtasks.googleapis.com firebase.googleapis.com \
firebaseapphosting.googleapis.com iam.googleapis.com iamcredentials.googleapis.com \
  identitytoolkit.googleapis.com logging.googleapis.com monitoring.googleapis.com \
  run.googleapis.com secretmanager.googleapis.com storage.googleapis.com sts.googleapis.com \
  --project "${PROJECT_ID}"

STATE_BUCKET="${PROJECT_ID}-gulfdocs-tfstate"
if ! gcloud storage buckets describe "gs://${STATE_BUCKET}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${STATE_BUCKET}" --project "${PROJECT_ID}" \
    --location "${REGION}" --uniform-bucket-level-access --public-access-prevention
  gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning
fi

if ! firebase projects:list --json | grep -q "\"projectId\": \"${PROJECT_ID}\""; then
  firebase projects:addfirebase "${PROJECT_ID}" --non-interactive
fi

terraform -chdir=infrastructure/terraform init -backend-config="bucket=${STATE_BUCKET}" -input=false
terraform -chdir=infrastructure/terraform validate
echo "GCP/Firebase bootstrap verified for ${PROJECT_ID} in ${REGION}."
