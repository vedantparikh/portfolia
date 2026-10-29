"""
Market Data Schemas
Pydantic schemas for market data operations and yfinance integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# yfinance Data Schemas
class YFinanceQuoteData(BaseModel):
    """yfinance quote data structure."""

    symbol: str = Field(..., description="Stock symbol")
    short_name: Optional[str] = Field(None, description="Short company name")
    long_name: Optional[str] = Field(None, description="Long company name")
    quote_type: Optional[str] = Field(
        None, description="Quote type (EQUITY, ETF, etc.)"
    )
    currency: Optional[str] = Field(None, description="Currency")
    exchange: Optional[str] = Field(None, description="Exchange")
    market_cap: Optional[int] = Field(None, description="Market capitalization")
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    country: Optional[str] = Field(None, description="Country")
    isin: Optional[str] = Field(None, description="ISIN")
    cusip: Optional[str] = Field(None, description="CUSIP")
    long_description: Optional[str] = Field(None, description="Long description")


class SymbolSearchResult(BaseModel):
    """One Yahoo symbol-search hit."""

    symbol: str = Field(..., description="Stock symbol")
    short_name: Optional[str] = Field(None, description="Short name")
    long_name: Optional[str] = Field(None, description="Long name")
    quote_type: Optional[str] = Field(None, description="Quote type")
    exchange: Optional[str] = Field(None, description="Exchange")
    market: Optional[str] = Field(None, description="Market")
    currency: Optional[str] = Field(None, description="Currency")
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    market_cap: Optional[int] = Field(None, description="Market cap")


# Market Data Quality Schemas
class DataQualityInfo(BaseModel):
    """Market data quality information."""

    symbol: str = Field(..., description="Stock symbol")
    is_fresh: bool = Field(..., description="Whether data is fresh")
    last_updated: Optional[datetime] = Field(None, description="Last update time")
    data_age_days: Optional[float] = Field(None, description="Data age in days")
    data_points: Optional[int] = Field(None, description="Number of data points")
    quality_score: Optional[float] = Field(None, description="Data quality score 0-1")
    missing_days: Optional[int] = Field(None, description="Number of missing days")
    gaps: Optional[List[Dict[str, Any]]] = Field(None, description="Data gaps")


class TickerUpdateResponse(BaseModel):
    """Ticker update response."""

    message: str = Field(..., description="Update message")
    status: str = Field(..., description="Update status")
    last_updated: Optional[datetime] = Field(None, description="Last update time")
    data_age_days: Optional[float] = Field(None, description="Data age in days")


class BulkUpdateResponse(BaseModel):
    """Bulk update response."""

    message: str = Field(..., description="Update message")
    total_tickers: int = Field(..., description="Total tickers processed")
    successful: List[str] = Field(..., description="Successfully updated tickers")
    failed: List[str] = Field(..., description="Failed tickers")
    success_count: int = Field(..., description="Success count")
    failed_count: int = Field(..., description="Failed count")


class ActiveTickersResponse(BaseModel):
    """Active tickers response."""

    active_tickers: List[str] = Field(..., description="List of active tickers")
    count: int = Field(..., description="Number of active tickers")


# Scheduler Status Schemas
class SchedulerStatus(BaseModel):
    """Scheduler status information."""

    is_running: bool = Field(..., description="Whether scheduler is running")
    update_interval_hours: int = Field(..., description="Update interval in hours")
    batch_size: int = Field(..., description="Batch size for updates")


class UpdateLog(BaseModel):
    """Update log entry."""

    ticker: str = Field(..., description="Ticker symbol")
    operation: str = Field(..., description="Operation type")
    status: str = Field(..., description="Operation status")
    timestamp: datetime = Field(..., description="Operation timestamp")
    records_processed: Optional[int] = Field(None, description="Records processed")


class ServiceStatusResponse(BaseModel):
    """Service status response."""

    service_status: str = Field(..., description="Service status")
    scheduler: SchedulerStatus = Field(..., description="Scheduler status")
    recent_operations: List[UpdateLog] = Field(..., description="Recent operations")
    timestamp: datetime = Field(..., description="Response timestamp")


class SchedulerControlResponse(BaseModel):
    """Scheduler control response."""

    message: str = Field(..., description="Response message")
    status: str = Field(..., description="Scheduler status")


class TickerRefreshResponse(BaseModel):
    """Ticker refresh response."""

    message: str = Field(..., description="Refresh message")
    symbol: str = Field(..., description="Ticker symbol")
    status: str = Field(..., description="Refresh status")


class TickerRefreshAllResponse(BaseModel):
    """Ticker refresh all response."""

    message: str = Field(..., description="Refresh message")
    total_tickers: int = Field(..., description="Total tickers")
    successful: List[str] = Field(..., description="Successful tickers")
    failed: List[str] = Field(..., description="Failed tickers")
    success_count: int = Field(..., description="Success count")
    failure_count: int = Field(..., description="Failure count")
    status: str = Field(..., description="Overall status")


# Asset Search Schemas (moved to bottom of file)


# New API Schemas for yfinance-only endpoints
class TickerDataPoint(BaseModel):
    """Single ticker data point."""

    date: str = Field(..., description="Date in ISO format")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: int = Field(..., description="Volume")
    adj_close: float = Field(..., description="Adjusted close price")


class StockSearchResult(BaseModel):
    """Stock search result."""

    symbol: str = Field(..., description="Stock symbol")
    name: Optional[str] = Field(None, description="Company name")
    exchange: Optional[str] = Field(None, description="Exchange")
    currency: Optional[str] = Field(None, description="Currency")
    type: Optional[str] = Field(None, description="Security type")


class StockSearchResponse(BaseModel):
    """Stock search response."""

    query: str = Field(..., description="Search query")
    results: List[StockSearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total results count")


class MarketStatusResponse(BaseModel):
    """Market status response."""

    is_open: Optional[bool] = Field(None, description="Whether market is open")
    current_time_et: Optional[str] = Field(None, description="Current time in ET")
    timezone: str = Field(..., description="Timezone")
    next_open: Optional[str] = Field(None, description="Next market open time")
    next_close: Optional[str] = Field(None, description="Next market close time")
    error: Optional[str] = Field(None, description="Error message if any")


# Missing response schemas for endpoints without response_model


# Asset search response schemas
class AssetSearchResultItem(BaseModel):
    """Single asset search result."""

    id: int = Field(..., description="Asset ID")
    symbol: str = Field(..., description="Asset symbol")
    name: Optional[str] = Field(None, description="Asset name")
    asset_type: Optional[str] = Field(None, description="Asset type")
    sector: Optional[str] = Field(None, description="Sector")
    exchange: Optional[str] = Field(None, description="Exchange")
    country: Optional[str] = Field(None, description="Country")
    currency: Optional[str] = Field(None, description="Currency")
    is_active: bool = Field(..., description="Whether asset is active")


class AssetDetailsResponse(BaseModel):
    """Asset details response."""

    id: int = Field(..., description="Asset ID")
    symbol: str = Field(..., description="Asset symbol")
    name: Optional[str] = Field(None, description="Asset name")
    description: Optional[str] = Field(None, description="Asset description")
    asset_type: Optional[str] = Field(None, description="Asset type")
    sector: Optional[str] = Field(None, description="Sector")
    exchange: Optional[str] = Field(None, description="Exchange")
    country: Optional[str] = Field(None, description="Country")
    currency: Optional[str] = Field(None, description="Currency")
    is_active: bool = Field(..., description="Whether asset is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PopularAssetsResponse(BaseModel):
    """Popular assets response."""

    assets: List[AssetSearchResultItem] = Field(..., description="Popular assets")


class SectorBreakdownItem(BaseModel):
    """Sector breakdown item."""

    sector: str = Field(..., description="Sector name")
    count: int = Field(..., description="Number of assets in sector")
    percentage: float = Field(..., description="Percentage of total assets")


class SectorBreakdownResponse(BaseModel):
    """Sector breakdown response."""

    sectors: List[SectorBreakdownItem] = Field(..., description="Sector breakdown")


class AssetTypeBreakdownItem(BaseModel):
    """Asset type breakdown item."""

    asset_type: str = Field(..., description="Asset type")
    count: int = Field(..., description="Number of assets of this type")
    percentage: float = Field(..., description="Percentage of total assets")


class AssetTypeBreakdownResponse(BaseModel):
    """Asset type breakdown response."""

    types: List[AssetTypeBreakdownItem] = Field(..., description="Asset type breakdown")


class ExchangeBreakdownItem(BaseModel):
    """Exchange breakdown item."""

    exchange: str = Field(..., description="Exchange name")
    count: int = Field(..., description="Number of assets on exchange")
    percentage: float = Field(..., description="Percentage of total assets")


class ExchangeBreakdownResponse(BaseModel):
    """Exchange breakdown response."""

    exchanges: List[ExchangeBreakdownItem] = Field(
        ..., description="Exchange breakdown"
    )


class SearchSuggestionItem(BaseModel):
    """Search suggestion item."""

    symbol: str = Field(..., description="Asset symbol")
    name: Optional[str] = Field(None, description="Asset name")
    asset_type: Optional[str] = Field(None, description="Asset type")


class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response."""

    suggestions: List[SearchSuggestionItem] = Field(
        ..., description="Search suggestions"
    )


# Market Data Summary Schemas
class MarketDataSummary(BaseModel):
    """Market data summary."""

    total_assets: int = Field(..., description="Total assets")
    active_assets: int = Field(..., description="Active assets")
    last_update: Optional[datetime] = Field(None, description="Last update")
    data_quality_score: Optional[float] = Field(
        None, description="Overall data quality"
    )
    coverage_percentage: Optional[float] = Field(
        None, description="Data coverage percentage"
    )
