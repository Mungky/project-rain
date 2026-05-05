from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    # Database
    postgres_dsn: str = "postgresql+asyncpg://rain:rain@localhost:5432/rain"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    # Persona default models
    drizzle_default_model: str = "kimi-k2.6:cloud"
    nimbus_default_model: str = "gemini-3.1-flash-image-preview"
    shower_default_model: str = ""
    storm_default_model: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "kimi-k2.6:cloud"
    ollama_keep_alive_minutes: int = 5
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_extraction_model: str = "gemma4:31b-cloud"
    qdrant_vector_size: int = 768

    # Feature toggles
    self_correction_enabled: bool = False

    # Phase 2+ providers (configure but not used in Phase 1)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # Phase 2+ MinIO
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_bucket_uploads: str = "rain-uploads"
    minio_secure: bool = False

    # Observability — Langfuse (optional)
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # Security
    session_secret_key: str = "change-me-in-production"

    # Cache TTLs (seconds)
    embedding_cache_ttl: int = 7 * 24 * 60 * 60  # 7 days
    llm_cache_ttl: int = 60 * 60  # 1 hour
    session_ttl: int = 24 * 60 * 60  # 24 hours

    @property
    def cors_allow_origins(self) -> list[str]:
        """Returns list of allowed CORS origins."""
        if self.environment == "development":
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return [self.frontend_origin]

    @property
    def providers_enabled(self) -> dict[str, bool]:
        """Which providers are enabled based on configuration."""
        enabled = {"ollama": True}  # Always enabled in Phase 1
        if self.anthropic_api_key:
            enabled["anthropic"] = True
        if self.openai_api_key:
            enabled["openai"] = True
        if self.google_api_key:
            enabled["google"] = True
        return enabled

    def get_provider_config(self, provider_name: str) -> dict[str, str]:
        """Get configuration for a specific provider."""
        configs = {
            "ollama": {"base_url": self.ollama_base_url},
            "anthropic": {"api_key": self.anthropic_api_key or ""},
            "openai": {"api_key": self.openai_api_key or ""},
            "google": {"api_key": self.google_api_key or ""},
        }
        return configs.get(provider_name, {})


settings = Settings()