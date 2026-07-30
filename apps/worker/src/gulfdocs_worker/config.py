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
    max_processing_retries: int = 3
    max_worker_duration_seconds: int = 540


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
