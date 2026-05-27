"""Brain-specific settings read from the project .env file.

These mirror the relevant portion of rain_backend.settings so the brain
package doesn't import from rain-api (avoiding circular imports).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BrainSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "glm-5.1:cloud"
    ollama_keep_alive_minutes: int = 5
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_extraction_model: str = "glm-5.1:cloud"

    # Persona default models (resolved via model-management tags at runtime)
    drizzle_default_model: str = ""
    shower_default_model: str = ""
    storm_default_model: str = ""

    # Phase 2+ providers
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # MinIO
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_bucket_uploads: str = "rain-uploads"
    minio_secure: bool = False

    # Feature toggles
    self_correction_enabled: bool = False

    # Observability — Langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"


brain_settings = BrainSettings()
