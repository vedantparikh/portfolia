"""
Market Data Router - yfinance only
API endpoints for market data operations using yfinance exclusively.
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth.dependencies import get_current_active_user
from core.schemas.market_data import (
    BulkPricesResponse,
    CurrentPriceResponse,
    MarketStatusResponse,
    StockSearchResponse,
    SupportedIntervalsResponse,
    SupportedPeriodsResponse,
    TickerDataResponse,
    TickerInfoResponse,
)
from core.services.market_data_service import market_data_service
from core.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/ticker/{symbol}", response_model=TickerDataResponse)
async def get_ticker_data(
    symbol: str,
    period: str = Query(
        "max",
        description="Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
    ),
    interval: str = Query(
        "1d",
        description="Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)",
    ),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Get historical market data for a ticker from yfinance.
    """
    try:
        symbol = symbol.upper()

        # Validate period and interval
        valid_periods = market_data_service.get_supported_periods()
        valid_intervals = market_data_service.get_supported_intervals()

        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Supported periods: {', '.join(valid_periods)}",
            )

        if interval not in valid_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Supported intervals: {', '.join(valid_intervals)}",
            )

        # Fetch data from yfinance
        data = await market_data_service.fetch_ticker_data(
            symbol=symbol, period=period, interval=interval
        )

        if data is None or data.empty:
            raise HTTPException(
                status_code=404, detail=f"No data available for symbol {symbol}"
            )

        # Convert DataFrame to list of dictionaries
        data_records = []
        for _, row in data.iterrows():
            data_records.append(
                {
                    "date": row["Date"].isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                    "adj_close": float(row.get("Adj Close", row["Close"])),
                }
            )

        return TickerDataResponse(
            symbol=symbol,
            period=period,
            interval=interval,
            data_points=len(data_records),
            data=data_records,
            source="yfinance",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching data for %s: %s", symbol, e)
        raise HTTPException(
            status_code=500, detail=f"Error fetching data for {symbol}: {str(e)}"
        ) from e


@router.get("/ticker/{symbol}/info", response_model=TickerInfoResponse)
async def get_ticker_info(
    symbol: str,
    _current_user: User = Depends(get_current_active_user),
):
    """
    Get comprehensive ticker information from yfinance.
    """
    try:
        symbol = symbol.upper()

        ticker_info = await market_data_service.get_ticker_info(symbol)

        if not ticker_info:
            raise HTTPException(
                status_code=404, detail=f"No information available for symbol {symbol}"
            )

        return TickerInfoResponse(
            symbol=ticker_info["symbol"],
            name=ticker_info.get("longName") or ticker_info.get("shortName"),
            company_name=ticker_info.get("longName"),
            sector=ticker_info.get("sector"),
            industry=ticker_info.get("industry"),
            exchange=ticker_info.get("exchange"),
            currency=ticker_info.get("currency"),
            market_cap=ticker_info.get("marketCap"),
            current_price=ticker_info.get("currentPrice")
            or ticker_info.get("regularMarketPrice"),
            previous_close=ticker_info.get("previousClose"),
            day_low=ticker_info.get("dayLow"),
            day_high=ticker_info.get("dayHigh"),
            volume=ticker_info.get("volume"),
            avg_volume=ticker_info.get("averageVolume"),
            beta=ticker_info.get("beta"),
            pe_ratio=ticker_info.get("trailingPE"),
            dividend_yield=ticker_info.get("dividendYield"),
            book_value=ticker_info.get("bookValue"),
            earnings_growth=ticker_info.get("earningsGrowth"),
            revenue_growth=ticker_info.get("revenueGrowth"),
            business_summary=ticker_info.get("longBusinessSummary"),
            website=ticker_info.get("website"),
            employees=ticker_info.get("fullTimeEmployees"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting ticker info for %s: %s", symbol, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting ticker info for {symbol}: {str(e)}",
        ) from e


@router.get("/ticker/{symbol}/price", response_model=CurrentPriceResponse)
async def get_current_price(
    symbol: str,
    _current_user: User = Depends(get_current_active_user),
):
    """
    Get current price for a ticker.
    """
    try:
        symbol = symbol.upper()

        price = await market_data_service.get_current_price(symbol)

        if price is None:
            raise HTTPException(
                status_code=404, detail=f"No price data available for symbol {symbol}"
            )

        return CurrentPriceResponse(
            symbol=symbol,
            price=price,
            source="yfinance",
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting price for %s: %s", symbol, e)
        raise HTTPException(
            status_code=500, detail=f"Error getting price for {symbol}: {str(e)}"
        ) from e


@router.get("/prices/bulk", response_model=BulkPricesResponse)
async def get_bulk_prices(
    symbols: List[str] = Query(..., description="List of symbols to get prices for"),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Get current prices for multiple symbols.
    """
    try:
        if not symbols:
            raise HTTPException(status_code=400, detail="No symbols provided")

        if len(symbols) > 50:  # Reasonable limit
            raise HTTPException(status_code=400, detail="Too many symbols (max 50)")

        # Convert to uppercase
        symbols = [s.upper() for s in symbols]

        prices = await market_data_service.get_multiple_current_prices(symbols)

        return BulkPricesResponse(
            prices=prices,
            source="yfinance",
            requested_count=len(symbols),
            successful_count=len([p for p in prices.values() if p is not None]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting bulk prices: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Error getting bulk prices: {str(e)}"
        ) from e


@router.get("/search", response_model=StockSearchResponse)
async def search_symbols(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Search for stock symbols.
    Note: This is a basic implementation that tries the query as a direct symbol.
    """
    try:
        results = await market_data_service.search_symbols(query, limit)

        return StockSearchResponse(
            query=query, results=results, total_count=len(results)
        )

    except Exception as e:
        logger.error("Error searching symbols for '%s': %s", query, e)
        raise HTTPException(
            status_code=500, detail=f"Error searching symbols: {str(e)}"
        ) from e


@router.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status(
    _current_user: User = Depends(get_current_active_user),
):
    """
    Get current market status.
    """
    try:
        status = await market_data_service.get_market_status()

        return MarketStatusResponse(
            is_open=status.get("is_open"),
            current_time_et=status.get("current_time_et"),
            timezone=status.get("timezone", "US/Eastern"),
            next_open=status.get("next_open"),
            next_close=status.get("next_close"),
            error=status.get("error"),
        )

    except Exception as e:
        logger.error("Error getting market status: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Error getting market status: {str(e)}"
        ) from e


@router.get("/supported-periods", response_model=SupportedPeriodsResponse)
async def get_supported_periods(
    _current_user: User = Depends(get_current_active_user),
):
    """Get list of supported period values."""
    return SupportedPeriodsResponse(
        periods=market_data_service.get_supported_periods(),
        description="Supported period values for historical data requests",
    )


@router.get("/supported-intervals", response_model=SupportedIntervalsResponse)
async def get_supported_intervals(
    _current_user: User = Depends(get_current_active_user),
):
    """Get list of supported interval values."""
    return SupportedIntervalsResponse(
        intervals=market_data_service.get_supported_intervals(),
        description="Supported interval values for historical data requests",
    )
