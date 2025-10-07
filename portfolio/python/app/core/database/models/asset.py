import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from core.database.models.base import Base


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

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    exchange = Column(String(100), nullable=True)
    isin = Column(
        String(12), nullable=True
    )  # International Securities Identification Number
    cusip = Column(
        String(9), nullable=True
    )  # Committee on Uniform Securities Identification Procedures
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="assets")
    portfolio_holdings = relationship(
        "PortfolioAsset", back_populates="asset", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )
    performance_metrics = relationship(
        "AssetPerformanceMetrics", back_populates="asset", cascade="all, delete-orphan"
    )
    portfolio_allocations = relationship(
        "PortfolioAllocation", back_populates="asset", cascade="all, delete-orphan"
    )
    benchmark_portfolios = relationship(
        "PortfolioBenchmark",
        back_populates="benchmark_asset",
        cascade="all, delete-orphan",
    )
    correlations_as_asset1 = relationship(
        "AssetCorrelation",
        foreign_keys="AssetCorrelation.asset1_id",
        cascade="all, delete-orphan",
    )
    correlations_as_asset2 = relationship(
        "AssetCorrelation",
        foreign_keys="AssetCorrelation.asset2_id",
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

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    country = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)  # e.g., "Major", "Sector", "Regional"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
        nullable=False,
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_market_indices_symbol", "symbol"),
        Index("idx_market_indices_category", "category"),
        Index("idx_market_indices_country", "country"),
        Index("idx_market_indices_active", "is_active"),
    )
