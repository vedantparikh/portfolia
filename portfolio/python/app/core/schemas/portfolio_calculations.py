"""
Portfolio Calculations Schemas

Pydantic schemas for portfolio performance calculation responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Core performance metrics."""

    cagr: Optional[float] = Field(None, description="Compound Annual Growth Rate (%)")
    xirr: Optional[float] = Field(
        None, description="Extended Internal Rate of Return (%)"
    )
    twr: Optional[float] = Field(None, description="Time-Weighted Return (%)")
    mwr: Optional[float] = Field(None, description="Money-Weighted Return (%)")
    volatility: Optional[float] = Field(None, description="Volatility (%)")
    max_drawdown: Optional[float] = Field(None, description="Maximum Drawdown (%)")


class PortfolioPerformanceResponse(BaseModel):
    """Portfolio performance calculation response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    portfolio_name: str = Field(..., description="Portfolio name")
    period: str = Field(..., description="Calculation period")
    start_date: Optional[datetime] = Field(None, description="Period start date")
    end_date: datetime = Field(..., description="Period end date")
    current_value: float = Field(..., description="Current portfolio value")
    metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    calculation_date: datetime = Field(
        ..., description="When calculation was performed"
    )
    error: Optional[str] = Field(
        None, description="Error message if calculation failed"
    )


class AssetPerformanceResponse(BaseModel):
    """Asset performance calculation response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    asset_id: int = Field(..., description="Asset ID")
    asset_symbol: str = Field(..., description="Asset symbol")
    asset_name: str = Field(..., description="Asset name")
    period: str = Field(..., description="Calculation period")
    start_date: Optional[datetime] = Field(None, description="Period start date")
    end_date: datetime = Field(..., description="Period end date")
    current_value: float = Field(..., description="Current asset value in portfolio")
    metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    calculation_date: datetime = Field(
        ..., description="When calculation was performed"
    )
    error: Optional[str] = Field(
        None, description="Error message if calculation failed"
    )


class BenchmarkPerformanceResponse(BaseModel):
    """Benchmark performance calculation response."""

    benchmark_symbol: str = Field(..., description="Benchmark symbol")
    period: str = Field(..., description="Calculation period")
    start_date: Optional[datetime] = Field(None, description="Period start date")
    end_date: datetime = Field(..., description="Period end date")
    current_value: float = Field(..., description="Current hypothetical value")
    metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    calculation_date: datetime = Field(
        ..., description="When calculation was performed"
    )
    error: Optional[str] = Field(
        None, description="Error message if calculation failed"
    )


class ComparisonMetrics(BaseModel):
    """Portfolio vs benchmark comparison metrics."""

    cagr_difference: Optional[float] = Field(
        None, description="CAGR difference (portfolio - benchmark)"
    )
    xirr_difference: Optional[float] = Field(
        None, description="XIRR difference (portfolio - benchmark)"
    )
    twr_difference: Optional[float] = Field(
        None, description="TWR difference (portfolio - benchmark)"
    )
    mwr_difference: Optional[float] = Field(
        None, description="MWR difference (portfolio - benchmark)"
    )
    outperforming: Optional[bool] = Field(
        None, description="Whether portfolio is outperforming benchmark"
    )


class PortfolioBenchmarkComparisonResponse(BaseModel):
    """Portfolio vs benchmark comparison response."""

    portfolio_performance: PortfolioPerformanceResponse = Field(
        ..., description="Portfolio performance"
    )
    benchmark_performance: BenchmarkPerformanceResponse = Field(
        ..., description="Benchmark performance"
    )
    comparison: ComparisonMetrics = Field(..., description="Comparison metrics")


class PeriodPerformanceSummary(BaseModel):
    """Performance summary for a specific period."""

    period: str = Field(..., description="Period identifier")
    period_name: str = Field(..., description="Human-readable period name")
    start_date: Optional[datetime] = Field(None, description="Period start date")
    end_date: datetime = Field(..., description="Period end date")
    metrics: PerformanceMetrics = Field(
        ..., description="Performance metrics for period"
    )


class MultiPeriodPerformanceResponse(BaseModel):
    """Multi-period performance analysis response."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    portfolio_name: str = Field(..., description="Portfolio name")
    periods: List[PeriodPerformanceSummary] = Field(
        ..., description="Performance by period"
    )
    calculation_date: datetime = Field(
        ..., description="When calculation was performed"
    )


class AssetMultiPeriodPerformanceResponse(BaseModel):
    """Multi-period performance analysis response for an asset."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    asset_id: int = Field(..., description="Asset ID")
    asset_symbol: str = Field(..., description="Asset symbol")
    asset_name: str = Field(..., description="Asset name")
    current_value: float = Field(..., description="Current asset value in portfolio")
    periods: List[PeriodPerformanceSummary] = Field(
        ..., description="Performance by period"
    )
    calculation_date: datetime = Field(
        ..., description="When calculation was performed"
    )


class BenchmarkMultiPeriodPerformanceResponse(BaseModel):
    """Multi-period performance analysis response for a benchmark."""

    benchmark_symbol: str = Field(..., description="Benchmark symbol")
    total_invested: float = Field(..., description="Total amount invested")
    current_value: float = Field(..., description="Current hypothetical value")
    periods: List[PeriodPerformanceSummary] = Field(
        ..., description="Performance by period"
    )
    calculation_date: datetime = Field(
        ..., description="When calculation was performed"
    )


class AvailablePeriod(BaseModel):
    """Available calculation period."""

    period_code: str = Field(..., description="Period code (e.g., '3m', '1y')")
    period_name: str = Field(..., description="Human-readable period name")
    description: str = Field(..., description="Period description")


class AvailablePeriodsResponse(BaseModel):
    """Available calculation periods response."""

    periods: List[AvailablePeriod] = Field(..., description="Available periods")


class CalculationStatus(BaseModel):
    """Calculation status response."""

    status: str = Field(..., description="Calculation status")
    message: str = Field(..., description="Status message")
    calculation_id: Optional[str] = Field(
        None, description="Calculation ID for tracking"
    )
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )


class PerformanceCalculationRequest(BaseModel):
    """Request for portfolio performance calculation."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    period: str = Field(..., description="Calculation period")
    end_date: Optional[datetime] = Field(None, description="End date for calculation")
    include_benchmark: Optional[bool] = Field(
        False, description="Include benchmark comparison"
    )
    benchmark_symbol: Optional[str] = Field(
        None, description="Benchmark symbol for comparison"
    )


class AssetPerformanceCalculationRequest(BaseModel):
    """Request for asset performance calculation."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    asset_id: int = Field(..., description="Asset ID")
    period: str = Field(..., description="Calculation period")
    end_date: Optional[datetime] = Field(None, description="End date for calculation")


class BenchmarkPerformanceCalculationRequest(BaseModel):
    """Request for benchmark performance calculation."""

    benchmark_symbol: str = Field(..., description="Benchmark symbol")
    investment_schedule: List[Dict[str, Any]] = Field(
        ..., description="Investment schedule"
    )
    period: str = Field(..., description="Calculation period")
    end_date: Optional[datetime] = Field(None, description="End date for calculation")


class MultiPeriodCalculationRequest(BaseModel):
    """Request for multi-period performance calculation."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    periods: List[str] = Field(..., description="List of periods to calculate")
    end_date: Optional[datetime] = Field(None, description="End date for calculations")
    include_benchmark: Optional[bool] = Field(
        False, description="Include benchmark comparison"
    )
    benchmark_symbol: Optional[str] = Field(
        None, description="Benchmark symbol for comparison"
    )


class PerformanceExportRequest(BaseModel):
    """Request for performance data export."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    periods: List[str] = Field(..., description="Periods to include in export")
    format: str = Field(default="json", description="Export format (json, csv, excel)")
    include_benchmark: Optional[bool] = Field(
        False, description="Include benchmark data"
    )
    benchmark_symbol: Optional[str] = Field(None, description="Benchmark symbol")


class PerformanceExportResponse(BaseModel):
    """Performance data export response."""

    export_id: str = Field(..., description="Export ID")
    download_url: str = Field(..., description="Download URL")
    format: str = Field(..., description="File format")
    size_bytes: int = Field(..., description="File size in bytes")
    expires_at: datetime = Field(..., description="Download link expiration")
    created_at: datetime = Field(..., description="Export creation time")


# Error response schemas


class CalculationError(BaseModel):
    """Calculation error details."""

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class PerformanceCalculationErrorResponse(BaseModel):
    """Performance calculation error response."""

    portfolio_id: Optional[int] = Field(None, description="Portfolio ID")
    asset_id: Optional[int] = Field(None, description="Asset ID")
    benchmark_symbol: Optional[str] = Field(None, description="Benchmark symbol")
    period: Optional[str] = Field(None, description="Calculation period")
    error: CalculationError = Field(..., description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")


# Summary schemas for dashboard/overview


class PortfolioPerformanceSummary(BaseModel):
    """Summary of portfolio performance across all periods."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    portfolio_name: str = Field(..., description="Portfolio name")
    current_value: float = Field(..., description="Current portfolio value")
    total_return: Optional[float] = Field(
        None, description="Total return since inception (%)"
    )
    best_period: Optional[str] = Field(None, description="Best performing period")
    best_period_return: Optional[float] = Field(
        None, description="Best period return (%)"
    )
    worst_period: Optional[str] = Field(None, description="Worst performing period")
    worst_period_return: Optional[float] = Field(
        None, description="Worst period return (%)"
    )
    average_annual_return: Optional[float] = Field(
        None, description="Average annual return (%)"
    )
    volatility: Optional[float] = Field(None, description="Average volatility (%)")
    sharpe_ratio: Optional[float] = Field(None, description="Average Sharpe ratio")
    calculation_date: datetime = Field(..., description="Summary calculation date")


class AssetPerformanceSummary(BaseModel):
    """Summary of asset performance within portfolio."""

    asset_id: int = Field(..., description="Asset ID")
    asset_symbol: str = Field(..., description="Asset symbol")
    asset_name: str = Field(..., description="Asset name")
    current_value: float = Field(..., description="Current asset value")
    weight_in_portfolio: float = Field(..., description="Weight in portfolio (%)")
    total_return: Optional[float] = Field(
        None, description="Total return since first purchase (%)"
    )
    contribution_to_portfolio: Optional[float] = Field(
        None, description="Contribution to portfolio return (%)"
    )
    best_period: Optional[str] = Field(None, description="Best performing period")
    best_period_return: Optional[float] = Field(
        None, description="Best period return (%)"
    )
    calculation_date: datetime = Field(..., description="Summary calculation date")


class PortfolioPerformanceOverview(BaseModel):
    """Comprehensive portfolio performance overview."""

    portfolio_summary: PortfolioPerformanceSummary = Field(
        ..., description="Portfolio summary"
    )
    asset_summaries: List[AssetPerformanceSummary] = Field(
        ..., description="Asset summaries"
    )
    benchmark_comparison: Optional[ComparisonMetrics] = Field(
        None, description="Benchmark comparison"
    )
    top_performers: List[AssetPerformanceSummary] = Field(
        ..., description="Top performing assets"
    )
    worst_performers: List[AssetPerformanceSummary] = Field(
        ..., description="Worst performing assets"
    )
    calculation_date: datetime = Field(..., description="Overview calculation date")
