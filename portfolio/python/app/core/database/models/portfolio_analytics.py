"""
Portfolio Analytics Models
Database models for comprehensive portfolio analysis and performance tracking.
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.models.base import Base

if TYPE_CHECKING:
    from core.database.models.asset import Asset
    from core.database.models.portfolio import Portfolio


class PerformanceMetricType(enum.Enum):
    """Performance metric type enumeration."""

    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    BETA = "beta"
    ALPHA = "alpha"
    INFORMATION_RATIO = "information_ratio"
    TREYNOR_RATIO = "treynor_ratio"
    CALMAR_RATIO = "calmar_ratio"
    VALUE_AT_RISK = "var"
    CONDITIONAL_VALUE_AT_RISK = "cvar"
    TRACKING_ERROR = "tracking_error"
    CORRELATION = "correlation"


class RiskLevel(enum.Enum):
    """Risk level enumeration."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PortfolioPerformanceHistory(Base):
    """Historical portfolio performance snapshots."""

    __tablename__ = "portfolio_performance_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Portfolio values
    total_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )
    total_unrealized_pnl_percent: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False
    )

    # Performance metrics
    daily_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    cumulative_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    annualized_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    volatility: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # Risk metrics
    var_95: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )  # 95% Value at Risk
    var_99: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )  # 99% Value at Risk
    beta: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    alpha: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # Benchmark comparison
    benchmark_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    tracking_error: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    information_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    portfolio: Mapped[Portfolio] = relationship(
        "Portfolio", back_populates="performance_history"
    )

    # Indexes
    __table_args__ = (
        Index("idx_portfolio_performance_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_performance_date", "snapshot_date"),
        Index(
            "idx_portfolio_performance_portfolio_date", "portfolio_id", "snapshot_date"
        ),
        UniqueConstraint(
            "portfolio_id", "snapshot_date", name="uq_portfolio_performance_date"
        ),
    )


class PortfolioAllocation(Base):
    """Portfolio target allocations and rebalancing information."""

    __tablename__ = "portfolio_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )

    # Allocation targets
    target_percentage: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False
    )  # Target allocation percentage
    min_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Minimum allocation
    max_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Maximum allocation

    # Rebalancing
    rebalance_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Rebalance trigger threshold
    last_rebalance_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rebalance_frequency: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # daily, weekly, monthly, quarterly

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    portfolio: Mapped[Portfolio] = relationship(
        "Portfolio", back_populates="allocations"
    )
    asset: Mapped[Asset] = relationship("Asset", back_populates="portfolio_allocations")

    # Indexes
    __table_args__ = (
        Index("idx_portfolio_allocations_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_allocations_asset_id", "asset_id"),
        Index("idx_portfolio_allocations_active", "is_active"),
        UniqueConstraint(
            "portfolio_id", "asset_id", name="uq_portfolio_asset_allocation"
        ),
    )


class RebalancingEvent(Base):
    """Portfolio rebalancing events and actions."""

    __tablename__ = "rebalancing_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # scheduled, threshold_triggered, manual
    trigger_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pre-rebalancing state
    pre_rebalance_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    pre_rebalance_allocations: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON of allocations

    # Rebalancing actions
    rebalancing_actions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON of buy/sell actions

    # Post-rebalancing state
    post_rebalance_value: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    post_rebalance_allocations: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON of allocations

    # Costs and impact
    rebalancing_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Transaction costs
    tax_impact: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Tax implications

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, completed, failed
    execution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    portfolio: Mapped[Portfolio] = relationship(
        "Portfolio", back_populates="rebalancing_events"
    )

    # Indexes
    __table_args__ = (
        Index("idx_rebalancing_events_portfolio_id", "portfolio_id"),
        Index("idx_rebalancing_events_date", "event_date"),
        Index("idx_rebalancing_events_status", "status"),
    )


class PortfolioBenchmark(Base):
    """Portfolio benchmark tracking and comparison."""

    __tablename__ = "portfolio_benchmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    benchmark_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )

    # Benchmark details
    benchmark_name: Mapped[str] = mapped_column(String(255), nullable=False)
    benchmark_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # index, custom, peer_group

    # Comparison metrics
    tracking_error: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    information_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    beta: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    alpha: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # Performance comparison
    excess_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    excess_return_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Primary benchmark

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    portfolio: Mapped[Portfolio] = relationship(
        "Portfolio", back_populates="benchmarks"
    )
    benchmark_asset: Mapped[Asset] = relationship(
        "Asset", back_populates="benchmark_portfolios"
    )

    @property
    def symbol(self) -> str | None:
        return self.benchmark_asset.symbol if self.benchmark_asset else None

    # Indexes
    __table_args__ = (
        Index("idx_portfolio_benchmarks_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_benchmarks_asset_id", "benchmark_asset_id"),
        Index("idx_portfolio_benchmarks_active", "is_active"),
        Index("idx_portfolio_benchmarks_primary", "is_primary"),
    )
