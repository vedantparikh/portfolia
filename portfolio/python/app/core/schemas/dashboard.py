"""
Dashboard Schemas
Pydantic schemas for dashboard data presentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.database.models.portfolio_analytics import RiskLevel


# Dashboard Overview Schemas
class PortfolioOverview(BaseModel):
    """Portfolio overview metrics."""
    
    total_value: float = Field(..., description="Total portfolio value")
    total_cost_basis: float = Field(..., description="Total cost basis")
    total_pnl: float = Field(..., description="Total unrealized P&L")
    total_pnl_percent: float = Field(..., description="Total unrealized P&L percentage")
    asset_count: int = Field(..., description="Number of assets in portfolio")
    last_updated: datetime = Field(..., description="Last update timestamp")


class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics."""
    
    total_return: Optional[float] = Field(None, description="Total return")
    annualized_return: Optional[float] = Field(None, description="Annualized return")
    volatility: Optional[float] = Field(None, description="Portfolio volatility")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    var_95: Optional[float] = Field(None, description="95% Value at Risk")
    beta: Optional[float] = Field(None, description="Portfolio beta")
    alpha: Optional[float] = Field(None, description="Portfolio alpha")


class RiskMetrics(BaseModel):
    """Portfolio risk metrics."""
    
    risk_level: Optional[RiskLevel] = Field(None, description="Risk level")
    risk_score: Optional[float] = Field(None, description="Risk score 0-100")
    portfolio_volatility: Optional[float] = Field(None, description="Portfolio volatility")
    concentration_risk: Optional[float] = Field(None, description="Concentration risk")
    effective_assets: Optional[float] = Field(None, description="Effective number of assets")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    var_95_1d: Optional[float] = Field(None, description="95% VaR 1-day")
    var_99_1d: Optional[float] = Field(None, description="99% VaR 1-day")


class AllocationBreakdown(BaseModel):
    """Portfolio allocation breakdown."""
    
    by_type: Dict[str, float] = Field(..., description="Allocation by asset type")
    by_sector: Dict[str, float] = Field(..., description="Allocation by sector")
    by_asset: List[Dict[str, Any]] = Field(..., description="Individual asset allocations")


class RecentActivity(BaseModel):
    """Recent portfolio activity."""
    
    id: int = Field(..., description="Transaction ID")
    type: str = Field(..., description="Transaction type")
    symbol: str = Field(..., description="Asset symbol")
    asset_name: str = Field(..., description="Asset name")
    quantity: float = Field(..., description="Transaction quantity")
    price: float = Field(..., description="Transaction price")
    total_amount: float = Field(..., description="Total transaction amount")
    date: datetime = Field(..., description="Transaction date")
    fees: float = Field(..., description="Transaction fees")


class PortfolioDashboard(BaseModel):
    """Complete portfolio dashboard data."""
    
    portfolio: Dict[str, Any] = Field(..., description="Portfolio basic information")
    overview: PortfolioOverview = Field(..., description="Portfolio overview metrics")
    performance: PerformanceMetrics = Field(..., description="Performance metrics")
    risk: RiskMetrics = Field(..., description="Risk metrics")
    allocation: AllocationBreakdown = Field(..., description="Allocation breakdown")
    holdings: List[Dict[str, Any]] = Field(..., description="Portfolio holdings")
    recent_activity: List[RecentActivity] = Field(..., description="Recent activity")


# Chart Data Schemas
class ChartDataPoint(BaseModel):
    """Chart data point."""
    
    date: str = Field(..., description="Date in ISO format")
    value: float = Field(..., description="Value at this date")


class PerformanceChartData(BaseModel):
    """Portfolio performance chart data."""
    
    dates: List[str] = Field(..., description="Chart dates")
    values: List[float] = Field(..., description="Portfolio values")
    returns: List[float] = Field(..., description="Daily returns")
    cumulative_returns: List[float] = Field(..., description="Cumulative returns")


class AssetChartData(BaseModel):
    """Asset performance chart data."""
    
    dates: List[str] = Field(..., description="Chart dates")
    prices: List[float] = Field(..., description="Asset prices")
    volumes: List[float] = Field(..., description="Trading volumes")
    returns: List[float] = Field(..., description="Daily returns")


# Asset Search Schemas
class AssetSearchFilters(BaseModel):
    """Asset search filters."""
    
    query: Optional[str] = Field(None, description="Search query")
    asset_type: Optional[str] = Field(None, description="Asset type filter")
    sector: Optional[str] = Field(None, description="Sector filter")
    exchange: Optional[str] = Field(None, description="Exchange filter")
    country: Optional[str] = Field(None, description="Country filter")
    sort_by: str = Field("symbol", description="Sort field")
    sort_order: str = Field("asc", description="Sort order")
    limit: int = Field(50, ge=1, le=1000, description="Result limit")
    offset: int = Field(0, ge=0, description="Result offset")


class AssetWithPerformance(BaseModel):
    """Asset with performance metrics."""
    
    id: int = Field(..., description="Asset ID")
    symbol: str = Field(..., description="Asset symbol")
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")
    currency: str = Field(..., description="Asset currency")
    exchange: Optional[str] = Field(None, description="Exchange")
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    country: Optional[str] = Field(None, description="Country")
    is_active: bool = Field(..., description="Is active")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: Optional[datetime] = Field(None, description="Last update")
    
    # Performance metrics
    current_price: Optional[float] = Field(None, description="Current price")
    price_change: Optional[float] = Field(None, description="Price change")
    price_change_percent: Optional[float] = Field(None, description="Price change percentage")
    rsi: Optional[float] = Field(None, description="RSI")
    macd: Optional[float] = Field(None, description="MACD")
    volatility_20d: Optional[float] = Field(None, description="20-day volatility")
    volatility_60d: Optional[float] = Field(None, description="60-day volatility")
    beta: Optional[float] = Field(None, description="Beta")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    total_return_1m: Optional[float] = Field(None, description="1-month return")
    total_return_3m: Optional[float] = Field(None, description="3-month return")
    total_return_1y: Optional[float] = Field(None, description="1-year return")
    calculation_date: Optional[datetime] = Field(None, description="Metrics calculation date")


class AssetSearchResults(BaseModel):
    """Asset search results."""
    
    assets: List[AssetWithPerformance] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Result limit")
    offset: int = Field(..., description="Result offset")
    has_more: bool = Field(..., description="Has more results")


class SearchSuggestion(BaseModel):
    """Search suggestion."""
    
    symbol: str = Field(..., description="Asset symbol")
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")


class BreakdownItem(BaseModel):
    """Breakdown item."""
    
    name: str = Field(..., description="Item name")
    asset_count: int = Field(..., description="Number of assets")
    portfolio_count: int = Field(..., description="Number of portfolios")


class AssetBreakdowns(BaseModel):
    """Asset breakdowns by various categories."""
    
    sectors: List[BreakdownItem] = Field(..., description="Sector breakdown")
    types: List[BreakdownItem] = Field(..., description="Type breakdown")
    exchanges: List[BreakdownItem] = Field(..., description="Exchange breakdown")


# Popular Assets Schema
class PopularAsset(BaseModel):
    """Popular asset based on portfolio holdings."""
    
    id: int = Field(..., description="Asset ID")
    symbol: str = Field(..., description="Asset symbol")
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")
    sector: Optional[str] = Field(None, description="Sector")
    portfolio_count: int = Field(..., description="Number of portfolios holding this asset")
