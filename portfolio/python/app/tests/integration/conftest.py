import fakeredis
import pytest
from fastapi.testclient import TestClient

import api.v1.auth.router as auth_router
import core.database.redis_client as redis_client_module
from core.database.connection import get_db
from main import app


@pytest.fixture
def fake_redis(monkeypatch):
    """Route every RedisClient connection to one in-memory server."""
    fake = fakeredis.FakeRedis()

    class FakeConnection:
        def __init__(self, connection_pool):
            pass

        def __enter__(self):
            return fake

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        redis_client_module.RedisClient, "RedisContextManager", FakeConnection
    )
    return fake


@pytest.fixture
def sent_emails(monkeypatch):
    """Capture outgoing emails instead of sending them."""
    outbox = []
    monkeypatch.setattr(
        auth_router,
        "send_forgot_password_email",
        lambda recipient_email, reset_url: outbox.append(reset_url),
    )
    monkeypatch.setattr(
        auth_router, "send_verification_email", lambda *args, **kwargs: None
    )
    return outbox


@pytest.fixture
def api(test_db, fake_redis, sent_emails):
    def request_session():
        try:
            yield test_db
            test_db.commit()
        except Exception:
            test_db.rollback()
            raise

    app.dependency_overrides[get_db] = request_session
    # No context manager: skips the lifespan (it would initialise the real database)
    # https, so the client sends the Secure refresh cookie back
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides.clear()
