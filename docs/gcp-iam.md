# GCP IAM design

GulfDocs avoids Owner, Editor, Project Admin, downloadable keys, and shared runtime identities. Terraform in `infrastructure/terraform` is the source of truth.

| Identity                 | Binding                                                    | Why it is needed                                                                                                   |
| ------------------------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `gulfdocs-api`           | Storage object admin on the document bucket                | Create signed upload/download operations, inspect metadata, and honor authorized deletion.                         |
| `gulfdocs-api`           | Cloud Tasks enqueuer; service-account user on task invoker | Submit identifier-only OIDC document jobs; it cannot invoke or administer arbitrary services directly.             |
| `gulfdocs-api`           | Secret accessor on database/signing secrets                | Open the pooled database connection and read the application signing secret.                                       |
| `gulfdocs-api`           | Service-account token creator on itself                    | Use IAM `signBlob` for GCS V4 signed URLs without a private key file.                                              |
| `gulfdocs-worker`        | Storage object user on the document bucket                 | Read processing inputs and delete expired objects during retention cleanup.                                        |
| `gulfdocs-worker`        | Vertex AI user                                             | Run configured Gemini/embedding models through ADC.                                                                |
| `gulfdocs-worker`        | Secret accessor on database secret                         | Persist processing results without access to the API signing secret.                                               |
| `gulfdocs-task-invoker`  | Cloud Run invoker on worker only                           | Deliver Tasks and Scheduler calls with a Google-signed token.                                                      |
| `gulfdocs-github-deploy` | Artifact Registry writer, Cloud Run admin                  | Publish immutable images and deploy revisions.                                                                     |
| `gulfdocs-github-deploy` | Service-account user on API/worker                         | Attach the intended runtime identity to each deployed revision.                                                    |
| `gulfdocs-github-deploy` | Database secret accessor, Logging viewer                   | Run migrations and inspect release-time errors. It has no document-object, infrastructure-admin, or Vertex access. |

GitHub trust is repository-bound through `attribute.repository`; only the configured `owner/name` can federate. It updates already provisioned Cloud Run revisions but does not apply project-wide Terraform. Production environment protection and required CI should restrict who can trigger deployment. Cloud Scheduler receives token-minting permission on the invoker identity; Cloud Run still validates both the custom audience and invoker email.

Review IAM with `gcloud projects get-iam-policy "$PROJECT_ID"` before each release. If a role grows broader than its stated purpose, split the workflow or define a narrower custom role rather than adding a project-wide administrator role.
