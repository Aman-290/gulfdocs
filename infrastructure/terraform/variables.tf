variable "project_id" {
  description = "Dedicated GCP project ID for GulfDocs."
  type        = string
}

variable "region" {
  description = "Region for latency-sensitive resources."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "production"
}

variable "api_image" {
  description = "Immutable API container image URI."
  type        = string
  default     = ""
  validation {
    condition     = !var.provision_runtime || var.api_image != ""
    error_message = "api_image is required when provision_runtime is true."
  }
}

variable "worker_image" {
  description = "Immutable worker container image URI."
  type        = string
  default     = ""
  validation {
    condition     = !var.provision_runtime || var.worker_image != ""
    error_message = "worker_image is required when provision_runtime is true."
  }
}

variable "provision_runtime" {
  description = "Create Cloud Run and Scheduler only after images and secret versions exist."
  type        = bool
  default     = false
}

variable "allowed_origins" {
  description = "Exact HTTPS origins allowed to call the API and upload to Storage."
  type        = list(string)
  default     = []
}

variable "github_repository" {
  description = "GitHub repository in owner/name form. Empty disables WIF until a remote exists."
  type        = string
  default     = ""
}

variable "billing_account_id" {
  description = "Optional billing account ID used only to create a notification budget."
  type        = string
  sensitive   = true
  default     = ""
}

variable "monthly_budget_usd" {
  description = "Optional notification-only monthly budget. Zero disables the budget resource."
  type        = number
  default     = 0
}

variable "document_retention_days" {
  description = "Maximum age of retained document objects and content."
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "Retention of the default Cloud Logging bucket."
  type        = number
  default     = 30
}
