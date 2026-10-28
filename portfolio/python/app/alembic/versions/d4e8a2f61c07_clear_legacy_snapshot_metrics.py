"""Clear snapshot metrics written by the old formula

Revision ID: d4e8a2f61c07
Revises: c3a7e9b14d20
Create Date: 2026-10-28

Rows written before the engine computed snapshots hold fractions (0.15) and
count deposits as returns. New rows are engine percents (15.0). The metrics of
the old rows are cleared; value and cost stay. There is nothing to restore.
"""

from alembic import op

revision = "d4e8a2f61c07"
down_revision = "c3a7e9b14d20"
branch_labels = None
depends_on = None

METRICS = (
    "daily_return",
    "cumulative_return",
    "annualized_return",
    "volatility",
    "sharpe_ratio",
    "max_drawdown",
    "var_95",
    "var_99",
    "beta",
    "alpha",
    "benchmark_return",
    "tracking_error",
    "information_ratio",
)


def upgrade() -> None:
    op.execute(
        "UPDATE portfolio_performance_history SET "
        + ", ".join(f"{column} = NULL" for column in METRICS)
    )


def downgrade() -> None:
    pass
