locals {
  prefix          = "gulfdocs-${var.environment}"
  api_name        = "${local.prefix}-api"
  worker_name     = "${local.prefix}-worker"
  worker_audience = "https://worker.gulfdocs.internal"
  bucket_name     = "${var.project_id}-${local.prefix}-documents"
  allowed_origins = length(var.allowed_origins) > 0 ? var.allowed_origins : ["https://invalid.example"]
  required_services = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "firebase.googleapis.com",
    "firebaseapphosting.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "identitytoolkit.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each           = local.required_services
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "api" {
  account_id   = "gulfdocs-api"
  display_name = "GulfDocs API runtime"
}

resource "google_service_account" "worker" {
  account_id   = "gulfdocs-worker"
  display_name = "GulfDocs worker runtime"
}

resource "google_service_account" "task_invoker" {
  account_id   = "gulfdocs-task-invoker"
  display_name = "GulfDocs Tasks and Scheduler invoker"
}

resource "google_service_account" "github_deployer" {
  account_id   = "gulfdocs-github-deploy"
  display_name = "GulfDocs GitHub Actions deployer"
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "gulfdocs"
  description   = "GulfDocs backend container images"
  format        = "DOCKER"

  cleanup_policies {
    id     = "delete-untagged-after-seven-days"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"
    }
  }

  cleanup_policies {
    id     = "keep-five-recent-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "documents" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  cors {
    origin          = local.allowed_origins
    method          = ["GET", "HEAD", "PUT"]
    response_header = ["Content-Type", "ETag", "x-goog-content-length-range"]
    max_age_seconds = 600
  }

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      age = var.document_retention_days
    }
  }

  lifecycle_rule {
    action { type = "AbortIncompleteMultipartUpload" }
    condition { age = 1 }
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "gulfdocs-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "upload_signing_secret" {
  secret_id = "gulfdocs-upload-signing-secret"
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_tasks_queue" "documents" {
  name     = "${local.prefix}-documents"
  location = var.region

  rate_limits {
    max_concurrent_dispatches = 1
    max_dispatches_per_second = 1
  }

  retry_config {
    max_attempts       = 3
    max_retry_duration = "1800s"
    min_backoff        = "10s"
    max_backoff        = "300s"
    max_doublings      = 4
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "worker" {
  count               = var.provision_runtime ? 1 : 0
  name                = local.worker_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false
  custom_audiences    = [local.worker_audience]

  template {
    service_account                  = google_service_account.worker.email
    timeout                          = "600s"
    max_instance_request_concurrency = 1

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.worker_image

      resources {
        limits   = { cpu = "1", memory = "1Gi" }
        cpu_idle = true
      }

      ports { container_port = 8080 }
      startup_probe {
        initial_delay_seconds = 2
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12
        http_get { path = "/healthz" }
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "WORKER_AUTH_MODE"
        value = "oidc"
      }
      env {
        name  = "WORKER_PROCESSING_MODE"
        value = "persistent"
      }
      env {
        name  = "WORKER_OIDC_AUDIENCE"
        value = local.worker_audience
      }
      env {
        name  = "WORKER_INVOKER_SERVICE_ACCOUNT"
        value = google_service_account.task_invoker.email
      }
      env {
        name  = "STORAGE_PROVIDER"
        value = "gcs"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.documents.name
      }
      env {
        name  = "AI_PROVIDER"
        value = "gemini"
      }
      env {
        name  = "DOCUMENT_RETENTION_DAYS"
        value = tostring(var.document_retention_days)
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "api" {
  count               = var.provision_runtime ? 1 : 0
  name                = local.api_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account                  = google_service_account.api.email
    timeout                          = "60s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.api_image

      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }

      ports { container_port = 8080 }
      startup_probe {
        initial_delay_seconds = 2
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12
        http_get { path = "/healthz" }
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "AUTH_PROVIDER"
        value = "firebase"
      }
      env {
        name  = "STORAGE_PROVIDER"
        value = "gcs"
      }
      env {
        name  = "TASK_QUEUE_PROVIDER"
        value = "cloud_tasks"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.documents.name
      }
      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = google_cloud_tasks_queue.documents.name
      }
      env {
        name  = "CLOUD_TASKS_WORKER_URL"
        value = "${google_cloud_run_v2_service.worker[0].uri}/internal/tasks/process-document"
      }
      env {
        name  = "CLOUD_TASKS_OIDC_AUDIENCE"
        value = local.worker_audience
      }
      env {
        name  = "CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT"
        value = google_service_account.task_invoker.email
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = jsonencode(var.allowed_origins)
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "LOCAL_UPLOAD_SIGNING_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upload_signing_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "public_api" {
  count    = var.provision_runtime ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.api[0].location
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "task_worker_invoker" {
  count    = var.provision_runtime ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.worker[0].location
  name     = google_cloud_run_v2_service.worker[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.task_invoker.email}"
}

resource "google_cloud_scheduler_job" "retention" {
  count            = var.provision_runtime ? 1 : 0
  name             = "${local.prefix}-retention"
  region           = var.region
  schedule         = "17 3 * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "600s"

  retry_config {
    retry_count          = 2
    min_backoff_duration = "30s"
    max_backoff_duration = "300s"
    max_doublings        = 2
  }

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.worker[0].uri}/internal/retention/cleanup"
    oidc_token {
      service_account_email = google_service_account.task_invoker.email
      audience              = local.worker_audience
    }
  }
}

resource "google_logging_project_bucket_config" "default" {
  project        = var.project_id
  location       = "global"
  bucket_id      = "_Default"
  retention_days = var.log_retention_days
}

resource "google_billing_budget" "monthly" {
  count           = var.billing_account_id != "" && var.monthly_budget_usd > 0 ? 1 : 0
  billing_account = var.billing_account_id
  display_name    = "GulfDocs monthly notification budget"

  budget_filter { projects = ["projects/${var.project_id}"] }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(var.monthly_budget_usd))
      nanos         = floor((var.monthly_budget_usd - floor(var.monthly_budget_usd)) * 1000000000)
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
}
