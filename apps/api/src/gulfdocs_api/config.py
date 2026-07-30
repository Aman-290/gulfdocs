from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    public_demo_enabled: bool = True
    database_url: str = "postgresql+psycopg://gulfdocs:gulfdocs@localhost:55432/gulfdocs"
    auth_provider: str = "development"
    storage_provider: str = "local"
    task_queue_provider: str = "inline"
    local_storage_root: str = ".local-storage"
    local_upload_signing_secret: str = "local-development-only-change-me"
    upload_url_ttl_seconds: int = 600
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gcs_bucket: str = ""
    cloud_tasks_queue: str = ""
    cloud_tasks_worker_url: str = ""
    cloud_tasks_invoker_service_account: str = ""
    max_pdf_size_bytes: int = 10 * 1024 * 1024
    max_document_pages: int = 50
    max_uploads_per_user_per_day: int = 5
    max_questions_per_user_per_day: int = 20
    max_questions_per_document: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
