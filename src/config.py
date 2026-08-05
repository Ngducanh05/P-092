from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "FixIt Agent API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str | list[str] = "http://localhost:3000"

    # LLM
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database
    database_url: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_verification_mode: Literal["jwks", "auth_server", "auto"] = "auto"
    supabase_storage_bucket: str = "ticket-attachments"
    supabase_signed_download_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    max_ticket_image_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    allowed_ticket_image_mime_types: str | list[str] = "image/jpeg,image/png,image/webp"
    allow_live_migration: bool = False
    run_supabase_integration_tests: bool = False
    enable_legacy_agent_routes: bool = False

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    @field_validator("cors_origins", "allowed_ticket_image_mime_types", mode="before")
    @classmethod
    def _split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [item.strip() for item in value if item.strip()]
        return [item.strip() for item in value.split(",") if item.strip()]

    @computed_field
    @property
    def parsed_cors_origins(self) -> list[str]:
        return list(self.cors_origins)

    @computed_field
    @property
    def parsed_allowed_ticket_image_mime_types(self) -> set[str]:
        return set(self.allowed_ticket_image_mime_types)

    def require_database_url(self) -> str:
        """Return DATABASE_URL or raise a safe configuration error."""
        if self.database_url:
            return self.database_url
        if self.app_env == "test":
            return "sqlite:///:memory:"
        raise RuntimeError("DATABASE_URL is required for FixIt Agent API.")

    def validate_runtime_safety(self) -> None:
        """Validate startup settings without exposing secret values."""
        if self.app_env == "production" and "*" in self.parsed_cors_origins:
            raise RuntimeError("Production CORS origins must be explicit.")
        if self.app_env in {"development", "production"} and not self.database_url:
            raise RuntimeError("DATABASE_URL is required for development and production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
