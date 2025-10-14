import os
from pathlib import Path
from typing import Any, List

from environs import Env
from pydantic_settings import BaseSettings

env = Env()


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    PROJECT_NAME: str = env.str("PROJECT_NAME", "Portfolia API")
    VERSION: str = env.str("VERSION", "1.0.0")
    DEBUG: bool = env.bool("DEBUG", False)
    ENVIRONMENT: str = env.str("ENVIRONMENT", "development")

    # Server settings
    HOST: str = env.str("HOST", "0.0.0.0")
    PORT: int = env.int("PORT", 8000)

    # API settings
    API_V1_STR: str = env.str("API_V1_STR", "/api/v1")
    API_HOST: str = env.str("API_HOST", "localhost")
    API_PORT: int = env.int("API_PORT", 8000)
    API_URL: str = env.str("API_URL", "http://localhost:8000")

    # CORS settings
    ALLOWED_ORIGINS: List[str] = env.list("ALLOWED_ORIGINS", ["*"])

    # Database settings
    POSTGRES_HOST: str = env.str("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = env.int("POSTGRES_PORT", 5432)
    POSTGRES_USER: str = env.str("POSTGRES_USER", "username")
    POSTGRES_PASSWORD: str = env.str("POSTGRES_PASSWORD", "password")
    POSTGRES_DB: str = env.str("POSTGRES_DB", "portfolio")

    # Database pool settings
    POOL_SIZE: int = env.int("POOL_SIZE", 20)
    MAX_OVERFLOW: int = env.int("MAX_OVERFLOW", 30)
    POOL_TIMEOUT: int = env.int("POOL_TIMEOUT", 30)
    POOL_RECYCLE: int = env.int("POOL_RECYCLE", 3600)

    # Redis settings
    REDIS_HOST: str = env.str("REDIS_HOST", "localhost")
    REDIS_PORT: int = env.int("REDIS_PORT", 6379)
    REDIS_DB: int = env.int("REDIS_DB", 0)
    REDIS_PASSWORD: str = env.str("REDIS_PASSWORD", "")

    # JWT settings
    SECRET_KEY: str = env.str("SECRET_KEY", "your-secret-key-here")
    JWT_SECRET_KEY: str = env.str(
        "JWT_SECRET_KEY", "your-jwt-secret-key-change-in-production"
    )
    ALGORITHM: str = env.str("ALGORITHM", "HS256")
    JWT_ALGORITHM: str = env.str("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = env.int("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = env.int("REFRESH_TOKEN_EXPIRE_MINUTES", 30)

    # Logging
    LOG_LEVEL: str = env.str("LOG_LEVEL", "info")

    # External API settings
    YAHOO_FINANCE_API_KEY: str = env.str("YAHOO_FINANCE_API_KEY", "")
    ALPHA_VANTAGE_API_KEY: str = ""

    # Test settings
    TESTING: bool = env.bool("TESTING", False)
    TEST_DATABASE_URL: str = env.str("TEST_DATABASE_URL", "sqlite:///./test.db")

    # Email settings
    EMAIL_FROM: str = env.str("EMAIL_FROM", "")
    EMAIL_HOST_USER: str = env.str("EMAIL_HOST_USER", "noreply@portfolia.com")
    EMAIL_HOST_PASSWORD: str = env.str("EMAIL_HOST_PASSWORD", "")
    EMAIL_HOST: str = env.str("EMAIL_HOST", "smtp-relay.brevo.com")
    EMAIL_PORT: int = env.int("EMAIL_PORT", 587)

    STATIC_DIR: str = env.str("STATIC_DIR", "STATICS")

    FRONTEND_URL: str = env.str("FRONTEND_URL", "http://localhost:3000")

    ALLOW_MONITORING: bool = env.bool("ALLOW_MONITORING", False)
    SENTRY_DSN: str = env.str("SENTRY_DSN", "")
    SEND_DEFAULT_PII: bool = env.bool("SEND_DEFAULT_PII", False)
    TRACES_SAMPLE_RATE: float = env.float("TRACES_SAMPLE_RATE", 1.0)
    PROFILE_SESSION_SAMPLE_RATE: float = env.float("PROFILE_SESSION_SAMPLE_RATE", 1.0)
    PROFILE_LIFECYCLE: str = env.str("PROFILE_LIFECYCLE", "trace")

    @property
    def STATIC_FILE_PATH(self) -> Path:
        return Path(__file__).parent / self.STATIC_DIR

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        if self.TESTING:
            return self.TEST_DATABASE_URL
        return (f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
                f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}")

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from components."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs: Any) -> None:
        from dotenv import load_dotenv

        load_dotenv()
        super().__init__(**kwargs)

        # Note: DATABASE_URL is a read-only property, so we don't override it here


# Create settings instance
settings = Settings()

# Override for testing if TESTING environment variable is set
if os.getenv("TESTING", "false").lower() == "true":
    settings.TESTING = True
    # Note: DATABASE_URL will be computed dynamically via the property
