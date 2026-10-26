from pathlib import Path
from typing import Annotated, Any, List, Optional

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LOCAL_ENVIRONMENTS = {"development", "dev", "local", "test"}
INSECURE_SECRET_DEFAULTS = {
    "",
    "password",
    "change-me",
    "your-secret-key-here",
    "your-jwt-secret-key-change-in-production",
}


class Settings(BaseSettings):
    """Application settings. Environment variables override the defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Portfolia API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    API_V1_STR: str = "/api/v1"
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    API_URL: str = "http://localhost:8000"

    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = Field(default_factory=list)

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "username"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "portfolio"

    POOL_SIZE: int = 20
    MAX_OVERFLOW: int = 30
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 3600

    WORKER_INTERVAL_SECONDS: int = 900

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_TTL_SECONDS: int = 8 * 60 * 60
    REDIS_TTL_MODEL_SECONDS: int = 8 * 60 * 60

    # JWT_SECRET_KEY wins when both are set, so existing tokens keep verifying.
    SECRET_KEY: str = Field(
        default="your-secret-key-here",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_EXPIRE_MINUTES_OVERRIDE: Optional[int] = Field(
        default=None,
        validation_alias="REFRESH_TOKEN_EXPIRE_MINUTES",
    )

    LOG_LEVEL: str = "info"

    YAHOO_FINANCE_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""

    TESTING: bool = False
    TEST_DATABASE_URL: str = "sqlite:///./test.db"

    EMAIL_FROM: str = ""
    EMAIL_HOST_USER: str = "noreply@portfolia.com"
    EMAIL_HOST_PASSWORD: str = ""
    EMAIL_HOST: str = "smtp-relay.brevo.com"
    EMAIL_PORT: int = 587

    STATIC_DIR: str = "STATICS"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def default_origins(self) -> "Settings":
        if not self.ALLOWED_ORIGINS:
            self.ALLOWED_ORIGINS = [self.FRONTEND_URL]
        return self

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.SECRET_KEY

    @property
    def REFRESH_TOKEN_EXPIRE_MINUTES(self) -> int:
        if self.REFRESH_TOKEN_EXPIRE_MINUTES_OVERRIDE is not None:
            return self.REFRESH_TOKEN_EXPIRE_MINUTES_OVERRIDE
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60

    @property
    def STATIC_FILE_PATH(self) -> Path:
        return Path(__file__).parent / self.STATIC_DIR

    @property
    def DATABASE_URL(self) -> str:
        if self.TESTING:
            return self.TEST_DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def validate_secrets(self) -> None:
        """Refuse placeholder secrets outside local development."""
        if self.ENVIRONMENT.lower() in LOCAL_ENVIRONMENTS or self.TESTING:
            return

        problems = []
        if self.SECRET_KEY in INSECURE_SECRET_DEFAULTS or len(self.SECRET_KEY) < 32:
            problems.append(
                "SECRET_KEY is unset, a placeholder, or shorter than 32 chars"
            )
        if self.POSTGRES_PASSWORD in INSECURE_SECRET_DEFAULTS:
            problems.append("POSTGRES_PASSWORD is unset or a placeholder")
        if not self.REDIS_PASSWORD:
            problems.append("REDIS_PASSWORD is not set")
        if "*" in self.ALLOWED_ORIGINS:
            problems.append('ALLOWED_ORIGINS must list explicit origins, not "*"')

        if problems:
            raise RuntimeError(
                f"Insecure configuration for ENVIRONMENT={self.ENVIRONMENT}: "
                + "; ".join(problems)
            )


settings = Settings()
settings.validate_secrets()
