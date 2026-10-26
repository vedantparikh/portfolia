"""Widen prices and cash amounts to numeric(20, 8).

Datetimes are already timestamp with time zone, so this migration does not
touch them.

Revision ID: b8c1d4e27a90
Revises: a3f1c9d2e7b4
Create Date: 2026-10-26

"""

import sqlalchemy as sa

from alembic import op

revision = "b8c1d4e27a90"
down_revision = "a3f1c9d2e7b4"
branch_labels = None
depends_on = None

# table, column, previous precision, previous scale, nullable
_COLUMNS = (
    ("transactions", "price", 20, 4, False),
    ("transactions", "total_amount", 20, 4, False),
    ("transactions", "fees", 20, 4, False),
    ("transactions", "taxes", 20, 4, False),
    ("portfolio_assets", "cost_basis", 20, 4, False),
    ("portfolio_assets", "cost_basis_total", 20, 4, False),
    ("portfolio_assets", "current_value", 20, 4, True),
    ("portfolio_assets", "unrealized_pnl", 20, 4, True),
    ("portfolio_assets", "realized_pnl", 20, 4, True),
    ("portfolio_assets", "today_pnl", 20, 4, True),
    ("portfolio_performance_history", "total_value", 20, 4, False),
    ("portfolio_performance_history", "total_cost_basis", 20, 4, False),
    ("portfolio_performance_history", "total_unrealized_pnl", 20, 4, False),
    ("rebalancing_events", "pre_rebalance_value", 20, 4, False),
    ("rebalancing_events", "post_rebalance_value", 20, 4, True),
    ("rebalancing_events", "rebalancing_cost", 20, 4, True),
    ("rebalancing_events", "tax_impact", 20, 4, True),
    ("watchlist_items", "added_price", 10, 2, True),
    ("watchlist_items", "current_price", 10, 2, True),
    ("watchlist_items", "price_change_since_added", 10, 2, True),
    ("watchlist_items", "alert_price_high", 10, 2, True),
    ("watchlist_items", "alert_price_low", 10, 2, True),
    ("watchlist_alerts", "threshold_value", 10, 2, False),
    ("watchlist_alerts", "triggered_value", 10, 2, True),
    ("watchlist_performance", "price", 10, 2, False),
    ("watchlist_performance", "market_cap", 20, 2, True),
    ("watchlist_performance", "price_change_since_added", 10, 2, True),
)

_WIDE = sa.Numeric(precision=20, scale=8)


def _alter(table, column, precision, scale, nullable, type_) -> None:
    op.alter_column(
        table,
        column,
        existing_type=sa.Numeric(precision=precision, scale=scale),
        type_=type_,
        existing_nullable=nullable,
    )


def upgrade() -> None:
    for table, column, precision, scale, nullable in _COLUMNS:
        _alter(table, column, precision, scale, nullable, _WIDE)


def downgrade() -> None:
    for table, column, precision, scale, nullable in _COLUMNS:
        _alter(
            table,
            column,
            20,
            8,
            nullable,
            sa.Numeric(precision=precision, scale=scale),
        )
