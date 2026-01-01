from functools import lru_cache

from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
