"""Stored snapshots and the analytics summary read the engine, in percent."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from core.database.models import Asset, Portfolio, Transaction, TransactionType, User
from core.database.models.asset import AssetType
from core.database.models.portfolio_analytics import PortfolioPerformanceHistory
from core.domain.valuation import MissingPriceError
from core.services.market_data_service import MarketDataService
from modules.analytics.service import PortfolioAnalyticsService


@pytest.fixture
def portfolio(test_db):
    user = User(email="snap@example.com", username="snap", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="Snap", currency="EUR")
    asset = Asset(
        symbol="SNP", name="Snap", asset_type=AssetType.EQUITY, user_id=user.id
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    bought = datetime.now(timezone.utc) - timedelta(days=10)
    for days, amount in ((10, "1000"), (5, "1100")):
        test_db.add(
            Transaction(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                transaction_type=TransactionType.BUY,
                quantity=Decimal("10"),
                price=Decimal(amount) / 10,
                total_amount=Decimal(amount),
                currency="EUR",
                transaction_date=datetime.now(timezone.utc) - timedelta(days=days),
            )
        )
    asset.currency = "EUR"
    test_db.commit()
    return portfolio, bought


def _prices(monkeypatch, closes):
    async def history(self, symbol):
        return {
            "close": closes,
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    monkeypatch.setattr(MarketDataService, "get_daily_history", history)


@pytest.mark.asyncio
async def test_snapshot_does_not_count_a_deposit_as_return(
    test_db, monkeypatch, portfolio
):
    book, bought = portfolio
    days = pd.date_range(bought.date(), periods=11, freq="D")
    # 100, then 110 the day before the second buy: only the first lot gains.
    closes = pd.Series([100.0] * 4 + [110.0] * 7, index=days)
    _prices(monkeypatch, closes)

    await PortfolioAnalyticsService(test_db).create_performance_snapshot(book.id)

    row = test_db.query(PortfolioPerformanceHistory).one()
    assert float(row.total_value) == pytest.approx(2200)
    assert float(row.total_cost_basis) == pytest.approx(2100)
    assert float(row.total_unrealized_pnl_percent) == pytest.approx(100 / 21, abs=1e-4)
    # Value doubled because of the deposit; the time-weighted return is 10%.
    assert float(row.cumulative_return) == pytest.approx(10)
    assert row.annualized_return is None


@pytest.mark.asyncio
async def test_summary_and_dashboard_use_the_engine(test_db, monkeypatch, portfolio):
    book, bought = portfolio
    days = pd.date_range(bought.date(), periods=11, freq="D")
    _prices(monkeypatch, pd.Series([100.0] * 4 + [110.0] * 7, index=days))
    service = PortfolioAnalyticsService(test_db)

    summary = await service.get_portfolio_analytics_summary(book.id)
    assert summary["currency"] == "EUR"
    assert float(summary["total_return"]) == pytest.approx(10)

    dashboard = await service.get_analytics_dashboard_summary(book.user_id)
    assert dashboard["portfolios"]["totals"] == [
        {"currency": "EUR", "total_value": 2200.0, "total_unrealized_pnl": 100.0}
    ]


@pytest.mark.asyncio
async def test_missing_price_is_not_valued_at_cost(test_db, monkeypatch, portfolio):
    book, _ = portfolio
    _prices(monkeypatch, pd.Series(dtype=float))
    with pytest.raises(MissingPriceError):
        await PortfolioAnalyticsService(test_db).create_performance_snapshot(book.id)
    assert test_db.query(PortfolioPerformanceHistory).count() == 0
