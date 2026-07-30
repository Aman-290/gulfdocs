from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    public_demo_enabled: bool = True
    max_pdf_size_bytes: int = 10 * 1024 * 1024
    max_document_pages: int = 50
    max_uploads_per_user_per_day: int = 5
    max_questions_per_user_per_day: int = 20
    max_questions_per_document: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
