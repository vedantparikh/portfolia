"""GET .../performance/series: points and summary come from one engine run."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from core.database.models import Asset, Portfolio, Transaction, TransactionType, User
from core.database.models.asset import AssetType
from modules.analytics.calculations import PortfolioCalculationService


@pytest.fixture
def portfolio(test_db):
    user = User(email="series@example.com", username="series", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P")
    asset = Asset(
        symbol="SER", name="Series", asset_type=AssetType.EQUITY, user_id=user.id
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    bought = datetime.now(timezone.utc) - timedelta(days=20)
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            total_amount=Decimal("1000"),
            transaction_date=bought,
        )
    )
    test_db.commit()
    return portfolio


def _service(test_db, monkeypatch, closes):
    service = PortfolioCalculationService(test_db)

    async def history(symbol):
        return {
            "close": closes,
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    monkeypatch.setattr(service.market_data_service, "get_daily_history", history)
    return service


def _closes(start: date, values):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)))


@pytest.mark.asyncio
async def test_inception_series_and_summary(test_db, monkeypatch, portfolio):
    start = (datetime.now(timezone.utc) - timedelta(days=20)).date()
    service = _service(test_db, monkeypatch, _closes(start, [100, 110, 121]))
    result = await service.get_performance_series(
        portfolio.id, portfolio.user_id, "inception"
    )

    assert [p["value"] for p in result["points"]] == [1000, 1100, 1210]
    assert result["points"][0]["stale_price"] is False
    assert result["points"][0]["stale_symbols"] == []
    assert {p["invested"] for p in result["points"]} == {1000}
    summary = result["summary"]
    assert summary["profit"] == pytest.approx(210)
    assert summary["twr_pct"] == pytest.approx(21)
    assert summary["max_drawdown_pct"] == 0


@pytest.mark.asyncio
async def test_missing_price_is_reported_not_valued_at_cost(
    test_db, monkeypatch, portfolio
):
    service = _service(test_db, monkeypatch, pd.Series(dtype=float))
    result = await service.get_performance_series(
        portfolio.id, portfolio.user_id, "inception"
    )
    assert result["points"] == []
    assert result["error"]


@pytest.mark.asyncio
async def test_other_users_portfolio_is_not_found(test_db, monkeypatch, portfolio):
    service = _service(test_db, monkeypatch, pd.Series(dtype=float))
    with pytest.raises(ValueError):
        await service.get_performance_series(portfolio.id, portfolio.user_id + 1, "1y")
