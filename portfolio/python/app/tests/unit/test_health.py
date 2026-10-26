"""Liveness ignores dependencies. Readiness is 503 when Postgres or Redis is down."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

HARDCODED = "2024-01-15T10:30:00Z"


def test_live_does_not_check_dependencies(client, monkeypatch):
    async def boom():
        raise AssertionError("live must not check dependencies")

    monkeypatch.setattr("health_check.get_db_health", boom)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("database", "redis_status", "status_code"),
    [
        ("healthy", "healthy", 200),
        ("unhealthy", "healthy", 503),
        ("healthy", "unhealthy", 503),
    ],
)
def test_ready_reflects_postgres_and_redis(
    client, monkeypatch, database, redis_status, status_code
):
    async def report():
        return {
            "database": database,
            "redis": redis_status,
            "overall": "ignored",
        }

    monkeypatch.setattr("health_check.get_db_health", report)
    expected = "healthy" if status_code == 200 else "unhealthy"
    for path in ("/health/ready", "/health/"):
        response = client.get(path)
        body = response.json()
        assert response.status_code == status_code
        assert body["status"] == expected
        assert body["database"] == database
        assert body["redis"] == redis_status
        assert "error" not in body
        parsed = datetime.strptime(body["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        assert body["timestamp"] != HARDCODED
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5


def test_the_test_router_is_gone(client):
    assert client.get("/api/v1/health").status_code == 404


def test_health_source_has_no_hardcoded_timestamp():
    source = Path(__file__).resolve().parents[2].joinpath("health_check.py").read_text()
    assert HARDCODED not in source
