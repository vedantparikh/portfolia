"""The cached PortfolioAsset position is rebuilt from transactions in today's share units."""

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
from modules.portfolios.service import PortfolioService


def _history(splits):
    return {
        "close": pd.Series([100.0], index=pd.to_datetime(["2025-01-02"])),
        "splits": pd.Series(
            list(splits.values()), index=pd.to_datetime(list(splits)), dtype=float
        ),
        "dividends": pd.Series(dtype=float),
    }


@pytest.fixture
def setup(test_db, monkeypatch):
    user = User(email="split@example.com", username="split", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P")
    asset = Asset(
        symbol="SPLT", name="Split Co", asset_type=AssetType.EQUITY, user_id=user.id
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fees=Decimal("5"),
            total_amount=Decimal("1005"),
            transaction_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )
    )
    test_db.commit()

    service = PortfolioService(test_db)
    state = {"splits": {}}

    async def price(symbol):
        return 55.0

    async def history(symbol):
        return _history(state["splits"])

    monkeypatch.setattr(service.market_data_service, "get_current_price", price)
    monkeypatch.setattr(service.market_data_service, "get_daily_history", history)
    return service, portfolio, asset, state


@pytest.mark.asyncio
async def test_buy_before_a_split_is_held_in_post_split_shares(setup):
    service, portfolio, asset, state = setup
    state["splits"] = {"2025-06-01": 2.0}
    pa = await service.recalculate_asset_state(portfolio.id, asset.id)
    assert pa.quantity == 20
    assert pa.cost_basis_total == Decimal("1005")
    assert pa.current_value == Decimal("1100")


@pytest.mark.asyncio
async def test_refresh_applies_a_split_after_the_last_trade(setup):
    service, portfolio, asset, state = setup
    await service.recalculate_asset_state(portfolio.id, asset.id)
    state["splits"] = {"2025-06-01": 2.0}
    assert await service.refresh_portfolio_values(portfolio.id, portfolio.user_id)
    pa = (
        service.db.query(PortfolioAsset)
        .filter_by(portfolio_id=portfolio.id, asset_id=asset.id)
        .one()
    )
    assert pa.quantity == 20
