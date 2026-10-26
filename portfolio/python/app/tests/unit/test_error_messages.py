"""Only DomainError messages reach API clients; anything else becomes a fixed text."""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.auth.dependencies import get_optional_current_user
from core.domain.positions import OversellError
from core.domain.valuation import MissingPriceError
from core.errors import DomainError, NotFoundError, public_message
from core.services.enhanced_statistical_service import EnhancedStatisticalService
from main import app

APP = Path(__file__).resolve().parents[2]


def _leaks(path: Path):
    tree = ast.parse(path.read_text())
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler) or not handler.name:
            continue
        for node in ast.walk(handler):
            if not (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", getattr(node.func, "attr", ""))
                == "HTTPException"
            ):
                continue
            detail = next((k.value for k in node.keywords if k.arg == "detail"), None)
            safe = (
                isinstance(detail, ast.Call)
                and getattr(detail.func, "id", "") == "public_message"
            )
            if (
                detail is not None
                and not safe
                and any(
                    isinstance(n, ast.Name) and n.id == handler.name
                    for n in ast.walk(detail)
                )
            ):
                yield f"{path.relative_to(APP)}:{node.lineno}"


def test_no_http_error_detail_embeds_the_caught_exception():
    files = [*(APP / "api").rglob("*.py"), APP / "main.py", APP / "health_check.py"]
    assert [leak for path in files for leak in _leaks(path)] == []


def test_domain_errors_keep_their_message_and_others_get_the_fallback():
    assert (
        public_message(DomainError("Portfolio has no assets"), "x")
        == "Portfolio has no assets"
    )
    assert (
        public_message(NotFoundError("Asset 3 not found"), "x") == "Asset 3 not found"
    )
    assert public_message(OversellError("Cannot sell 5"), "x") == "Cannot sell 5"
    assert (
        public_message(MissingPriceError("No price for AAA"), "x") == "No price for AAA"
    )
    assert (
        public_message(ValueError("invalid literal for int()"), "Bad input")
        == "Bad input"
    )
    assert public_message(KeyError("secret"), "Failed") == "Failed"


def test_domain_errors_are_still_value_errors():
    with pytest.raises(ValueError):
        raise NotFoundError("gone")


def test_internal_error_text_never_reaches_the_client(client, monkeypatch):
    async def broken(self):
        raise RuntimeError("connection to db at 10.0.0.5:5432 refused")

    monkeypatch.setattr(EnhancedStatisticalService, "get_available_indicators", broken)
    app.dependency_overrides[get_optional_current_user] = lambda: None

    with TestClient(app, raise_server_exceptions=False) as quiet:
        response = quiet.get("/api/v1/statistical-indicators/indicators")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Something went wrong"
    assert "10.0.0.5" not in response.text


def test_domain_error_text_reaches_the_client(client, monkeypatch):
    async def missing(self, request, user_id=None):
        raise DomainError("No market data found for symbol ZZZZ")

    monkeypatch.setattr(EnhancedStatisticalService, "calculate_indicators", missing)
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.post(
        "/api/v1/statistical-indicators/calculate",
        json={"symbol": "ZZZZ"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "bad_request",
        "message": "No market data found for symbol ZZZZ",
    }


def test_not_found_is_404_and_bad_input_is_400(client, test_db):
    from core.auth.dependencies import get_current_user
    from core.database.models import Portfolio, User

    user = User(email="err@example.com", username="err", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P")
    test_db.add(portfolio)
    test_db.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    base = "/api/v1/portfolios/calculations/portfolio"

    missing = client.get(f"{base}/999999/performance?period=1y")
    bad_period = client.get(f"{base}/{portfolio.id}/performance?period=nonsense")

    assert (missing.status_code, missing.json()["error"]) == (
        404,
        {"code": "not_found", "message": "Portfolio 999999 not found"},
    )
    assert (bad_period.status_code, bad_period.json()["error"]) == (
        400,
        {"code": "bad_request", "message": "Unknown period type: nonsense"},
    )


def test_validation_errors_use_the_envelope(client):
    response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert "username" in body["message"]
    assert body["details"]
