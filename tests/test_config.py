import pytest
from pydantic import ValidationError

from askoz.config import Settings


def test_env_vars_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_DATABASE_URL", "postgresql://u:p@db.example:5432/x")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.database_url.hosts()[0]["host"] == "db.example"


def test_invalid_database_url_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_DATABASE_URL", "not-a-url")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_secrets_are_masked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_ANTHROPIC_API_KEY", "sk-very-secret")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert "sk-very-secret" not in repr(settings)


def test_prod_requires_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_ENV", "prod")
    with pytest.raises(ValidationError, match="missing required settings"):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
