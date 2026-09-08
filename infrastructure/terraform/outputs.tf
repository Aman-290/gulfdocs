output "api_url" {
  value = var.provision_runtime ? google_cloud_run_v2_service.api[0].uri : null
}

output "worker_url" {
  value     = var.provision_runtime ? google_cloud_run_v2_service.worker[0].uri : null
  sensitive = true
}

output "documents_bucket" {
  value = google_storage_bucket.documents.name
}

output "artifact_repository" {
  value = google_artifact_registry_repository.containers.name
}

output "github_deployer_service_account" {
  value = google_service_account.github_deployer.email
}

output "workload_identity_provider" {
  value = var.github_repository == "" ? null : google_iam_workload_identity_pool_provider.github[0].name
}
