"""The public surface of the API: meta routes, auth flow, validation, symbol search."""

import pytest

from core.services.market_data_service import MarketDataService

PASSWORD = "TestPass123!"


def register(api, username, email=None, password=PASSWORD, **extra):
    return api.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email or f"{username}@example.com",
            "password": password,
            "confirm_password": password,
            **extra,
        },
    )


def login(api, username, password=PASSWORD):
    return api.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def error(response):
    body = response.json()
    assert set(body) >= {"error", "request_id"}
    return body["error"]


class TestMetaEndpoints:
    def test_root(self, api):
        response = api.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Welcome to Portfolia API"
        assert body["docs"] == "/docs"

    def test_liveness(self, api):
        response = api.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_api_v1_root(self, api):
        response = api.get("/api/v1/")
        assert response.status_code == 200
        assert response.json()["message"] == "Portfolia API v1"

    def test_openapi_lists_every_feature(self, api):
        paths = api.get("/openapi.json").json()["paths"]
        for prefix in (
            "/api/v1/auth/",
            "/api/v1/stock/",
            "/api/v1/statistical-indicators/",
            "/api/v1/portfolios",
            "/api/v1/watchlists",
        ):
            assert any(p.startswith(prefix) for p in paths), prefix


class TestRegistration:
    def test_success(self, api):
        response = register(api, "integration", email="Integration@Example.com")

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["username"] == "integration"
        assert body["email"] == "integration@example.com"
        assert body["is_active"] is True
        assert body["is_verified"] is False
        assert {"id", "created_at", "updated_at"} <= set(body)
        assert "password_hash" not in body

    def test_duplicate_username(self, api):
        assert register(api, "dupe", email="one@example.com").status_code == 201

        response = register(api, "dupe", email="two@example.com")

        assert response.status_code == 400
        assert error(response) == {
            "code": "bad_request",
            "message": "Username already taken",
        }

    def test_duplicate_email(self, api):
        assert register(api, "first", email="same@example.com").status_code == 201

        response = register(api, "second", email="same@example.com")

        assert response.status_code == 400
        assert error(response)["message"] == "Email already registered"

    def test_missing_confirm_password(self, api):
        response = api.post(
            "/api/v1/auth/register",
            json={
                "username": "missing",
                "email": "m@example.com",
                "password": PASSWORD,
            },
        )

        assert response.status_code == 422
        body = error(response)
        assert body["code"] == "validation_error"
        assert "confirm_password" in body["message"]

    def test_empty_body(self, api):
        response = api.post("/api/v1/auth/register", json={})
        assert response.status_code == 422
        assert error(response)["code"] == "validation_error"

    def test_short_password(self, api):
        response = register(api, "shortpw", password="123")
        assert response.status_code == 422
        assert "password" in error(response)["message"]

    def test_weak_password(self, api):
        response = register(api, "weakpw", password="alllowercase")
        assert response.status_code == 400
        assert (
            error(response)["message"] == "Password does not meet security requirements"
        )

    def test_username_must_be_alphanumeric(self, api):
        response = register(api, "invalid user")
        assert response.status_code == 422
        assert "username" in error(response)["message"]


class TestLoginAndSession:
    def test_login_returns_an_access_token_and_a_refresh_cookie(self, api):
        register(api, "loginuser")

        response = login(api, "loginuser")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["access_token"] and "refresh_token" not in body
        assert api.cookies.get("portfolia_refresh")
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_needs_a_username(self, api):
        response = api.post(
            "/api/v1/auth/login",
            json={"email": "loginuser@example.com", "password": PASSWORD},
        )
        assert response.status_code == 422
        assert "username" in error(response)["message"]

    def test_login_with_empty_body(self, api):
        assert api.post("/api/v1/auth/login", json={}).status_code == 422

    def test_invalid_credentials(self, api):
        response = login(api, "nobody", "wrongpassword")
        assert response.status_code == 401
        assert error(response)["message"] == "Incorrect username or password"

    def test_me_with_and_without_token(self, api):
        register(api, "meuser")
        token = login(api, "meuser").json()["access_token"]

        response = api.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "meuser"

        response = api.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert error(response)["code"] == "unauthorized"

    def test_logout(self, api):
        register(api, "logoutuser")
        token = login(api, "logoutuser").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = api.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"
        assert api.get("/api/v1/auth/me", headers=headers).status_code == 401

    def test_forgot_password_does_not_reveal_unknown_emails(self, api, sent_emails):
        response = api.post(
            "/api/v1/auth/forgot-password", json={"email": "unknown@example.com"}
        )

        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]
        assert sent_emails == []


class TestMarketEndpoints:
    def test_symbol_search(self, api, monkeypatch):
        async def search_quotes(self, query):
            return [{"symbol": "AAPL", "short_name": "Apple", "quote_type": "EQUITY"}]

        monkeypatch.setattr(MarketDataService, "search_quotes", search_quotes)

        response = api.get("/api/v1/stock/symbols", params={"name": "apple"})

        assert response.status_code == 200
        assert response.json()[0]["symbol"] == "AAPL"
        assert response.json()[0]["quote_type"] == "EQUITY"

    def test_symbol_search_without_results(self, api, monkeypatch):
        async def search_quotes(self, query):
            return []

        monkeypatch.setattr(MarketDataService, "search_quotes", search_quotes)

        response = api.get("/api/v1/stock/symbols", params={"name": "zzzz"})

        assert response.status_code == 404
        assert error(response)["message"] == "No symbols found"

    def test_symbol_search_needs_a_name(self, api):
        response = api.get("/api/v1/stock/symbols")
        assert response.status_code == 422
        assert "name" in error(response)["message"]


class TestStatisticalIndicators:
    def test_rsi_is_registered(self, api):
        response = api.get("/api/v1/statistical-indicators/indicators")

        assert response.status_code == 200
        names = [i["name"] for i in response.json()["indicators"]]
        assert "rsi_indicator" in names

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"symbol": "AAPL"},
            {"indicators": [{"indicator_name": "rsi_indicator", "parameters": {}}]},
        ],
    )
    def test_calculate_requires_symbol_and_indicators(self, api, payload):
        response = api.post("/api/v1/statistical-indicators/calculate", json=payload)
        assert response.status_code == 422
        assert error(response)["code"] == "validation_error"
