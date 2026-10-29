"""GET /assets/: paging total, database sorts and quote sorts."""

import pytest

from core.auth.dependencies import get_current_active_user
from core.database.models import Asset, User
from core.database.models.asset import AssetType
from core.services.market_data_service import market_data_service
from main import app

QUOTES = {
    "AAA": {"symbol": "AAA", "market_cap": 50},
    "BBB": {"symbol": "BBB", "market_cap": 300},
    "CCC": {"symbol": "CCC"},
    "DDD": {"symbol": "DDD", "market_cap": 120},
}


@pytest.fixture
def assets(test_db, monkeypatch):
    user = User(email="assets@example.com", username="assets", password_hash="x")
    other = User(email="other@example.com", username="other", password_hash="x")
    test_db.add_all([user, other])
    test_db.flush()
    for symbol, name in [
        ("CCC", "Charlie"),
        ("AAA", "Zulu"),
        ("DDD", "Alpha"),
        ("BBB", "Bravo"),
    ]:
        test_db.add(
            Asset(
                symbol=symbol, name=name, asset_type=AssetType.EQUITY, user_id=user.id
            )
        )
    test_db.add(
        Asset(symbol="EEE", name="Echo", asset_type=AssetType.EQUITY, user_id=other.id)
    )
    test_db.commit()

    async def symbols_info(symbols):
        return [QUOTES[s] for s in symbols if s in QUOTES]

    monkeypatch.setattr(market_data_service, "get_symbols_info", symbols_info)
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield
    app.dependency_overrides.pop(get_current_active_user, None)


def symbols(response):
    return [a["symbol"] for a in response.json()]


def test_pages_carry_the_total(client, assets):
    response = client.get("/api/v1/assets/?limit=2&skip=2")
    assert symbols(response) == ["CCC", "DDD"]
    assert response.headers["X-Total-Count"] == "4"


def test_sorts_by_a_column(client, assets):
    response = client.get("/api/v1/assets/?sort_by=name&sort_order=desc&limit=3")
    assert symbols(response) == ["AAA", "CCC", "BBB"]
    assert response.headers["X-Total-Count"] == "4"


def test_sorts_by_a_quote_field_with_missing_values_last(client, assets):
    response = client.get("/api/v1/assets/?sort_by=market_cap&sort_order=desc&limit=3")
    assert symbols(response) == ["BBB", "DDD", "AAA"]
    assert all(a["detail"] is None for a in response.json())
    assert response.headers["X-Total-Count"] == "4"

    response = client.get(
        "/api/v1/assets/?sort_by=market_cap&skip=2&include_detail=true"
    )
    assert symbols(response) == ["BBB", "CCC"]
    assert response.json()[0]["detail"]["market_cap"] == "300"


def test_assets_without_the_quote_field_stay_in_symbol_order(client, assets):
    response = client.get("/api/v1/assets/?sort_by=volume_24h&sort_order=desc")
    assert symbols(response) == ["AAA", "BBB", "CCC", "DDD"]


def test_rejects_an_unknown_sort(client, assets):
    assert client.get("/api/v1/assets/?sort_by=quantity").status_code == 422
