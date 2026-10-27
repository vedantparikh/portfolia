"""
Regression: two concurrent first transactions for the same asset returned 500
(unique violation on portfolio_assets) because the market-price await happened
after the new PortfolioAsset was staged, letting the other request insert it too.
"""

from datetime import datetime, timezone
from decimal import Decimal

from core.database.models import Asset, Portfolio, PortfolioAsset, User
from core.schemas.portfolio import TransactionCreate
from core.services.market_data_service import MarketDataService
from modules.portfolios.service import PortfolioService


async def test_price_is_fetched_before_portfolio_asset_is_staged(test_db, monkeypatch):
    staged_at_await = []

    async def fake_price(self, symbol):
        staged_at_await.append(
            [o for o in test_db.new if isinstance(o, PortfolioAsset)]
        )
        return 110.0

    monkeypatch.setattr(MarketDataService, "get_current_price", fake_price)

    user = User(email="a@example.com", username="alice", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(name="p", user_id=user.id)
    asset = Asset(symbol="AAPL", name="Apple", asset_type="EQUITY", user_id=user.id)
    test_db.add_all([portfolio, asset])
    test_db.commit()

    transaction = await PortfolioService(test_db).add_transaction(
        portfolio.id,
        TransactionCreate(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type="buy",
            quantity=Decimal("10"),
            price=Decimal("100"),
            transaction_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        user.id,
    )

    assert transaction is not None
    assert staged_at_await == [[]]
    holding = test_db.query(PortfolioAsset).one()
    assert holding.quantity == Decimal("10")
    assert holding.current_value == Decimal("1100")
