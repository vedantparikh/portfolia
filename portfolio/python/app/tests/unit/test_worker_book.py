"""The worker refreshes holdings and writes snapshots. Requests do not."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionType,
    User,
)
from core.database.models.asset import AssetType
from core.database.models.portfolio_analytics import PortfolioPerformanceHistory
from modules.analytics.service import PortfolioAnalyticsService
from workers.book import refresh_book, snapshot_due


def test_snapshot_is_due_after_a_trade_and_after_the_close():
    morning = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)
    trade = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)
    close = datetime(2026, 10, 27, 22, 5, tzinfo=timezone.utc)
    stored = datetime(2026, 10, 27, 22, 6, tzinfo=timezone.utc)

    assert snapshot_due(trade, None, morning)
    assert not snapshot_due(None, None, morning)
    assert snapshot_due(None, None, close)
    assert snapshot_due(None, morning, close)
    assert not snapshot_due(trade, stored, close)
    assert snapshot_due(
        datetime(2026, 10, 27, 22, 10, tzinfo=timezone.utc), stored, close
    )


class _Market:
    def __init__(self):
        self.refreshed = None
        self.history = []
        self.fx = []

    async def get_current_prices(self, symbols, *, fetch=True, refresh=False):
        self.refreshed = refresh
        return {symbol: Decimal("10") for symbol in symbols}

    async def get_yesterdays_closes(self, symbols, *, fetch=True):
        return {symbol: Decimal("9") for symbol in symbols}

    async def get_daily_history(self, symbol, *, fetch=True):
        self.history.append(symbol)
        return None

    async def get_fx_rates(self, quote, portfolio):
        self.fx.append((quote, portfolio))
        return None


def _book(db, when):
    user = User(email="book@example.com", username="book", password_hash="x")
    db.add(user)
    db.flush()
    portfolio = Portfolio(user_id=user.id, name="Book", currency="USD")
    asset = Asset(
        symbol="ACME",
        name="Acme",
        asset_type=AssetType.EQUITY,
        currency="EUR",
        user_id=user.id,
    )
    db.add_all([portfolio, asset])
    db.flush()
    db.add(
        PortfolioAsset(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            quantity=Decimal("1"),
            cost_basis=Decimal("10"),
            cost_basis_total=Decimal("10"),
        )
    )
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("1"),
            price=Decimal("10"),
            total_amount=Decimal("10"),
            transaction_date=when,
            updated_at=when,
        )
    )
    db.commit()
    return portfolio


@pytest.mark.asyncio
async def test_worker_refreshes_holdings_and_writes_a_snapshot(test_db, monkeypatch):
    when = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)
    portfolio = _book(test_db, when)
    written = []

    async def record(self, portfolio_id, snapshot_date=None):
        written.append(portfolio_id)

    monkeypatch.setattr(
        PortfolioAnalyticsService, "create_performance_snapshot", record
    )
    market = _Market()

    result = await refresh_book(test_db, market, when)

    assert result == {"holding_symbols": 1, "fx_pairs": 1, "snapshots": 1}
    assert market.refreshed is True
    assert market.history == ["ACME"]
    assert market.fx == [("EUR", "USD")]
    assert written == [portfolio.id]


@pytest.mark.asyncio
async def test_worker_skips_a_snapshot_already_taken_after_the_close(test_db):
    trade = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)
    portfolio = _book(test_db, trade)
    test_db.add(
        PortfolioPerformanceHistory(
            portfolio_id=portfolio.id,
            snapshot_date=datetime(2026, 10, 27, 22, 6, tzinfo=timezone.utc),
            total_value=Decimal("10"),
            total_cost_basis=Decimal("10"),
            total_unrealized_pnl=Decimal("0"),
            total_unrealized_pnl_percent=Decimal("0"),
            created_at=datetime(2026, 10, 27, 22, 6, tzinfo=timezone.utc),
        )
    )
    test_db.commit()
    market = _Market()

    result = await refresh_book(
        test_db,
        market,
        datetime(2026, 10, 27, 22, 30, tzinfo=timezone.utc),
    )

    assert result["snapshots"] == 0
    assert market.refreshed is True
