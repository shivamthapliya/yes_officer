"""Application settings, read from the environment (and `.env` in development).

Every tunable lives here so nothing is hardcoded elsewhere in the codebase.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from typing import Annotated

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    APP_NAME: str = "Yes Officer — Quiz & Live Polling"
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Database ---
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    REDIS_POLL_TTL_SECONDS: int = 24 * 60 * 60
    ACTIVE_POINTER_GRACE_SECONDS: int = 10 * 60

    # --- Auth ---
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ACCESS_COOKIE_NAME: str = "yo_access"
    REFRESH_COOKIE_NAME: str = "yo_refresh"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    AUTH_RATE_LIMIT: str = "10/minute"

    # --- Internal worker -> API callbacks ---
    INTERNAL_API_BASE_URL: str = "http://localhost:8000"
    INTERNAL_SHARED_SECRET: str

    # --- Chat & AI batching ---
    CHAT_MAX_LENGTH: int = 500
    CHAT_RATE_LIMIT_COUNT: int = 5
    CHAT_RATE_LIMIT_WINDOW_SECONDS: float = 5.0
    CHAT_BATCH_SIZE: int = 50
    CHAT_FLUSH_INTERVAL_SECONDS: int = 10
    BATCH_RECOVERY_INTERVAL_SECONDS: int = 30
    BATCH_RECOVERY_AGE_SECONDS: int = 60
    BATCH_MAX_ATTEMPTS: int = 3
    WS_SEND_TIMEOUT_SECONDS: float = 2.0

    # --- LLM ---
    LLM_PROVIDER: str = "auto"  # auto | groq | anthropic | stub
    ANTHROPIC_API_KEY: str | None = None
    # Groq (groq.com, OpenAI-compatible). GROK_API_KEY is accepted as a common misspelling.
    GROQ_API_KEY: str | None = Field(None, validation_alias=AliasChoices("GROQ_API_KEY", "GROK_API_KEY"))
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT_SECONDS: float = 60.0
    # Empty means "the provider's default": claude-opus-5-5 (anthropic) or openai/gpt-oss-120b (groq).
    LLM_MODEL: str = ""
    LLM_EFFORT: str = "low"
    LLM_MAX_TOKENS: int = 16000

    # --- Polls ---
    POLL_MIN_TIME_LIMIT_SECONDS: int = 10
    POLL_MAX_TIME_LIMIT_SECONDS: int = 300
    POLL_MIN_OPTIONS: int = 2
    POLL_MAX_OPTIONS: int = 6

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str) and not value.strip().startswith("["):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @property
    def llm_provider(self) -> str:
        """The analyzer to use: an explicit LLM_PROVIDER, or in "auto" whichever key is set."""
        if self.LLM_PROVIDER in ("groq", "anthropic", "stub"):
            return self.LLM_PROVIDER
        if self.GROQ_API_KEY:
            return "groq"
        if self.ANTHROPIC_API_KEY:
            return "anthropic"
        return "stub"

    @property
    def use_real_llm(self) -> bool:
        return self.llm_provider != "stub"

    @property
    def llm_model(self) -> str:
        if self.LLM_MODEL:
            return self.LLM_MODEL
        return "openai/gpt-oss-120b" if self.llm_provider == "groq" else "claude-opus-5-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
