"""
Portfolio Calculations Schemas

Pydantic schemas for portfolio performance calculation responses.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Core performance metrics."""

    cagr: Optional[float] = Field(
        None, description="Annualised TWR (%); the plain TWR under a year"
    )
    xirr: Optional[float] = Field(
        None, description="Money-weighted return per year, XIRR (%)"
    )
    twr: Optional[float] = Field(
        None, description="Time-weighted return over the period (%)"
    )
    mwr: Optional[float] = Field(
        None, description="Money-weighted return over the period (%)"
    )
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


class AvailablePeriod(BaseModel):
    """Available calculation period."""

    period_code: str = Field(..., description="Period code (e.g., '3m', '1y')")
    period_name: str = Field(..., description="Human-readable period name")
    description: str = Field(..., description="Period description")


class AvailablePeriodsResponse(BaseModel):
    """Available calculation periods response."""

    periods: List[AvailablePeriod] = Field(..., description="Available periods")


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


# Error response schemas


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


class SeriesPoint(BaseModel):
    """One trading day of the portfolio value history."""

    date: date
    value: float = Field(..., description="Market value at the close")
    invested: float = Field(
        ...,
        description="Value at the period start plus deposits minus withdrawals since",
    )
    cost_basis: float = Field(..., description="FIFO cost of the open positions")
    stale_price: bool = Field(
        False,
        description="A holding is valued at a close more than 5 sessions old",
    )
    stale_symbols: List[str] = Field(default_factory=list)


class DayReturn(BaseModel):
    date: date
    return_pct: float


class PeriodSummary(BaseModel):
    """Performance over one period, from the same daily series as the chart."""

    start_date: date
    end_date: date
    trading_days: int
    start_value: float = Field(..., description="Value at the close before the period")
    end_value: float
    deposits: float
    withdrawals: float = Field(..., description="Sale proceeds and dividends")
    net_contributions: float
    profit: float = Field(..., description="end - start - net contributions")
    twr_pct: Optional[float] = Field(None, description="Time-weighted return (%)")
    twr_annualized_pct: Optional[float] = Field(
        None, description="Annualised TWR (%), periods of a year or more"
    )
    mwr_pct: Optional[float] = Field(
        None, description="Money-weighted return over the period (%)"
    )
    mwr_annualized_pct: Optional[float] = Field(
        None, description="Money-weighted return, XIRR (%)"
    )
    volatility_pct: Optional[float] = Field(None, description="Annualised (%)")
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    best_day: Optional[DayReturn] = None
    worst_day: Optional[DayReturn] = None


class PerformanceSeriesResponse(BaseModel):
    portfolio_id: int
    period: str
    points: List[SeriesPoint]
    summary: Optional[PeriodSummary] = None
    error: Optional[str] = None


class BenchmarkOption(BaseModel):
    symbol: str
    name: str


class BenchmarkOptionsResponse(BaseModel):
    currency: str
    options: List[BenchmarkOption]


class BenchmarkInfo(BaseModel):
    symbol: str
    name: str
    currency: Optional[str] = None


class BenchmarkPoint(BaseModel):
    date: date
    value: float = Field(..., description="Portfolio value at the close")
    benchmark_value: float = Field(
        ..., description="Value of the same cash flows invested in the benchmark"
    )
    invested: float = Field(
        ...,
        description="Value at the period start plus deposits minus withdrawals since",
    )
    stale_price: bool = False
    stale_symbols: List[str] = Field(default_factory=list)


class BenchmarkComparisonResponse(BaseModel):
    """The portfolio next to a shadow portfolio that put the same money into the benchmark."""

    portfolio_id: int
    period: str
    benchmark: BenchmarkInfo
    points: List[BenchmarkPoint]
    portfolio: Optional[PeriodSummary] = None
    shadow: Optional[PeriodSummary] = Field(
        None,
        description="Same flows invested in the benchmark; its TWR is the benchmark return",
    )
    difference: Optional["BenchmarkDifference"] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class BenchmarkDifference(BaseModel):
    """Portfolio minus shadow; returns in percentage points."""

    end_value: Optional[float] = None
    profit: Optional[float] = None
    twr_pct: Optional[float] = None
    mwr_pct: Optional[float] = None


class HoldingContribution(BaseModel):
    """One holding's share of the period: profit in money, return in percentage points."""

    asset_id: int
    symbol: str
    name: Optional[str] = None
    start_value: float
    end_value: float
    inflow: float = Field(..., description="Bought in the period, fees included")
    outflow: float = Field(..., description="Sale cash and dividends in the period")
    profit: float = Field(..., description="end − start − inflow + outflow")
    contribution_pp: float = Field(
        ..., description="Share of the period's TWR; all holdings sum to it"
    )
    quote_currency: Optional[str] = Field(
        None, description="Set when quoted in another currency than the portfolio"
    )
    currency_effect: Optional[float] = Field(
        None, description="Part of the profit from the exchange rate"
    )


class CalendarReturnRow(BaseModel):
    period: str = Field(..., description='"2026-03" or "2026"')
    start: date
    end: date
    return_pct: float
    benchmark_pct: Optional[float] = None
    partial: bool = Field(
        ..., description="The period covers only part of the month or year"
    )


class DrawdownEpisode(BaseModel):
    peak_date: date
    trough_date: date
    recovery_date: Optional[date] = None
    depth_pct: float
    days_to_trough: int
    days_to_recover: Optional[int] = Field(
        None, description="Calendar days from peak back to it; null while under"
    )


class DrawdownPoint(BaseModel):
    date: date
    drawdown_pct: float


class DrawdownSummary(BaseModel):
    current_pct: float
    max_pct: float
    episodes: List[DrawdownEpisode]
    points: List[DrawdownPoint]


class TimingEffect(BaseModel):
    """Actual profit against the same flows at the period's steady TWR rate."""

    profit: float
    steady_profit: float
    timing_effect: float
    steady_daily_pct: float


class CurrencyEffectRow(BaseModel):
    currency: str
    effect: float


class CurrencyEffect(BaseModel):
    total: float
    profit: float = Field(..., description="The period's whole profit, for scale")
    by_currency: List[CurrencyEffectRow]


class InsightBenchmark(BaseModel):
    symbol: str
    name: Optional[str] = None
    note: Optional[str] = None
    error: Optional[str] = None


class PerformanceInsightResponse(BaseModel):
    """What drove the period's return (core/domain/insight.py)."""

    portfolio_id: int
    period: str
    currency: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    twr_pct: Optional[float] = None
    contributions: List[HoldingContribution]
    months: List[CalendarReturnRow]
    years: List[CalendarReturnRow]
    drawdown: Optional[DrawdownSummary] = None
    timing: Optional[TimingEffect] = None
    currency_effect: Optional[CurrencyEffect] = None
    benchmark: Optional[InsightBenchmark] = None
    error: Optional[str] = None
