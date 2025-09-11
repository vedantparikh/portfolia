"""
Portfolio Analytics Schemas
Pydantic schemas for comprehensive portfolio analysis and performance tracking.
"""

from datetime import datetime
from decimal import Decimal
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from app.core.database.models.portfolio_analytics import RiskLevel


# Portfolio Performance History Schemas
class PortfolioPerformanceHistoryBase(BaseModel):
    portfolio_id: int
    snapshot_date: datetime
    total_value: Decimal = Field(..., description="Total portfolio value")
    total_cost_basis: Decimal = Field(..., description="Total cost basis")
    total_unrealized_pnl: Decimal = Field(..., description="Total unrealized P&L")
    total_unrealized_pnl_percent: Decimal = Field(
        ..., description="Total unrealized P&L percentage"
    )
    daily_return: Optional[Decimal] = Field(None, description="Daily return")
    cumulative_return: Optional[Decimal] = Field(None, description="Cumulative return")
    annualized_return: Optional[Decimal] = Field(None, description="Annualized return")
    volatility: Optional[Decimal] = Field(None, description="Portfolio volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    var_95: Optional[Decimal] = Field(None, description="95% Value at Risk")
    var_99: Optional[Decimal] = Field(None, description="99% Value at Risk")
    beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    alpha: Optional[Decimal] = Field(None, description="Portfolio alpha")
    benchmark_return: Optional[Decimal] = Field(None, description="Benchmark return")
    tracking_error: Optional[Decimal] = Field(None, description="Tracking error")
    information_ratio: Optional[Decimal] = Field(None, description="Information ratio")


class PortfolioPerformanceHistoryCreate(PortfolioPerformanceHistoryBase):
    pass


class PortfolioPerformanceHistory(PortfolioPerformanceHistoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Asset Performance Metrics Schemas
class AssetPerformanceMetricsBase(BaseModel):
    asset_id: int
    calculation_date: datetime
    current_price: Decimal = Field(..., description="Current asset price")
    price_change: Optional[Decimal] = Field(None, description="Price change")
    price_change_percent: Optional[Decimal] = Field(
        None, description="Price change percentage"
    )

    # Technical indicators
    sma_20: Optional[Decimal] = Field(None, description="20-day Simple Moving Average")
    sma_50: Optional[Decimal] = Field(None, description="50-day Simple Moving Average")
    sma_200: Optional[Decimal] = Field(
        None, description="200-day Simple Moving Average"
    )
    ema_12: Optional[Decimal] = Field(
        None, description="12-day Exponential Moving Average"
    )
    ema_26: Optional[Decimal] = Field(
        None, description="26-day Exponential Moving Average"
    )

    # Momentum indicators
    rsi: Optional[Decimal] = Field(None, description="Relative Strength Index")
    macd: Optional[Decimal] = Field(None, description="MACD")
    macd_signal: Optional[Decimal] = Field(None, description="MACD Signal")
    macd_histogram: Optional[Decimal] = Field(None, description="MACD Histogram")
    stochastic_k: Optional[Decimal] = Field(None, description="Stochastic %K")
    stochastic_d: Optional[Decimal] = Field(None, description="Stochastic %D")

    # Volatility indicators
    bollinger_upper: Optional[Decimal] = Field(None, description="Bollinger Upper Band")
    bollinger_middle: Optional[Decimal] = Field(
        None, description="Bollinger Middle Band"
    )
    bollinger_lower: Optional[Decimal] = Field(None, description="Bollinger Lower Band")
    atr: Optional[Decimal] = Field(None, description="Average True Range")

    # Volume indicators
    volume_sma: Optional[Decimal] = Field(
        None, description="Volume Simple Moving Average"
    )
    volume_ratio: Optional[Decimal] = Field(None, description="Volume ratio")
    obv: Optional[Decimal] = Field(None, description="On-Balance Volume")

    # Risk metrics
    volatility_20d: Optional[Decimal] = Field(None, description="20-day volatility")
    volatility_60d: Optional[Decimal] = Field(None, description="60-day volatility")
    volatility_252d: Optional[Decimal] = Field(None, description="252-day volatility")
    beta: Optional[Decimal] = Field(None, description="Asset beta")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Asset Sharpe ratio")

    # Performance metrics (matching database model)
    total_return_1m: Optional[Decimal] = Field(None, description="1-month total return")
    total_return_3m: Optional[Decimal] = Field(None, description="3-month total return")
    total_return_1y: Optional[Decimal] = Field(None, description="1-year total return")

    # Note: total_return_6m, total_return_3y, total_return_5y not in database model
    # These would need to be calculated fields if needed


class AssetPerformanceMetricsCreate(AssetPerformanceMetricsBase):
    pass


class AssetPerformanceMetrics(AssetPerformanceMetricsBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Portfolio Allocation Schemas
class PortfolioAllocationBase(BaseModel):
    portfolio_id: int
    asset_id: int
    target_percentage: Decimal = Field(
        ..., ge=0, le=100, description="Target allocation percentage"
    )
    min_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Minimum allocation percentage"
    )
    max_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Maximum allocation percentage"
    )
    rebalance_threshold: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Rebalance trigger threshold"
    )
    last_rebalance_date: Optional[datetime] = Field(
        None, description="Last rebalance date"
    )
    rebalance_frequency: Optional[str] = Field(None, description="Rebalance frequency")
    is_active: bool = Field(default=True, description="Whether allocation is active")


class PortfolioAllocationCreate(PortfolioAllocationBase):
    pass


class PortfolioAllocationUpdate(BaseModel):
    target_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    min_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    max_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    rebalance_threshold: Optional[Decimal] = Field(None, ge=0, le=100)
    rebalance_frequency: Optional[str] = None
    is_active: Optional[bool] = None


class PortfolioAllocation(PortfolioAllocationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Rebalancing Event Schemas
class RebalancingEventBase(BaseModel):
    portfolio_id: int
    event_date: datetime
    event_type: str = Field(
        ..., description="Event type: scheduled, threshold_triggered, manual"
    )
    trigger_reason: Optional[str] = Field(None, description="Reason for rebalancing")
    pre_rebalance_value: Decimal = Field(
        ..., description="Portfolio value before rebalancing"
    )
    pre_rebalance_allocations: Optional[str] = Field(
        None, description="JSON of pre-rebalance allocations"
    )
    rebalancing_actions: Optional[str] = Field(
        None, description="JSON of rebalancing actions"
    )
    post_rebalance_value: Optional[Decimal] = Field(
        None, description="Portfolio value after rebalancing"
    )
    post_rebalance_allocations: Optional[str] = Field(
        None, description="JSON of post-rebalance allocations"
    )
    rebalancing_cost: Optional[Decimal] = Field(None, description="Transaction costs")
    tax_impact: Optional[Decimal] = Field(None, description="Tax implications")
    status: str = Field(
        default="pending", description="Event status: pending, completed, failed"
    )
    execution_notes: Optional[str] = Field(None, description="Execution notes")


class RebalancingEventCreate(RebalancingEventBase):
    pass


class RebalancingEventUpdate(BaseModel):
    post_rebalance_value: Optional[Decimal] = None
    post_rebalance_allocations: Optional[str] = None
    rebalancing_cost: Optional[Decimal] = None
    tax_impact: Optional[Decimal] = None
    status: Optional[str] = None
    execution_notes: Optional[str] = None


class RebalancingEvent(RebalancingEventBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Portfolio Risk Metrics Schemas
class PortfolioRiskMetricsBase(BaseModel):
    portfolio_id: int
    calculation_date: datetime
    portfolio_volatility: Decimal = Field(..., description="Portfolio volatility")
    portfolio_beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    portfolio_alpha: Optional[Decimal] = Field(None, description="Portfolio alpha")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    treynor_ratio: Optional[Decimal] = Field(None, description="Treynor ratio")
    calmar_ratio: Optional[Decimal] = Field(None, description="Calmar ratio")

    # Drawdown metrics
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    max_drawdown_duration: Optional[int] = Field(
        None, description="Maximum drawdown duration in days"
    )
    current_drawdown: Optional[Decimal] = Field(None, description="Current drawdown")

    # Value at Risk
    var_95_1d: Optional[Decimal] = Field(None, description="95% VaR 1-day")
    var_99_1d: Optional[Decimal] = Field(None, description="99% VaR 1-day")
    var_95_1m: Optional[Decimal] = Field(None, description="95% VaR 1-month")
    var_99_1m: Optional[Decimal] = Field(None, description="99% VaR 1-month")

    # Conditional Value at Risk
    cvar_95_1d: Optional[Decimal] = Field(None, description="95% CVaR 1-day")
    cvar_99_1d: Optional[Decimal] = Field(None, description="99% CVaR 1-day")

    # Risk level assessment
    risk_level: Optional[RiskLevel] = Field(None, description="Risk level")
    risk_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Risk score 0-100"
    )

    # Diversification metrics
    concentration_risk: Optional[Decimal] = Field(
        None, description="Concentration risk (Herfindahl index)"
    )
    effective_number_of_assets: Optional[Decimal] = Field(
        None, description="Effective number of assets"
    )
    diversification_ratio: Optional[Decimal] = Field(
        None, description="Diversification ratio"
    )

    # Correlation metrics
    average_correlation: Optional[Decimal] = Field(
        None, description="Average correlation"
    )
    max_correlation: Optional[Decimal] = Field(None, description="Maximum correlation")


class PortfolioRiskMetricsCreate(PortfolioRiskMetricsBase):
    pass


class PortfolioRiskMetrics(PortfolioRiskMetricsBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Asset Correlation Schemas
class AssetCorrelationBase(BaseModel):
    asset1_id: int
    asset2_id: int
    calculation_date: datetime
    correlation_1m: Optional[Decimal] = Field(None, description="1-month correlation")
    correlation_3m: Optional[Decimal] = Field(None, description="3-month correlation")
    correlation_6m: Optional[Decimal] = Field(None, description="6-month correlation")
    correlation_1y: Optional[Decimal] = Field(None, description="1-year correlation")
    correlation_3y: Optional[Decimal] = Field(None, description="3-year correlation")
    rolling_correlation_20d: Optional[Decimal] = Field(
        None, description="20-day rolling correlation"
    )
    rolling_correlation_60d: Optional[Decimal] = Field(
        None, description="60-day rolling correlation"
    )
    p_value: Optional[Decimal] = Field(
        None, description="Statistical significance p-value"
    )
    is_significant: Optional[bool] = Field(
        None, description="Whether correlation is statistically significant"
    )


class AssetCorrelationCreate(AssetCorrelationBase):
    pass


class AssetCorrelation(AssetCorrelationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Portfolio Benchmark Schemas
class PortfolioBenchmarkBase(BaseModel):
    portfolio_id: int
    benchmark_asset_id: int
    benchmark_name: str = Field(..., description="Benchmark name")
    benchmark_type: str = Field(
        ..., description="Benchmark type: index, custom, peer_group"
    )
    tracking_error: Optional[Decimal] = Field(None, description="Tracking error")
    information_ratio: Optional[Decimal] = Field(None, description="Information ratio")
    beta: Optional[Decimal] = Field(None, description="Beta")
    alpha: Optional[Decimal] = Field(None, description="Alpha")
    excess_return: Optional[Decimal] = Field(None, description="Excess return")
    excess_return_percent: Optional[Decimal] = Field(
        None, description="Excess return percentage"
    )
    is_active: bool = Field(default=True, description="Whether benchmark is active")
    is_primary: bool = Field(
        default=False, description="Whether this is the primary benchmark"
    )


class PortfolioBenchmarkCreate(PortfolioBenchmarkBase):
    pass


class PortfolioBenchmarkUpdate(BaseModel):
    benchmark_name: Optional[str] = None
    benchmark_type: Optional[str] = None
    tracking_error: Optional[Decimal] = None
    information_ratio: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    excess_return: Optional[Decimal] = None
    excess_return_percent: Optional[Decimal] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None


class PortfolioBenchmark(PortfolioBenchmarkBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Comprehensive Analytics Schemas
class PortfolioAnalyticsSummary(BaseModel):
    """Comprehensive portfolio analytics summary."""

    portfolio_id: int
    portfolio_name: str
    calculation_date: datetime

    # Basic metrics
    total_value: Decimal
    total_cost_basis: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_percent: Decimal

    # Performance metrics
    total_return: Optional[Decimal] = None
    annualized_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None

    # Risk metrics
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[Decimal] = None
    var_95_1d: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None

    # Diversification metrics
    concentration_risk: Optional[Decimal] = None
    effective_number_of_assets: Optional[Decimal] = None
    diversification_ratio: Optional[Decimal] = None

    # Benchmark comparison
    benchmark_name: Optional[str] = None
    excess_return: Optional[Decimal] = None
    tracking_error: Optional[Decimal] = None
    information_ratio: Optional[Decimal] = None


class PortfolioAllocationAnalysis(BaseModel):
    """Portfolio allocation analysis with drift detection."""

    portfolio_id: int
    analysis_date: datetime

    # Current allocations
    current_allocations: List[dict] = Field(
        ..., description="Current asset allocations"
    )
    target_allocations: List[dict] = Field(..., description="Target asset allocations")

    # Drift analysis
    total_drift: Decimal = Field(..., description="Total allocation drift")
    max_drift: Decimal = Field(..., description="Maximum single asset drift")
    assets_requiring_rebalance: List[dict] = Field(
        ..., description="Assets requiring rebalancing"
    )

    # Rebalancing recommendations
    rebalancing_actions: List[dict] = Field(
        ..., description="Recommended rebalancing actions"
    )
    estimated_cost: Optional[Decimal] = Field(
        None, description="Estimated rebalancing cost"
    )
    tax_impact: Optional[Decimal] = Field(None, description="Estimated tax impact")


class PortfolioRiskAnalysis(BaseModel):
    """Comprehensive portfolio risk analysis."""

    portfolio_id: int
    analysis_date: datetime

    # Risk metrics
    portfolio_volatility: Decimal
    portfolio_beta: Optional[Decimal] = None
    portfolio_alpha: Optional[Decimal] = None

    # Risk ratios
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    treynor_ratio: Optional[Decimal] = None
    calmar_ratio: Optional[Decimal] = None

    # Drawdown analysis
    max_drawdown: Optional[Decimal] = None
    max_drawdown_duration: Optional[int] = None
    current_drawdown: Optional[Decimal] = None

    # Value at Risk
    var_95_1d: Optional[Decimal] = None
    var_99_1d: Optional[Decimal] = None
    var_95_1m: Optional[Decimal] = None
    var_99_1m: Optional[Decimal] = None

    # Diversification analysis
    concentration_risk: Optional[Decimal] = None
    effective_number_of_assets: Optional[Decimal] = None
    diversification_ratio: Optional[Decimal] = None

    # Correlation analysis
    average_correlation: Optional[Decimal] = None
    max_correlation: Optional[Decimal] = None

    # Risk level assessment
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[Decimal] = None


class PortfolioPerformanceAnalysis(BaseModel):
    """Comprehensive portfolio performance analysis."""

    portfolio_id: int
    analysis_date: datetime
    period_days: int

    # Performance metrics
    total_return: Decimal
    annualized_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None

    # Benchmark comparison
    benchmark_return: Optional[Decimal] = None
    excess_return: Optional[Decimal] = None
    tracking_error: Optional[Decimal] = None
    information_ratio: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None

    # Performance attribution
    asset_contributions: List[dict] = Field(
        ..., description="Asset contribution to performance"
    )
    sector_contributions: List[dict] = Field(
        ..., description="Sector contribution to performance"
    )

    # Performance trends
    performance_trend: str = Field(
        ..., description="Performance trend: improving, declining, stable"
    )
    momentum_score: Optional[Decimal] = Field(None, description="Momentum score")


class PortfolioRebalancingRecommendation(BaseModel):
    """Portfolio rebalancing recommendations."""

    portfolio_id: int
    recommendation_date: datetime

    # Rebalancing trigger
    trigger_reason: str = Field(
        ..., description="Reason for rebalancing recommendation"
    )
    current_drift: Decimal = Field(..., description="Current allocation drift")

    # Recommended actions
    rebalancing_actions: List[dict] = Field(
        ..., description="Recommended buy/sell actions"
    )
    estimated_cost: Optional[Decimal] = Field(
        None, description="Estimated transaction costs"
    )
    tax_impact: Optional[Decimal] = Field(None, description="Estimated tax impact")

    # Expected outcomes
    expected_allocations: List[dict] = Field(
        ..., description="Expected post-rebalancing allocations"
    )
    expected_risk_reduction: Optional[Decimal] = Field(
        None, description="Expected risk reduction"
    )
    expected_return_impact: Optional[Decimal] = Field(
        None, description="Expected return impact"
    )

    # Priority and timing
    priority: str = Field(..., description="Priority: high, medium, low")
    recommended_timing: str = Field(..., description="Recommended timing for execution")
    urgency_score: Optional[Decimal] = Field(None, description="Urgency score 0-100")


# Supporting schemas for analytics responses
class AllocationItem(BaseModel):
    """Portfolio allocation item."""

    asset_id: int = Field(..., description="Asset ID")
    asset_symbol: str = Field(..., description="Asset symbol")
    asset_name: Optional[str] = Field(None, description="Asset name")
    current_percentage: Decimal = Field(
        ..., description="Current allocation percentage"
    )
    target_percentage: Optional[Decimal] = Field(
        None, description="Target allocation percentage"
    )
    current_value: Decimal = Field(..., description="Current value")
    quantity: Optional[Decimal] = Field(None, description="Quantity held")


class AllocationDrift(BaseModel):
    """Allocation drift analysis item."""

    asset_id: int = Field(..., description="Asset ID")
    asset_symbol: str = Field(..., description="Asset symbol")
    current_percentage: Decimal = Field(
        ..., description="Current allocation percentage"
    )
    target_percentage: Decimal = Field(..., description="Target allocation percentage")
    drift_percentage: Decimal = Field(..., description="Drift from target")
    drift_amount: Decimal = Field(..., description="Drift amount in currency")
    requires_rebalancing: bool = Field(..., description="Whether rebalancing is needed")
    recommended_action: Optional[str] = Field(None, description="Recommended action")


class RebalancingAction(BaseModel):
    """Rebalancing action recommendation."""

    asset_id: int = Field(..., description="Asset ID")
    asset_symbol: str = Field(..., description="Asset symbol")
    action_type: str = Field(..., description="Action type: buy, sell, hold")
    current_quantity: Decimal = Field(..., description="Current quantity")
    target_quantity: Decimal = Field(..., description="Target quantity")
    quantity_change: Decimal = Field(..., description="Quantity to buy/sell")
    estimated_cost: Optional[Decimal] = Field(
        None, description="Estimated transaction cost"
    )
    priority: str = Field(..., description="Priority: high, medium, low")


# Missing response schemas for analytics endpoints
class PerformanceSnapshotResponse(BaseModel):
    """Performance snapshot response."""

    id: int = Field(..., description="Snapshot ID")
    portfolio_id: int = Field(..., description="Portfolio ID")
    snapshot_date: datetime = Field(..., description="Snapshot date")
    total_value: Decimal = Field(..., description="Total portfolio value")
    total_cost_basis: Decimal = Field(..., description="Total cost basis")
    total_unrealized_pnl: Decimal = Field(..., description="Total unrealized P&L")
    total_unrealized_pnl_percent: Decimal = Field(
        ..., description="Total unrealized P&L percentage"
    )
    created_at: datetime = Field(..., description="Creation timestamp")


class AssetMetricsResponse(BaseModel):
    """Asset metrics response matching database model."""

    id: int = Field(..., description="Metrics ID")
    asset_id: int = Field(..., description="Asset ID")
    calculation_date: datetime = Field(..., description="Calculation date")

    # Price metrics
    current_price: Decimal = Field(..., description="Current asset price")
    price_change: Optional[Decimal] = Field(None, description="Price change")
    price_change_percent: Optional[Decimal] = Field(
        None, description="Price change percentage"
    )

    # Technical indicators
    sma_20: Optional[Decimal] = Field(None, description="20-day Simple Moving Average")
    sma_50: Optional[Decimal] = Field(None, description="50-day Simple Moving Average")
    sma_200: Optional[Decimal] = Field(
        None, description="200-day Simple Moving Average"
    )
    ema_12: Optional[Decimal] = Field(
        None, description="12-day Exponential Moving Average"
    )
    ema_26: Optional[Decimal] = Field(
        None, description="26-day Exponential Moving Average"
    )

    # Momentum indicators
    rsi: Optional[Decimal] = Field(None, description="Relative Strength Index")
    macd: Optional[Decimal] = Field(None, description="MACD")
    macd_signal: Optional[Decimal] = Field(None, description="MACD Signal")
    macd_histogram: Optional[Decimal] = Field(None, description="MACD Histogram")
    stochastic_k: Optional[Decimal] = Field(None, description="Stochastic %K")
    stochastic_d: Optional[Decimal] = Field(None, description="Stochastic %D")

    # Volatility indicators
    bollinger_upper: Optional[Decimal] = Field(None, description="Bollinger Upper Band")
    bollinger_middle: Optional[Decimal] = Field(
        None, description="Bollinger Middle Band"
    )
    bollinger_lower: Optional[Decimal] = Field(None, description="Bollinger Lower Band")
    atr: Optional[Decimal] = Field(None, description="Average True Range")

    # Volume indicators
    volume_sma: Optional[Decimal] = Field(
        None, description="Volume Simple Moving Average"
    )
    volume_ratio: Optional[Decimal] = Field(None, description="Volume ratio")
    obv: Optional[Decimal] = Field(None, description="On-Balance Volume")

    # Risk metrics
    volatility_20d: Optional[Decimal] = Field(None, description="20-day volatility")
    volatility_60d: Optional[Decimal] = Field(None, description="60-day volatility")
    volatility_252d: Optional[Decimal] = Field(None, description="252-day volatility")
    beta: Optional[Decimal] = Field(None, description="Asset beta")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Asset Sharpe ratio")

    # Performance metrics
    total_return_1m: Optional[Decimal] = Field(None, description="1-month total return")
    total_return_3m: Optional[Decimal] = Field(None, description="3-month total return")
    total_return_1y: Optional[Decimal] = Field(None, description="1-year total return")

    created_at: datetime = Field(..., description="Creation timestamp")


class AllocationAnalysisResponse(BaseModel):
    """Portfolio allocation analysis response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    current_allocations: List[AllocationItem] = Field(
        ..., description="Current allocations"
    )
    target_allocations: List[AllocationItem] = Field(
        ..., description="Target allocations"
    )
    allocation_drift: List[AllocationDrift] = Field(
        ..., description="Allocation drift analysis"
    )
    total_drift_percentage: Decimal = Field(..., description="Total drift percentage")
    rebalancing_needed: bool = Field(..., description="Whether rebalancing is needed")
    analysis_date: datetime = Field(..., description="Analysis date")


class RiskCalculationResponse(BaseModel):
    """Portfolio risk calculation response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    calculation_date: datetime = Field(..., description="Calculation date")
    risk_level: RiskLevel = Field(..., description="Risk level")
    portfolio_volatility: Decimal = Field(..., description="Portfolio volatility")
    var_95: Decimal = Field(..., description="95% Value at Risk")
    var_99: Decimal = Field(..., description="99% Value at Risk")
    expected_shortfall_95: Optional[Decimal] = Field(
        None, description="95% Expected Shortfall"
    )
    expected_shortfall_99: Optional[Decimal] = Field(
        None, description="99% Expected Shortfall"
    )
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    correlation_to_market: Optional[Decimal] = Field(
        None, description="Correlation to market"
    )


class PerformanceComparisonResponse(BaseModel):
    """Portfolio performance comparison response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    period_days: int = Field(..., description="Comparison period in days")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    portfolio_performance: List[dict] = Field(
        ..., description="Portfolio performance data"
    )
    benchmark_performance: Optional[List[dict]] = Field(
        None, description="Benchmark performance data"
    )
