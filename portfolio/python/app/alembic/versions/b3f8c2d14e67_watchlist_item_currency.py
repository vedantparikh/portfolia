"""Quote currency on watchlist items

Revision ID: b3f8c2d14e67
Revises: a7d3e9c51f28
Create Date: 2026-10-29

"""

import sqlalchemy as sa

from alembic import op

revision = "b3f8c2d14e67"
down_revision = "a7d3e9c51f28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watchlist_items", sa.Column("currency", sa.String(length=3), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("watchlist_items", "currency")
