"""Portfolio summary = sum of live holdings; no cost-basis stand-in for missing prices."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from core.database.models import Asset, Portfolio, Transaction, TransactionType, User
from core.database.models.asset import AssetType
from modules.portfolios.service import PortfolioService


def _buy(portfolio, asset, qty, price, when):
    qty, price = Decimal(qty), Decimal(price)
    return Transaction(
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        transaction_type=TransactionType.BUY,
        quantity=qty,
        price=price,
        total_amount=qty * price,
        transaction_date=when,
    )


@pytest.fixture
def service(test_db, monkeypatch):
    user = User(email="sum@example.com", username="sum", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P")
    priced = Asset(
        symbol="PRC", name="Priced", asset_type=AssetType.EQUITY, user_id=user.id
    )
    unpriced = Asset(
        symbol="NOP", name="No price", asset_type=AssetType.EQUITY, user_id=user.id
    )
    test_db.add_all([portfolio, priced, unpriced])
    test_db.flush()
    now = datetime.now(timezone.utc)
    test_db.add_all(
        [
            _buy(portfolio, priced, 10, 80, now - timedelta(days=30)),
            _buy(portfolio, priced, 5, 104, now),
            _buy(portfolio, unpriced, 1, 500, now - timedelta(days=30)),
        ]
    )
    test_db.commit()

    service = PortfolioService(test_db)

    async def prices(symbols):
        return {"PRC": Decimal("105")}

    async def closes(symbols):
        return {"PRC": Decimal("100")}

    async def no_price(symbol):
        return None

    async def no_history(symbol):
        return {"close": pd.Series(dtype=float), "splits": pd.Series(dtype=float)}

    monkeypatch.setattr(service.market_data_service, "get_current_prices", prices)
    monkeypatch.setattr(service.market_data_service, "get_yesterdays_closes", closes)
    monkeypatch.setattr(service.market_data_service, "get_current_price", no_price)
    monkeypatch.setattr(service.market_data_service, "get_daily_history", no_history)
    return service, portfolio, (priced.id, unpriced.id)


@pytest.mark.asyncio
async def test_summary(service):
    service, portfolio, asset_ids = service
    for asset_id in asset_ids:
        await service.recalculate_asset_state(portfolio.id, asset_id)
    summary = await service.get_portfolio_summary(portfolio.id, portfolio.user_id)

    assert summary.missing_prices == ["NOP"]
    assert summary.total_cost_basis == 800 + 520 + 500
    assert summary.total_current_value == 15 * 105
    # unrealized only over priced positions: 1575 - 1320
    assert summary.total_unrealized_pnl == 255
    # 10 held all day +50, 5 bought today at 104 -> +5; base 1000 + 520
    assert summary.today_pnl == 55
    assert summary.today_pnl_percent == pytest.approx(55 / 1520 * 100, abs=0.01)


@pytest.mark.asyncio
async def test_holdings_carry_price_and_weight(service):
    service, portfolio, asset_ids = service
    for asset_id in asset_ids:
        await service.recalculate_asset_state(portfolio.id, asset_id)
    holdings = {h.symbol: h for h in await service.get_portfolio_holdings(portfolio.id)}
    assert holdings["PRC"].current_price == 105
    assert holdings["PRC"].weight_percent == 100
    assert holdings["NOP"].weight_percent is None
