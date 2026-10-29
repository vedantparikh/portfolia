"""
Portfolio Performance Schemas
Pydantic schemas for portfolio performance and analytics.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class PortfolioPerformance(BaseModel):
    """Portfolio performance metrics."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    period_days: int = Field(..., description="Performance period in days")
    total_return: Decimal = Field(..., description="Total return")
    annualized_return: Optional[Decimal] = Field(None, description="Annualized return")
    volatility: Optional[Decimal] = Field(None, description="Volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    alpha: Optional[Decimal] = Field(None, description="Portfolio alpha")
    calculation_date: datetime = Field(..., description="Calculation date")


class PortfolioRefreshResponse(BaseModel):
    """Portfolio refresh response."""

    message: str = Field(..., description="Refresh message")


class BulkAddResponse(BaseModel):
    """Bulk add response."""

    added_items: List[str] = Field(..., description="Successfully added items")
    failed_symbols: List[dict] = Field(..., description="Failed symbols with errors")
    total_requested: int = Field(..., description="Total requested")
    successfully_added: int = Field(..., description="Successfully added count")
    failed: int = Field(..., description="Failed count")


class ReorderResponse(BaseModel):
    """Reorder response."""

    message: str = Field(..., description="Reorder message")


class DeleteResponse(BaseModel):
    """Delete response."""

    message: str = Field(..., description="Delete message")


class WatchlistBulkAddResponse(BaseModel):
    """Watchlist bulk add response."""

    added_items: List[str] = Field(..., description="Successfully added items")
    failed_symbols: List[dict] = Field(..., description="Failed symbols with errors")
    total_requested: int = Field(..., description="Total requested")
    successfully_added: int = Field(..., description="Successfully added count")
    failed: int = Field(..., description="Failed count")


class WatchlistReorderResponse(BaseModel):
    """Watchlist reorder response."""

    message: str = Field(..., description="Reorder message")


class WatchlistDeleteResponse(BaseModel):
    """Watchlist delete response."""

    message: str = Field(..., description="Delete message")


class WatchlistItemDeleteResponse(BaseModel):
    """Watchlist item delete response."""

    message: str = Field(..., description="Delete message")


# Analytics Response Schemas
class AnalyticsSummaryResponse(BaseModel):
    """Analytics summary response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    portfolio_name: str = Field(..., description="Portfolio name")
    calculation_date: datetime = Field(..., description="Calculation date")

    # Basic metrics
    total_value: Decimal = Field(..., description="Total portfolio value")
    total_cost_basis: Decimal = Field(..., description="Total cost basis")
    total_unrealized_pnl: Decimal = Field(..., description="Total unrealized P&L")
    total_unrealized_pnl_percent: Decimal = Field(
        ..., description="Total unrealized P&L percentage"
    )

    # Performance metrics
    total_return: Optional[Decimal] = Field(None, description="Total return")
    annualized_return: Optional[Decimal] = Field(None, description="Annualized return")
    volatility: Optional[Decimal] = Field(None, description="Volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")

    # Risk metrics
    risk_level: Optional[str] = Field(None, description="Risk level")
    risk_score: Optional[Decimal] = Field(None, description="Risk score")
    var_95_1d: Optional[Decimal] = Field(None, description="95% VaR 1-day")
    beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    alpha: Optional[Decimal] = Field(None, description="Portfolio alpha")

    # Diversification metrics
    concentration_risk: Optional[Decimal] = Field(
        None, description="Concentration risk"
    )
    effective_number_of_assets: Optional[Decimal] = Field(
        None, description="Effective number of assets"
    )
    diversification_ratio: Optional[Decimal] = Field(
        None, description="Diversification ratio"
    )

    # Benchmark comparison
    benchmark_name: Optional[str] = Field(None, description="Benchmark name")
    excess_return: Optional[Decimal] = Field(None, description="Excess return")
    tracking_error: Optional[Decimal] = Field(None, description="Tracking error")
    information_ratio: Optional[Decimal] = Field(None, description="Information ratio")


class PerformanceComparisonResponse(BaseModel):
    """Performance comparison response."""

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


class RebalancingRecommendationResponse(BaseModel):
    """Rebalancing recommendation response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    recommendation_date: datetime = Field(..., description="Recommendation date")

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


class AllocationAnalysisResponse(BaseModel):
    """Allocation analysis response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    analysis_date: datetime = Field(..., description="Analysis date")

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


class RiskAnalysisResponse(BaseModel):
    """Risk analysis response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    analysis_date: datetime = Field(..., description="Analysis date")

    # Risk metrics
    portfolio_volatility: Decimal = Field(..., description="Portfolio volatility")
    portfolio_beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    portfolio_alpha: Optional[Decimal] = Field(None, description="Portfolio alpha")

    # Risk ratios
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    treynor_ratio: Optional[Decimal] = Field(None, description="Treynor ratio")
    calmar_ratio: Optional[Decimal] = Field(None, description="Calmar ratio")

    # Drawdown analysis
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

    # Diversification analysis
    concentration_risk: Optional[Decimal] = Field(
        None, description="Concentration risk"
    )
    effective_number_of_assets: Optional[Decimal] = Field(
        None, description="Effective number of assets"
    )
    diversification_ratio: Optional[Decimal] = Field(
        None, description="Diversification ratio"
    )

    # Correlation analysis
    average_correlation: Optional[Decimal] = Field(
        None, description="Average correlation"
    )
    max_correlation: Optional[Decimal] = Field(None, description="Maximum correlation")

    # Risk level assessment
    risk_level: Optional[str] = Field(None, description="Risk level")
    risk_score: Optional[Decimal] = Field(None, description="Risk score")
