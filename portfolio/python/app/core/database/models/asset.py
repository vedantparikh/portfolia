from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.models.base import Base

if TYPE_CHECKING:
    from core.database.models.portfolio import PortfolioAsset
    from core.database.models.portfolio_analytics import (
        PortfolioAllocation,
        PortfolioBenchmark,
    )
    from core.database.models.transaction import Transaction
    from core.database.models.user import User


class AssetType(enum.Enum):
    """Asset type enumeration."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    BOND = "BOND"
    INDEX = "INDEX"
    CASH = "CASH"
    MUTUALFUND = "MUTUALFUND"
    COMMODITY = "COMMODITY"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    REAL_ESTATE = "REAL_ESTATE"
    OTHER = "OTHER"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    WARRANT = "WARRANT"


class Asset(Base):
    """Financial asset model."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(100), nullable=True)
    isin: Mapped[str | None] = mapped_column(
        String(12), nullable=True
    )  # International Securities Identification Number
    cusip: Mapped[str | None] = mapped_column(
        String(9), nullable=True
    )  # Committee on Uniform Securities Identification Procedures
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # None = Yahoo; "trades" = no market data (e.g. knock-outs), priced from its own fills
    price_source: Mapped[str | None] = mapped_column(String(10), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    user: Mapped[User] = relationship("User", back_populates="assets")
    portfolio_holdings: Mapped[list[PortfolioAsset]] = relationship(
        "PortfolioAsset", back_populates="asset", cascade="all, delete-orphan"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )
    portfolio_allocations: Mapped[list[PortfolioAllocation]] = relationship(
        "PortfolioAllocation", back_populates="asset", cascade="all, delete-orphan"
    )
    benchmark_portfolios: Mapped[list[PortfolioBenchmark]] = relationship(
        "PortfolioBenchmark",
        back_populates="benchmark_asset",
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_assets_user_id", "user_id"),
        Index("idx_assets_symbol", "symbol"),
        Index("idx_assets_user_symbol", "user_id", "symbol", unique=True),
        Index("idx_assets_type", "asset_type"),
        Index("idx_assets_currency", "currency"),
        Index("idx_assets_exchange", "exchange"),
        Index("idx_assets_sector", "sector"),
        Index("idx_assets_country", "country"),
        Index("idx_assets_active", "is_active"),
    )


class MarketIndex(Base):
    """Market benchmark indices."""

    __tablename__ = "market_indices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g., "Major", "Sector", "Regional"
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

    # Indexes for performance
    __table_args__ = (
        Index("idx_market_indices_symbol", "symbol"),
        Index("idx_market_indices_category", "category"),
        Index("idx_market_indices_country", "country"),
        Index("idx_market_indices_active", "is_active"),
    )
