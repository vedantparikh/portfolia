"""Broker logins (Trade Republic via pytr) and their fetch runs

Revision ID: a7d3e9c51f28
Revises: f1c4d7a92b36
Create Date: 2026-10-29

"""

import sqlalchemy as sa

from alembic import op

revision = "a7d3e9c51f28"
down_revision = "f1c4d7a92b36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("secret", sa.Text(), nullable=True),
        sa.Column("fetch_status", sa.String(20), nullable=False),
        sa.Column("fetch_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetch_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetch_report", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_broker_connections_user_source",
        "broker_connections",
        ["user_id", "source"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_broker_connections_user_source", table_name="broker_connections")
    op.drop_table("broker_connections")
