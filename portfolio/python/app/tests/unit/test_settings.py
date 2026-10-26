"""Settings collapse the duplicate auth keys and honor refresh-token days."""

import pytest

from config import Settings


def _settings(monkeypatch, **env):
    for key in (
        "JWT_SECRET_KEY",
        "SECRET_KEY",
        "JWT_ALGORITHM",
        "ALGORITHM",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "REFRESH_TOKEN_EXPIRE_MINUTES",
        "ALLOWED_ORIGINS",
        "FRONTEND_URL",
        "TESTING",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


def test_jwt_secret_wins_when_both_are_set(monkeypatch):
    settings = _settings(
        monkeypatch,
        JWT_SECRET_KEY="j" * 40,
        SECRET_KEY="s" * 40,
    )
    assert settings.SECRET_KEY == "j" * 40
    assert settings.JWT_SECRET_KEY == settings.SECRET_KEY


def test_secret_key_is_used_when_jwt_secret_is_absent(monkeypatch):
    settings = _settings(monkeypatch, SECRET_KEY="s" * 40)
    assert settings.SECRET_KEY == "s" * 40


def test_algorithm_alias(monkeypatch):
    settings = _settings(monkeypatch, ALGORITHM="HS512")
    assert settings.JWT_ALGORITHM == "HS512"


def test_refresh_days_become_minutes(monkeypatch):
    settings = _settings(monkeypatch, REFRESH_TOKEN_EXPIRE_DAYS="7")
    assert settings.REFRESH_TOKEN_EXPIRE_MINUTES == 7 * 24 * 60


def test_refresh_minutes_override_days(monkeypatch):
    settings = _settings(
        monkeypatch,
        REFRESH_TOKEN_EXPIRE_DAYS="7",
        REFRESH_TOKEN_EXPIRE_MINUTES="30",
    )
    assert settings.REFRESH_TOKEN_EXPIRE_MINUTES == 30


def test_origins_default_to_the_frontend(monkeypatch):
    settings = _settings(monkeypatch, FRONTEND_URL="http://localhost:3200")
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3200"]


def test_origins_split_on_commas(monkeypatch):
    settings = _settings(
        monkeypatch,
        ALLOWED_ORIGINS="http://a.example, http://b.example",
    )
    assert settings.ALLOWED_ORIGINS == ["http://a.example", "http://b.example"]


def test_production_rejects_a_short_secret(monkeypatch):
    settings = _settings(
        monkeypatch,
        ENVIRONMENT="production",
        TESTING="false",
        JWT_SECRET_KEY="short",
        POSTGRES_PASSWORD="not-a-placeholder-password",
        REDIS_PASSWORD="redis-secret",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.validate_secrets()
