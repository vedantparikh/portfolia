"""`python -m portfolia recalc` rebuilds every holding, realized P&L before tax."""

import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
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
from core.services.market_data_service import MarketDataService


def test_module_imports_on_its_own():
    result = subprocess.run(
        [sys.executable, "-c", "import portfolia"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_recalc_rebuilds_holdings(test_db, monkeypatch):
    from portfolia import recalc

    user = User(email="recalc@example.com", username="recalc", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="R", currency="EUR")
    asset = Asset(
        symbol="RC",
        name="R",
        asset_type=AssetType.EQUITY,
        user_id=user.id,
        currency="EUR",
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    for kind, qty, price, fees, taxes, total, day in (
        (TransactionType.BUY, 10, 100, 1, 0, 1001, 2),
        (TransactionType.SELL, 10, 150, 1, 100, 1399, 5),
    ):
        test_db.add(
            Transaction(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                transaction_type=kind,
                quantity=Decimal(qty),
                price=Decimal(price),
                fees=Decimal(fees),
                taxes=Decimal(taxes),
                total_amount=Decimal(total),
                currency="EUR",
                transaction_date=datetime(2025, 1, day, tzinfo=timezone.utc),
            )
        )
    test_db.commit()

    async def history(self, symbol):
        return {
            "close": pd.Series(dtype=float),
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    async def price(self, symbol):
        return None

    monkeypatch.setattr(MarketDataService, "get_daily_history", history)
    monkeypatch.setattr(MarketDataService, "get_current_price", price)

    assert await recalc(test_db) == 1
    holding = test_db.query(PortfolioAsset).one()
    assert holding.quantity == 0
    # 1500 - 1 fee - 1001 cost; the 100 tax withheld is not a loss
    assert holding.realized_pnl == Decimal("498")
