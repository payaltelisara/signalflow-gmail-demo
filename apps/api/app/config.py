from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://signalflow:signalflow@localhost:5432/signalflow"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "signalflow"
    minio_secret_key: str = "signalflow-local-only"
    minio_bucket: str = "signalflow"
    session_secret: str = "change-me-before-any-non-local-use"
    dev_admin_email: str = "admin@signalflow.local"
    dev_admin_password: str = "change-me-local-password"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_import_rows: int = 50_000
    # Local Ollama is a required workflow dependency. The legacy flag remains
    # only so existing .env files parse cleanly; workers do not use it as a fallback.
    ai_enabled: bool = True
    ai_required: bool = True
    ollama_base_url: str = "http://host.containers.internal:11434"
    ollama_model: str = ""
    ollama_timeout_seconds: int = 20
    ollama_max_concurrency: int = 2
    ai_max_input_characters: int = 6000
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173"
    public_app_url: str = "http://localhost:8080"
    credential_encryption_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8080/api/v1/integrations/gmail/callback"
    gmail_poll_interval_seconds: int = 300
    gmail_test_mode: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = False
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_poll_interval_seconds: int = 300
    api_rate_limit_per_minute: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
