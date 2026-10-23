import pytest
from pydantic import ValidationError

from askoz.config import Settings


def test_env_vars_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_DATABASE_URL", "postgresql://u:p@db.example:5432/x")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.database_url == "postgresql://u:p@db.example:5432/x"


def test_unix_socket_database_url_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "postgresql://u:p@/x?host=/cloudsql/proj:australia-southeast1:db"
    monkeypatch.setenv("ASKOZ_DATABASE_URL", url)
    assert Settings(_env_file=None).database_url == url  # pyright: ignore[reportCallIssue]


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


def test_crawl_contact_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_CRAWL_CONTACT_URL", "github.com/no-scheme")
    with pytest.raises(ValidationError, match="crawl_contact_url"):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    monkeypatch.setenv("ASKOZ_CRAWL_CONTACT_URL", "https://github.com/x/askoz")
    monkeypatch.setenv("ASKOZ_CRAWL_CONTACT_EMAIL", "not-an-email")
    with pytest.raises(ValidationError, match="crawl_contact_email"):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_empty_crawl_contact_means_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKOZ_CRAWL_CONTACT_URL", "")
    assert Settings(_env_file=None).crawl_contact_url is None  # pyright: ignore[reportCallIssue]
