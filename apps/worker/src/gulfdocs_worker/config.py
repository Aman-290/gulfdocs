from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    worker_auth_mode: str = "development"
    worker_development_token: str = "local-development-only"
    worker_oidc_audience: str = ""
    worker_invoker_service_account: str = ""
    worker_processing_mode: str = "mock"
    database_url: str = "postgresql+psycopg://gulfdocs:gulfdocs@localhost:55432/gulfdocs"
    storage_provider: str = "local"
    local_storage_root: str = ".local-storage"
    gcp_project_id: str = ""
    gcs_bucket: str = ""
    ai_provider: str = "fake"
    gemini_api_key: str | None = None
    gcp_region: str = "us-central1"
    gemini_extraction_model: str = "gemini-3.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    max_processing_retries: int = 3
    max_worker_duration_seconds: int = 540


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
