# Deployment

## Prerequisites

Use a dedicated, billing-enabled GCP/Firebase project, an authenticated `gcloud`/Firebase CLI, Terraform 1.8+, Docker, pnpm, and uv. This repository never attaches billing, creates a public GitHub repository, or stores secrets. A pooled Neon PostgreSQL URL with `pgvector` and a GitHub remote are external prerequisites for a complete deployment.

## Initial provisioning

```bash
export PROJECT_ID=replace-with-dedicated-project
export REGION=us-central1
infrastructure/scripts/bootstrap-gcp.sh
cp infrastructure/terraform/terraform.tfvars.example infrastructure/terraform/terraform.tfvars
```

Populate `terraform.tfvars` locally with `provision_runtime = false` for the foundation apply. Create secret versions without putting values in shell history (for example, write from an already secured local file with `gcloud secrets versions add ... --data-file=...`). The Terraform files create secret containers only.

The first apply creates APIs, identities/IAM, Artifact Registry, Storage, Tasks, secret containers, retention settings, logging, WIF when configured, and an optional budget. With `provision_runtime = false`, it cannot create an unusable Cloud Run revision. Use an ephemeral access token when ADC is unavailable:

```bash
export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"
terraform -chdir=infrastructure/terraform init -backend-config="bucket=${PROJECT_ID}-gulfdocs-tfstate"
terraform -chdir=infrastructure/terraform apply
# Build/push both images with infrastructure/scripts/deploy-*.sh or equivalent immutable commands.
# Add real secret versions, set both immutable image URIs and provision_runtime=true.
terraform -chdir=infrastructure/terraform apply
unset GOOGLE_OAUTH_ACCESS_TOKEN
```

Both applies are normal reviewed plans against the same remote state. Import any resource created by a manual fallback before a full apply.

## Database and seed

```bash
PROJECT_ID="$PROJECT_ID" infrastructure/scripts/seed-production.sh
```

This applies migrations and verifies the code-packaged fictional public demo. It never sends a document to Gemini.

## GitHub deployment

After a repository is approved, set production repository variables `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, and `FIREBASE_APP_ORIGIN`. Apply Terraform with `github_repository="owner/name"` to bind WIF. A successful main-branch `CI` run builds immutable backend images, updates only the two already provisioned Cloud Run services, runs migrations, performs health/privacy/demo checks, and queries release-time errors. Infrastructure changes remain an explicit reviewed Terraform apply so the deployment identity needs no project-wide infrastructure-admin role. No JSON key is used.

Follow `docs/firebase-app-hosting.md` for the single frontend rollout. Coordinate releases by keeping API changes backward compatible until App Hosting reports the new frontend healthy.

## Verification and rollback

```bash
API_BASE_URL=https://replace-after-real-deploy infrastructure/scripts/smoke-test.sh
gcloud run services describe gulfdocs-production-api --region "$REGION"
gcloud run services describe gulfdocs-production-worker --region "$REGION"
gcloud storage buckets describe "gs://${PROJECT_ID}-gulfdocs-production-documents"
gcloud tasks queues describe gulfdocs-production-documents --location "$REGION"
```

Confirm API max 2/min 0, worker max 1/min 0/concurrency 1, unauthenticated worker returns 403, bucket public-access prevention and lifecycle are active, and one synthetic upload traverses Tasks. Roll back with `gcloud run services update-traffic SERVICE --to-revisions=KNOWN_GOOD=100`; roll back App Hosting from its rollout history. Database migrations must be backward compatible before traffic rollback.
