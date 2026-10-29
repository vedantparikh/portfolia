"""Route order and the two endpoints that used to 500."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from api.v1.analytics.router import get_user_analytics_dashboard
from api.v1.portfolio_calculations.router import get_portfolio_performance_overview
from core.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    get_current_verified_user,
    get_optional_current_user,
)
from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionType,
    User,
)
from core.database.models.asset import AssetType
from main import app
from modules.analytics.calculations import PortfolioCalculationService


@pytest.fixture
def portfolio(test_db):
    user = User(email="routes@example.com", username="routes", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P")
    asset = Asset(
        symbol="RTE", name="Route", asset_type=AssetType.EQUITY, user_id=user.id
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    test_db.add(
        PortfolioAsset(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            quantity=Decimal("10"),
            cost_basis=Decimal("100"),
            cost_basis_total=Decimal("1000"),
        )
    )
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            total_amount=Decimal("1000"),
            transaction_date=datetime.now(timezone.utc) - timedelta(days=20),
        )
    )
    test_db.commit()
    return portfolio


def _login_as(user):
    for dependency in (
        get_current_user,
        get_current_active_user,
        get_current_verified_user,
        get_optional_current_user,
    ):
        app.dependency_overrides[dependency] = lambda: user


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/assets/search/popular",
        "/api/v1/assets/search/suggestions?q=AA",
        "/api/v1/watchlists/public",
        "/api/v1/watchlists/stats",
        "/api/v1/statistical-indicators/configurations/search?q=a",
    ],
)
def test_literal_route_is_not_shadowed_by_an_id_route(client, portfolio, path):
    _login_as(portfolio.user)

    assert client.get(path).status_code == 200


def test_asset_search_only_sees_own_assets(client, test_db, portfolio):
    other = User(email="other@example.com", username="other", password_hash="x")
    test_db.add(other)
    test_db.commit()
    _login_as(other)

    own_asset_id = portfolio.user.assets[0].id
    assert client.get(f"/api/v1/assets/search/{own_asset_id}").status_code == 404
    assert client.get("/api/v1/assets/search/popular").json() == {"assets": []}
    assert client.get("/api/v1/assets/search/suggestions?q=RT").json() == {
        "suggestions": []
    }

    _login_as(portfolio.user)
    assert [
        a["symbol"]
        for a in client.get("/api/v1/assets/search/popular").json()["assets"]
    ] == ["RTE"]


@pytest.mark.asyncio
async def test_overview_uses_the_engine_value(test_db, monkeypatch, portfolio):
    async def performance(self, portfolio_id, user_id, period):
        return {"current_value": 1210.0, "metrics": {"twr": 21.0, "cagr": 21.0}}

    monkeypatch.setattr(
        PortfolioCalculationService, "calculate_portfolio_performance", performance
    )
    overview = await get_portfolio_performance_overview(
        portfolio.id, db=test_db, current_user=portfolio.user
    )

    assert overview.portfolio_summary.current_value == 1210.0
    assert overview.portfolio_summary.total_return == 21.0


@pytest.mark.asyncio
async def test_user_dashboard_responds(test_db, portfolio):
    dashboard = await get_user_analytics_dashboard(
        force_refresh=False, current_user=portfolio.user, db=test_db
    )

    assert dashboard["user_id"] == portfolio.user_id
    assert dashboard["portfolios"]["total_count"] == 1
