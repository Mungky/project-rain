"""Database connection settings for Project Rain.

Shared config for PostgreSQL, Redis, Qdrant, and MinIO connections.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL
    postgres_dsn: str = "postgresql+asyncpg://rain:rain@localhost:5432/rain"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_vector_size: int = 768

    # MinIO
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_bucket_uploads: str = "rain-uploads"
    minio_bucket_workshop: str = "rain-workshop"
    minio_secure: bool = False


db_settings = DatabaseSettings()
