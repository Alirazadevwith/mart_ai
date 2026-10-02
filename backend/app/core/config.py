"""Typed application settings, loaded from the environment / `.env`."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Application ----
    PROJECT_NAME: str = "Mart AI"
    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ---- Database ----
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "mart_ai"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "mart_ai"
    POSTGRES_TEST_DB: str = "mart_ai_test"

    # ---- Security ----
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # ---- CORS ----
    # NoDecode stops pydantic-settings from JSON-decoding this before our validator runs.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- LLM (Phase 2) ----
    LLM_PROVIDER: Literal["grok", "groq", "openai", "gemini", "fake"] = "fake"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    LLM_TEMPERATURE: float = 0.2

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string so `.env` stays readable."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def _dsn(self, database: str) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=database,
            )
        )

    @property
    def database_url(self) -> str:
        return self._dsn(self.POSTGRES_DB)

    @property
    def test_database_url(self) -> str:
        return self._dsn(self.POSTGRES_TEST_DB)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
