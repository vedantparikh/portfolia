"""
Portfolio Analytics Models
Database models for comprehensive portfolio analysis and performance tracking.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from core.database.models.base import Base


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
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    
    # Portfolio values
    total_value = Column(Numeric(20, 4), nullable=False)
    total_cost_basis = Column(Numeric(20, 4), nullable=False)
    total_unrealized_pnl = Column(Numeric(20, 4), nullable=False)
    total_unrealized_pnl_percent = Column(Numeric(10, 4), nullable=False)
    
    # Performance metrics
    daily_return = Column(Numeric(10, 6), nullable=True)
    cumulative_return = Column(Numeric(10, 6), nullable=True)
    annualized_return = Column(Numeric(10, 6), nullable=True)
    volatility = Column(Numeric(10, 6), nullable=True)
    sharpe_ratio = Column(Numeric(10, 6), nullable=True)
    max_drawdown = Column(Numeric(10, 6), nullable=True)
    
    # Risk metrics
    var_95 = Column(Numeric(10, 6), nullable=True)  # 95% Value at Risk
    var_99 = Column(Numeric(10, 6), nullable=True)  # 99% Value at Risk
    beta = Column(Numeric(10, 6), nullable=True)
    alpha = Column(Numeric(10, 6), nullable=True)
    
    # Benchmark comparison
    benchmark_return = Column(Numeric(10, 6), nullable=True)
    tracking_error = Column(Numeric(10, 6), nullable=True)
    information_ratio = Column(Numeric(10, 6), nullable=True)
    
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="performance_history")
    
    # Indexes
    __table_args__ = (
        Index("idx_portfolio_performance_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_performance_date", "snapshot_date"),
        Index("idx_portfolio_performance_portfolio_date", "portfolio_id", "snapshot_date"),
        UniqueConstraint("portfolio_id", "snapshot_date", name="uq_portfolio_performance_date"),
    )


class AssetPerformanceMetrics(Base):
    """Asset-specific performance metrics and technical indicators."""
    
    __tablename__ = "asset_performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    calculation_date = Column(DateTime(timezone=True), nullable=False)
    
    # Price metrics
    current_price = Column(Numeric(20, 4), nullable=False)
    price_change = Column(Numeric(20, 4), nullable=True)
    price_change_percent = Column(Numeric(10, 4), nullable=True)
    
    # Technical indicators
    sma_20 = Column(Numeric(20, 4), nullable=True)  # Simple Moving Average 20
    sma_50 = Column(Numeric(20, 4), nullable=True)  # Simple Moving Average 50
    sma_200 = Column(Numeric(20, 4), nullable=True)  # Simple Moving Average 200
    ema_12 = Column(Numeric(20, 4), nullable=True)  # Exponential Moving Average 12
    ema_26 = Column(Numeric(20, 4), nullable=True)  # Exponential Moving Average 26
    
    # Momentum indicators
    rsi = Column(Numeric(10, 4), nullable=True)  # Relative Strength Index
    macd = Column(Numeric(20, 4), nullable=True)  # MACD
    macd_signal = Column(Numeric(20, 4), nullable=True)  # MACD Signal
    macd_histogram = Column(Numeric(20, 4), nullable=True)  # MACD Histogram
    stochastic_k = Column(Numeric(10, 4), nullable=True)  # Stochastic %K
    stochastic_d = Column(Numeric(10, 4), nullable=True)  # Stochastic %D
    
    # Volatility indicators
    bollinger_upper = Column(Numeric(20, 4), nullable=True)
    bollinger_middle = Column(Numeric(20, 4), nullable=True)
    bollinger_lower = Column(Numeric(20, 4), nullable=True)
    atr = Column(Numeric(20, 4), nullable=True)  # Average True Range
    
    # Volume indicators
    volume_sma = Column(Numeric(20, 0), nullable=True)  # Volume SMA
    volume_ratio = Column(Numeric(10, 4), nullable=True)  # Current volume / Average volume
    obv = Column(Numeric(20, 0), nullable=True)  # On-Balance Volume
    
    # Risk metrics
    volatility_20d = Column(Numeric(10, 6), nullable=True)  # 20-day volatility
    volatility_60d = Column(Numeric(10, 6), nullable=True)  # 60-day volatility
    volatility_252d = Column(Numeric(10, 6), nullable=True)  # 252-day volatility
    beta = Column(Numeric(10, 6), nullable=True)
    sharpe_ratio = Column(Numeric(10, 6), nullable=True)
    
    # Performance metrics
    total_return_1m = Column(Numeric(10, 6), nullable=True)
    total_return_3m = Column(Numeric(10, 6), nullable=True)
    total_return_6m = Column(Numeric(10, 6), nullable=True)
    total_return_1y = Column(Numeric(10, 6), nullable=True)
    total_return_3y = Column(Numeric(10, 6), nullable=True)
    total_return_5y = Column(Numeric(10, 6), nullable=True)
    
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    
    # Relationships
    asset = relationship("Asset", back_populates="performance_metrics")
    
    # Indexes
    __table_args__ = (
        Index("idx_asset_performance_asset_id", "asset_id"),
        Index("idx_asset_performance_date", "calculation_date"),
        Index("idx_asset_performance_asset_date", "asset_id", "calculation_date"),
        UniqueConstraint("asset_id", "calculation_date", name="uq_asset_performance_date"),
    )


class PortfolioAllocation(Base):
    """Portfolio target allocations and rebalancing information."""
    
    __tablename__ = "portfolio_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    
    # Allocation targets
    target_percentage = Column(Numeric(10, 4), nullable=False)  # Target allocation percentage
    min_percentage = Column(Numeric(10, 4), nullable=True)  # Minimum allocation
    max_percentage = Column(Numeric(10, 4), nullable=True)  # Maximum allocation
    
    # Rebalancing
    rebalance_threshold = Column(Numeric(10, 4), nullable=True)  # Rebalance trigger threshold
    last_rebalance_date = Column(DateTime(timezone=True), nullable=True)
    rebalance_frequency = Column(String(20), nullable=True)  # daily, weekly, monthly, quarterly
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text('now()'),
        onupdate=text('now()'),
        nullable=False,
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="allocations")
    asset = relationship("Asset", back_populates="portfolio_allocations")
    
    # Indexes
    __table_args__ = (
        Index("idx_portfolio_allocations_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_allocations_asset_id", "asset_id"),
        Index("idx_portfolio_allocations_active", "is_active"),
        UniqueConstraint("portfolio_id", "asset_id", name="uq_portfolio_asset_allocation"),
    )


class RebalancingEvent(Base):
    """Portfolio rebalancing events and actions."""
    
    __tablename__ = "rebalancing_events"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    event_date = Column(DateTime(timezone=True), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # scheduled, threshold_triggered, manual
    trigger_reason = Column(Text, nullable=True)
    
    # Pre-rebalancing state
    pre_rebalance_value = Column(Numeric(20, 4), nullable=False)
    pre_rebalance_allocations = Column(Text, nullable=True)  # JSON of allocations
    
    # Rebalancing actions
    rebalancing_actions = Column(Text, nullable=True)  # JSON of buy/sell actions
    
    # Post-rebalancing state
    post_rebalance_value = Column(Numeric(20, 4), nullable=True)
    post_rebalance_allocations = Column(Text, nullable=True)  # JSON of allocations
    
    # Costs and impact
    rebalancing_cost = Column(Numeric(20, 4), nullable=True)  # Transaction costs
    tax_impact = Column(Numeric(20, 4), nullable=True)  # Tax implications
    
    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, completed, failed
    execution_notes = Column(Text, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="rebalancing_events")
    
    # Indexes
    __table_args__ = (
        Index("idx_rebalancing_events_portfolio_id", "portfolio_id"),
        Index("idx_rebalancing_events_date", "event_date"),
        Index("idx_rebalancing_events_status", "status"),
    )


class PortfolioRiskMetrics(Base):
    """Portfolio risk analysis and metrics."""
    
    __tablename__ = "portfolio_risk_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    calculation_date = Column(DateTime(timezone=True), nullable=False)
    
    # Risk metrics
    portfolio_volatility = Column(Numeric(10, 6), nullable=False)
    portfolio_beta = Column(Numeric(10, 6), nullable=True)
    portfolio_alpha = Column(Numeric(10, 6), nullable=True)
    sharpe_ratio = Column(Numeric(10, 6), nullable=True)
    sortino_ratio = Column(Numeric(10, 6), nullable=True)
    treynor_ratio = Column(Numeric(10, 6), nullable=True)
    calmar_ratio = Column(Numeric(10, 6), nullable=True)
    
    # Drawdown metrics
    max_drawdown = Column(Numeric(10, 6), nullable=True)
    max_drawdown_duration = Column(Integer, nullable=True)  # Days
    current_drawdown = Column(Numeric(10, 6), nullable=True)
    
    # Value at Risk
    var_95_1d = Column(Numeric(10, 6), nullable=True)  # 95% VaR 1-day
    var_99_1d = Column(Numeric(10, 6), nullable=True)  # 99% VaR 1-day
    var_95_1m = Column(Numeric(10, 6), nullable=True)  # 95% VaR 1-month
    var_99_1m = Column(Numeric(10, 6), nullable=True)  # 99% VaR 1-month
    
    # Conditional Value at Risk
    cvar_95_1d = Column(Numeric(10, 6), nullable=True)
    cvar_99_1d = Column(Numeric(10, 6), nullable=True)
    
    # Risk level assessment
    risk_level = Column(Enum(RiskLevel), nullable=True)
    risk_score = Column(Numeric(10, 4), nullable=True)  # 0-100 risk score
    
    # Diversification metrics
    concentration_risk = Column(Numeric(10, 6), nullable=True)  # Herfindahl index
    effective_number_of_assets = Column(Numeric(10, 4), nullable=True)
    diversification_ratio = Column(Numeric(10, 6), nullable=True)
    
    # Correlation metrics
    average_correlation = Column(Numeric(10, 6), nullable=True)
    max_correlation = Column(Numeric(10, 6), nullable=True)
    
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="risk_metrics")
    
    # Indexes
    __table_args__ = (
        Index("idx_portfolio_risk_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_risk_date", "calculation_date"),
        Index("idx_portfolio_risk_portfolio_date", "portfolio_id", "calculation_date"),
        UniqueConstraint("portfolio_id", "calculation_date", name="uq_portfolio_risk_date"),
    )


class AssetCorrelation(Base):
    """Asset correlation matrix for portfolio analysis."""
    
    __tablename__ = "asset_correlations"
    
    id = Column(Integer, primary_key=True, index=True)
    asset1_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    asset2_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    calculation_date = Column(DateTime(timezone=True), nullable=False)
    
    # Correlation metrics
    correlation_1m = Column(Numeric(10, 6), nullable=True)  # 1-month correlation
    correlation_3m = Column(Numeric(10, 6), nullable=True)  # 3-month correlation
    correlation_6m = Column(Numeric(10, 6), nullable=True)  # 6-month correlation
    correlation_1y = Column(Numeric(10, 6), nullable=True)  # 1-year correlation
    correlation_3y = Column(Numeric(10, 6), nullable=True)  # 3-year correlation
    
    # Rolling correlation
    rolling_correlation_20d = Column(Numeric(10, 6), nullable=True)
    rolling_correlation_60d = Column(Numeric(10, 6), nullable=True)
    
    # Statistical significance
    p_value = Column(Numeric(10, 6), nullable=True)
    is_significant = Column(Boolean, nullable=True)  # p < 0.05
    
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    
    # Relationships
    asset1 = relationship("Asset", foreign_keys=[asset1_id])
    asset2 = relationship("Asset", foreign_keys=[asset2_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_asset_correlation_asset1", "asset1_id"),
        Index("idx_asset_correlation_asset2", "asset2_id"),
        Index("idx_asset_correlation_date", "calculation_date"),
        UniqueConstraint("asset1_id", "asset2_id", "calculation_date", name="uq_asset_correlation"),
    )


class PortfolioBenchmark(Base):
    """Portfolio benchmark tracking and comparison."""
    
    __tablename__ = "portfolio_benchmarks"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    benchmark_asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    
    # Benchmark details
    benchmark_name = Column(String(255), nullable=False)
    benchmark_type = Column(String(50), nullable=False)  # index, custom, peer_group
    
    # Comparison metrics
    tracking_error = Column(Numeric(10, 6), nullable=True)
    information_ratio = Column(Numeric(10, 6), nullable=True)
    beta = Column(Numeric(10, 6), nullable=True)
    alpha = Column(Numeric(10, 6), nullable=True)
    
    # Performance comparison
    excess_return = Column(Numeric(10, 6), nullable=True)
    excess_return_percent = Column(Numeric(10, 4), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)  # Primary benchmark
    
    created_at = Column(
        DateTime(timezone=True), server_default=text('now()'), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text('now()'),
        onupdate=text('now()'),
        nullable=False,
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="benchmarks")
    benchmark_asset = relationship("Asset", back_populates="benchmark_portfolios")
    
    # Indexes
    __table_args__ = (
        Index("idx_portfolio_benchmarks_portfolio_id", "portfolio_id"),
        Index("idx_portfolio_benchmarks_asset_id", "benchmark_asset_id"),
        Index("idx_portfolio_benchmarks_active", "is_active"),
        Index("idx_portfolio_benchmarks_primary", "is_primary"),
    )
