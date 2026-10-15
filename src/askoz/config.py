"""Typed application settings, loaded from environment variables and `.env`.

Why this matters in production: every config value is validated at startup.
A malformed DATABASE_URL fails immediately with a clear error instead of
crashing on the first request, and secrets are wrapped in SecretStr so they
never appear in logs or tracebacks.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASKOZ_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: PostgresDsn = PostgresDsn("postgresql://askoz:askoz@127.0.0.1:5432/askoz")
    redis_url: RedisDsn = RedisDsn("redis://127.0.0.1:6379/0")

    # Where raw crawled pages are stored. Local disk in dev; object storage in prod.
    blob_dir: Path = Path("data/blobs")
    # Downloaded ML models (embedding model weights etc.).
    models_dir: Path = Path("data/models")
    # Shown in the crawler's User-Agent so site operators can identify and contact us.
    # The URL should explain what the bot is (the repo README works). Some sites
    # (e.g. the ATO) reject bots without a URL, so `askoz crawl` requires one.
    crawl_contact_url: str | None = None
    crawl_contact_email: str | None = None

    voyage_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    # Claude models. Both default to the current Opus; the rewriter runs at low
    # effort. Switch either one by env var and compare with `askoz eval`.
    answer_model: str = "claude-opus-5-5"
    rewrite_model: str = "claude-opus-5-5"

    @field_validator("crawl_contact_url", "crawl_contact_email")
    @classmethod
    def _empty_means_unset(cls, value: str | None) -> str | None:
        return value or None  # `ASKOZ_CRAWL_CONTACT_URL=` in .env means "not configured"

    @field_validator("crawl_contact_url")
    @classmethod
    def _contact_url_is_https(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("https://"):
            raise ValueError("crawl_contact_url must be an https:// URL")
        return value

    @field_validator("crawl_contact_email")
    @classmethod
    def _contact_email_looks_valid(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("crawl_contact_email must be an email address")
        return value

    @model_validator(mode="after")
    def _require_secrets_in_prod(self) -> "Settings":
        if self.env == "prod":
            missing = [
                name
                for name in ("voyage_api_key", "anthropic_api_key")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"missing required settings in prod: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process. Tests call `get_settings.cache_clear()`."""
    return Settings()
