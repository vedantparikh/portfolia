"""Portfolio broker sync columns, and assets priced from their own trades

Revision ID: e5b2c8d40a17
Revises: d4e8a2f61c07
Create Date: 2026-10-28

"""

import sqlalchemy as sa

from alembic import op

revision = "e5b2c8d40a17"
down_revision = "d4e8a2f61c07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portfolios", sa.Column("sync_source", sa.String(20), nullable=True))
    op.add_column(
        "portfolios", sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("portfolios", sa.Column("sync_digest", sa.String(64), nullable=True))
    op.add_column("portfolios", sa.Column("sync_report", sa.JSON(), nullable=True))
    op.add_column("assets", sa.Column("price_source", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "price_source")
    op.drop_column("portfolios", "sync_report")
    op.drop_column("portfolios", "sync_digest")
    op.drop_column("portfolios", "synced_at")
    op.drop_column("portfolios", "sync_source")
