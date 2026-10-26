"""
Integration tests for authentication, session revocation, rate limiting and
cross-user authorization.

Runs the real FastAPI app against in-memory SQLite and an in-memory fake Redis.
Email sending and market data are stubbed; nothing touches the network.
"""

from datetime import datetime, timezone
from decimal import Decimal

import fakeredis
import pytest
from fastapi.testclient import TestClient

import api.v1.auth.router as auth_router
import core.database.redis_client as redis_client_module
from core.auth.utils import DUMMY_PASSWORD_HASH, hash_refresh_token
from core.database.connection import get_db
from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    User,
    UserSession,
)
from core.services.market_data_service import MarketDataService
from main import app

STRONG_PASSWORD = "Str0ng!Passw0rd"


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


@pytest.fixture(autouse=True)
def stub_prices(monkeypatch):
    # A float, exactly like the real service returns
    async def fake_price(self, symbol):
        return 110.0

    monkeypatch.setattr(MarketDataService, "get_current_price", fake_price)


@pytest.fixture
def api(test_db, fake_redis, sent_emails):
    app.dependency_overrides[get_db] = lambda: test_db
    # No context manager: skips the lifespan (it would initialise the real database)
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_and_login(api, db, username):
    response = api.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": STRONG_PASSWORD,
            "confirm_password": STRONG_PASSWORD,
            "first_name": username,
            "last_name": "Test",
        },
    )
    assert response.status_code == 201, response.text
    user = db.query(User).filter(User.username == username).one()
    user.is_verified = True
    db.commit()
    return user, login(api, username)


def login(api, username, password=STRONG_PASSWORD):
    response = api.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def create_portfolio_with_asset(db, user, symbol):
    portfolio = Portfolio(name=f"{user.username} portfolio", user_id=user.id)
    asset = Asset(symbol=symbol, name=symbol, asset_type="EQUITY", user_id=user.id)
    db.add_all([portfolio, asset])
    db.commit()
    return portfolio, asset


def transaction_payload(portfolio_id, asset_id, kind="buy", quantity="10", price="100"):
    return {
        "portfolio_id": portfolio_id,
        "asset_id": asset_id,
        "transaction_type": kind,
        "quantity": quantity,
        "price": price,
        "fees": "5",
        "transaction_date": datetime(2025, 1, 2, tzinfo=timezone.utc).isoformat(),
    }


class TestPasswordReset:
    def test_forgot_password_does_not_leak_reset_link(self, api, test_db, sent_emails):
        register_and_login(api, test_db, "alice")

        response = api.post(
            "/api/v1/auth/forgot-password", json={"email": "alice@example.com"}
        )

        assert response.status_code == 200
        assert "reset_url" not in response.json()
        assert len(sent_emails) == 1  # the link only goes to the user's inbox

    def test_reset_token_is_single_use_and_revokes_sessions(
        self, api, test_db, sent_emails
    ):
        _, tokens = register_and_login(api, test_db, "alice")
        api.post("/api/v1/auth/forgot-password", json={"email": "alice@example.com"})
        token = sent_emails[0].split("token=")[1]
        new_password = "N3w!Passw0rdX"
        body = {
            "token": token,
            "new_password": new_password,
            "confirm_new_password": new_password,
        }

        assert api.post("/api/v1/auth/reset-password", json=body).status_code == 200
        assert api.post("/api/v1/auth/reset-password", json=body).status_code == 400
        # The session from before the reset no longer works
        assert api.get("/api/v1/auth/me", headers=auth(tokens)).status_code == 401
        login(api, "alice", new_password)

    def test_weak_password_rejected_without_burning_token(
        self, api, test_db, sent_emails
    ):
        register_and_login(api, test_db, "alice")
        api.post("/api/v1/auth/forgot-password", json={"email": "alice@example.com"})
        token = sent_emails[0].split("token=")[1]

        weak = {
            "token": token,
            "new_password": "password",
            "confirm_new_password": "password",
        }
        assert api.post("/api/v1/auth/reset-password", json=weak).status_code == 400

        strong = "N3w!Passw0rdX"
        ok = {"token": token, "new_password": strong, "confirm_new_password": strong}
        assert api.post("/api/v1/auth/reset-password", json=ok).status_code == 200


class TestSessions:
    def test_unknown_username_still_checks_a_password(self, api, monkeypatch):
        seen = []
        real = auth_router.verify_password

        def spy(plain, hashed):
            seen.append(hashed)
            return real(plain, hashed)

        monkeypatch.setattr(auth_router, "verify_password", spy)
        response = api.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": STRONG_PASSWORD},
        )
        assert response.status_code == 401
        assert seen == [DUMMY_PASSWORD_HASH]

    def test_refresh_token_is_stored_as_a_hash(self, api, test_db):
        user, tokens = register_and_login(api, test_db, "alice")
        stored = (
            test_db.query(UserSession)
            .filter(UserSession.user_id == user.id)
            .one()
            .refresh_token
        )
        assert stored == hash_refresh_token(tokens["refresh_token"])
        assert stored != tokens["refresh_token"]

    def test_refresh_rotates_and_detects_reuse(self, api, test_db):
        _, tokens = register_and_login(api, test_db, "alice")

        first = api.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert first.status_code == 200
        rotated = first.json()
        assert rotated["refresh_token"] != tokens["refresh_token"]

        # Replaying the old refresh token is rejected and kills the session
        replay = api.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert replay.status_code == 401
        assert api.get("/api/v1/auth/me", headers=auth(rotated)).status_code == 401

    def test_access_token_cannot_be_used_to_refresh(self, api, test_db):
        _, tokens = register_and_login(api, test_db, "alice")
        response = api.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )
        assert response.status_code == 401

    def test_logout_revokes_the_session(self, api, test_db):
        _, tokens = register_and_login(api, test_db, "alice")
        assert api.post("/api/v1/auth/logout", headers=auth(tokens)).status_code == 200
        assert api.get("/api/v1/auth/me", headers=auth(tokens)).status_code == 401
        refresh = api.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh.status_code == 401

    def test_change_password_keeps_current_session_only(self, api, test_db):
        _, current = register_and_login(api, test_db, "alice")
        other = login(api, "alice")

        response = api.post(
            "/api/v1/auth/change-password",
            headers=auth(current),
            json={
                "current_password": STRONG_PASSWORD,
                "new_password": "N3w!Passw0rdX",
                "confirm_new_password": "N3w!Passw0rdX",
            },
        )

        assert response.status_code == 200, response.text
        assert api.get("/api/v1/auth/me", headers=auth(current)).status_code == 200
        assert api.get("/api/v1/auth/me", headers=auth(other)).status_code == 401


class TestRateLimiting:
    def test_login_is_rate_limited_per_username(self, api, test_db):
        register_and_login(api, test_db, "alice")  # one successful attempt
        statuses = [
            api.post(
                "/api/v1/auth/login", json={"username": "alice", "password": "wrong"}
            ).status_code
            for _ in range(auth_router.LOGIN_MAX_ATTEMPTS)
        ]
        assert statuses[-1] == 429
        assert set(statuses[:-1]) == {401}


class TestCrossUserAuthorization:
    def test_cannot_read_another_users_holdings(self, api, test_db):
        alice, _ = register_and_login(api, test_db, "alice")
        _, mallory_tokens = register_and_login(api, test_db, "mallory")
        portfolio, _ = create_portfolio_with_asset(test_db, alice, "AAPL")

        response = api.get(
            f"/api/v1/portfolios/{portfolio.id}/holdings", headers=auth(mallory_tokens)
        )
        assert response.status_code == 404

    def test_body_portfolio_id_cannot_redirect_a_transaction(self, api, test_db):
        alice, _ = register_and_login(api, test_db, "alice")
        mallory, mallory_tokens = register_and_login(api, test_db, "mallory")
        victim_portfolio, _ = create_portfolio_with_asset(test_db, alice, "AAPL")
        own_portfolio, own_asset = create_portfolio_with_asset(test_db, mallory, "MSFT")

        response = api.post(
            f"/api/v1/portfolios/{own_portfolio.id}/transactions",
            headers=auth(mallory_tokens),
            json=transaction_payload(victim_portfolio.id, own_asset.id),
        )

        assert response.status_code == 201, response.text
        assert response.json()["portfolio_id"] == own_portfolio.id
        assert (
            test_db.query(Transaction)
            .filter(Transaction.portfolio_id == victim_portfolio.id)
            .count()
            == 0
        )

    def test_cannot_trade_another_users_asset(self, api, test_db):
        alice, _ = register_and_login(api, test_db, "alice")
        mallory, mallory_tokens = register_and_login(api, test_db, "mallory")
        _, alice_asset = create_portfolio_with_asset(test_db, alice, "AAPL")
        own_portfolio, _ = create_portfolio_with_asset(test_db, mallory, "MSFT")

        response = api.post(
            f"/api/v1/portfolios/{own_portfolio.id}/transactions",
            headers=auth(mallory_tokens),
            json=transaction_payload(own_portfolio.id, alice_asset.id),
        )
        assert response.status_code == 404


class TestTransactionWrites:
    def test_buy_computes_total_with_fees_and_values_position(self, api, test_db):
        alice, tokens = register_and_login(api, test_db, "alice")
        portfolio, asset = create_portfolio_with_asset(test_db, alice, "AAPL")

        response = api.post(
            f"/api/v1/portfolios/{portfolio.id}/transactions",
            headers=auth(tokens),
            json={**transaction_payload(portfolio.id, asset.id), "total_amount": "1"},
        )

        assert response.status_code == 201, response.text
        assert Decimal(response.json()["total_amount"]) == Decimal("1005")
        position = test_db.query(PortfolioAsset).one()
        assert position.cost_basis_total == Decimal("1005")
        # Float price * Decimal quantity used to crash and wipe these to None
        assert position.current_value == Decimal("1100")
        assert position.unrealized_pnl == Decimal("95")

    def test_oversell_is_rejected_and_nothing_is_saved(self, api, test_db):
        alice, tokens = register_and_login(api, test_db, "alice")
        portfolio, asset = create_portfolio_with_asset(test_db, alice, "AAPL")
        url = f"/api/v1/portfolios/{portfolio.id}/transactions"
        api.post(
            url, headers=auth(tokens), json=transaction_payload(portfolio.id, asset.id)
        )

        response = api.post(
            url,
            headers=auth(tokens),
            json=transaction_payload(
                portfolio.id, asset.id, kind="sell", quantity="11"
            ),
        )

        assert response.status_code == 400
        assert test_db.query(Transaction).count() == 1
        assert test_db.query(PortfolioAsset).one().quantity == Decimal("10")
