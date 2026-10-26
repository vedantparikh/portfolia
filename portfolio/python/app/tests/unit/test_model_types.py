"""Prices and cash are numeric(20, 8). Datetimes stay timezone-aware."""

from sqlalchemy import DateTime, Numeric

from core.database.models import Base
from core.database.models.transaction import Transaction

MONEY = {
    ("transactions", "price"),
    ("transactions", "total_amount"),
    ("transactions", "fees"),
    ("transactions", "taxes"),
    ("portfolio_assets", "cost_basis"),
    ("portfolio_assets", "cost_basis_total"),
    ("portfolio_assets", "current_value"),
    ("portfolio_assets", "unrealized_pnl"),
    ("portfolio_assets", "realized_pnl"),
    ("portfolio_assets", "today_pnl"),
    ("portfolio_performance_history", "total_value"),
    ("portfolio_performance_history", "total_cost_basis"),
    ("portfolio_performance_history", "total_unrealized_pnl"),
    ("rebalancing_events", "pre_rebalance_value"),
    ("rebalancing_events", "post_rebalance_value"),
    ("rebalancing_events", "rebalancing_cost"),
    ("rebalancing_events", "tax_impact"),
    ("watchlist_items", "added_price"),
    ("watchlist_items", "current_price"),
    ("watchlist_items", "price_change_since_added"),
    ("watchlist_items", "alert_price_high"),
    ("watchlist_items", "alert_price_low"),
    ("watchlist_alerts", "threshold_value"),
    ("watchlist_alerts", "triggered_value"),
    ("watchlist_performance", "price"),
    ("watchlist_performance", "market_cap"),
    ("watchlist_performance", "price_change_since_added"),
}


def test_money_and_prices_are_wide_and_datetimes_are_aware():
    seen = set()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone is True, f"{table.name}.{column.name}"
            if (table.name, column.name) in MONEY:
                assert isinstance(column.type, Numeric)
                assert column.type.precision == 20
                assert column.type.scale == 8
                seen.add((table.name, column.name))
    assert seen == MONEY


def test_transaction_price_is_a_mapped_decimal():
    assert Transaction.__annotations__["price"] == "Mapped[Decimal]"
