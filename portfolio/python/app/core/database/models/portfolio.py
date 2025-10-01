from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database.connection import Base


class Portfolio(Base):
    """Portfolio model for user investment portfolios."""

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="portfolios")
    assets = relationship(
        "PortfolioAsset", back_populates="portfolio", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )
    performance_history = relationship(
        "PortfolioPerformanceHistory",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    allocations = relationship(
        "PortfolioAllocation", back_populates="portfolio", cascade="all, delete-orphan"
    )
    rebalancing_events = relationship(
        "RebalancingEvent", back_populates="portfolio", cascade="all, delete-orphan"
    )
    risk_metrics = relationship(
        "PortfolioRiskMetrics", back_populates="portfolio", cascade="all, delete-orphan"
    )
    benchmarks = relationship(
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

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Numeric(20, 8), nullable=False)  # Support for fractional shares
    cost_basis = Column(Numeric(20, 4), nullable=False)  # Average cost per share
    cost_basis_total = Column(Numeric(20, 4), nullable=False)  # Total cost basis
    current_value = Column(Numeric(20, 4), nullable=True)  # Current market value
    unrealized_pnl = Column(Numeric(20, 4), nullable=True)  # Unrealized profit/loss
    unrealized_pnl_percent = Column(
        Numeric(10, 4), nullable=True
    )  # Unrealized P&L percentage
    realized_pnl = Column(Numeric(20, 4), nullable=True)  # Realized profit/loss
    realized_pnl_percent = Column(
        Numeric(10, 4), nullable=True
    )  # Realized P&L percentage
    today_pnl = Column(Numeric(20, 4), nullable=True)
    today_pnl_percent = Column(Numeric(10, 4), nullable=True)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    portfolio = relationship("Portfolio", back_populates="assets")
    asset = relationship("Asset", back_populates="portfolio_holdings")

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
