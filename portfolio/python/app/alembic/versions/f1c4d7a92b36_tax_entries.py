"""Account-level tax entries (refunds, charges) per portfolio

Revision ID: f1c4d7a92b36
Revises: e5b2c8d40a17
Create Date: 2026-10-29

"""

import sqlalchemy as sa

from alembic import op

revision = "f1c4d7a92b36"
down_revision = "e5b2c8d40a17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tax_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("isin", sa.String(12), nullable=True),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_tax_entries_portfolio_source_key",
        "tax_entries",
        ["portfolio_id", "source_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_tax_entries_portfolio_source_key", table_name="tax_entries")
    op.drop_table("tax_entries")
