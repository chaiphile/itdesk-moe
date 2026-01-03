from functools import lru_cache

# Prefer pydantic v1's BaseSettings when available (compatible with many FastAPI versions);
# otherwise fall back to pydantic v2's `pydantic_settings` helper.
try:
    from pydantic import BaseSettings  # type: ignore
except Exception:
    from pydantic_settings import BaseSettings  # type: ignore


class Settings(BaseSettings):
    APP_NAME: str = "edu-ticketing-api"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # Database
    # read from environment; do not hardcode credentials here
    DATABASE_URL: str = ""

    # Authentication
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Placeholders for future use
    REDIS_URL: str | None = None
    CORS_ORIGINS: str = "http://localhost,http://127.0.0.1:3000"
    # S3 / MinIO
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minio"
    S3_SECRET_KEY: str = "change_me"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = False
    # Public base URL used for returned presigned URLs (host/browser reachable)
    # Example: http://localhost:9000 or https://files.myorg.edu
    S3_PUBLIC_BASE_URL: str | None = None
    S3_BUCKET: str = "ticketing-attachments"
    MINIO_BUCKET: str | None = None

    # Attachments
    ATTACHMENTS_MAX_SIZE_BYTES: int = 26214400
    ATTACHMENTS_PRESIGN_EXPIRES_SECONDS: int = 900

    # Attachment retention
    ATTACHMENT_RETENTION_DAYS: int = 30
    RETENTION_CLEANUP_INTERVAL: int = 86400  # 24 hours in seconds

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
