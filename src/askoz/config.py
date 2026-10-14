"""Typed application settings, loaded from environment variables and `.env`.

Why this matters in production: every config value is validated at startup.
A malformed DATABASE_URL fails immediately with a clear error instead of
crashing on the first request, and secrets are wrapped in SecretStr so they
never appear in logs or tracebacks.
"""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASKOZ_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: PostgresDsn = PostgresDsn("postgresql://askoz:askoz@127.0.0.1:5432/askoz")
    redis_url: RedisDsn = RedisDsn("redis://127.0.0.1:6379/0")

    voyage_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

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
