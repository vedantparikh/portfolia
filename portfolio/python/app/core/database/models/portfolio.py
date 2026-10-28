from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database.models.base import Base

if TYPE_CHECKING:
    from core.database.models.asset import Asset
    from core.database.models.portfolio_analytics import (
        PortfolioAllocation,
        PortfolioBenchmark,
        PortfolioPerformanceHistory,
        RebalancingEvent,
    )
    from core.database.models.transaction import Transaction
    from core.database.models.user import User


class Portfolio(Base):
    """Portfolio model for user investment portfolios."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Broker sync: "pytr" re-imports the Trade Republic export when it changes
    sync_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="portfolios")
    assets: Mapped[list[PortfolioAsset]] = relationship(
        "PortfolioAsset", back_populates="portfolio", cascade="all, delete-orphan"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )
    performance_history: Mapped[list[PortfolioPerformanceHistory]] = relationship(
        "PortfolioPerformanceHistory",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    allocations: Mapped[list[PortfolioAllocation]] = relationship(
        "PortfolioAllocation", back_populates="portfolio", cascade="all, delete-orphan"
    )
    rebalancing_events: Mapped[list[RebalancingEvent]] = relationship(
        "RebalancingEvent", back_populates="portfolio", cascade="all, delete-orphan"
    )
    benchmarks: Mapped[list[PortfolioBenchmark]] = relationship(
        "PortfolioBenchmark", back_populates="portfolio", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_portfolios_user_id", "user_id"),
        Index("idx_portfolios_currency", "currency"),
        Index("idx_portfolios_active", "is_active"),
        Index("idx_portfolios_public", "is_public"),
    )


class PortfolioAsset(Base):
    """Assets within portfolios with current holdings."""

    __tablename__ = "portfolio_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # Support for fractional shares
    cost_basis: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # Average cost per share
    cost_basis_total: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # Total cost basis
    current_value: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Current market value
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Unrealized profit/loss
    unrealized_pnl_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Unrealized P&L percentage
    realized_pnl: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Realized profit/loss
    realized_pnl_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Realized P&L percentage
    today_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    today_pnl_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="assets")
    asset: Mapped[Asset] = relationship("Asset", back_populates="portfolio_holdings")

    # Indexes for performance
    __table_args__ = (
        Index("idx_portfolio_assets_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_assets_asset_id", "asset_id"),
        Index(
            "idx_portfolio_assets_portfolio_asset",
            "portfolio_id",
            "asset_id",
            unique=True,
        ),
    )

    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        if self.current_value is not None:
            return float(self.current_value)
        return float(self.cost_basis_total)

    @property
    def total_return(self) -> float:
        """Calculate total return (realized + unrealized)."""
        if self.unrealized_pnl is not None:
            return float(self.unrealized_pnl)
        return 0.0

    @property
    def total_return_percent(self) -> float:
        """Calculate total return percentage."""
        if self.unrealized_pnl_percent is not None:
            return float(self.unrealized_pnl_percent)
        return 0.0
