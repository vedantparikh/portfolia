"""
Stock Router
API endpoints for stock data operations with separate endpoints for fresh and local data.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from core.auth.dependencies import (
    get_client_ip,
    get_current_user,
    get_optional_current_user,
)
from core.auth.utils import is_rate_limited
from core.logging_config import (
    get_logger,
    log_api_request,
    log_api_response,
)
from core.schemas.market import MajorIndex, MarketData
from core.schemas.market_data import (
    SymbolSearchResult,
    YFinanceDataResponse,
    YFinancePriceData,
)
from core.services.market_data_service import market_data_service
from core.services.utils import get_major_indices as list_major_indices

logger = get_logger(__name__)

router = APIRouter(tags=["market-data"])


@router.get("/symbols", response_model=List[SymbolSearchResult])
async def get_symbols(
    name: str,
    request: Request,
    current_user=Depends(get_optional_current_user),
):
    """Yahoo matches for a name, ticker or ISIN. Anonymous callers are rate limited."""
    if not current_user:
        client_ip = get_client_ip(request) if request else "unknown"
        if is_rate_limited(
            client_ip, "symbol_search", max_attempts=10, window_seconds=3600
        ):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please authenticate or try again later.",
            )

    quotes = await market_data_service.search_quotes(name)
    if not quotes:
        raise HTTPException(status_code=404, detail="No symbols found")
    return [SymbolSearchResult(**quote) for quote in quotes]


@router.get("/symbol-data", response_model=YFinanceDataResponse)
async def get_symbol_data_fresh(
    name: str,
    request: Request,
    period: str = Query(
        default="max",
        description="Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
    ),
    interval: str = Query(
        default="1d",
        description="Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)",
    ),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user=Depends(get_optional_current_user),
):
    """
    Get fresh stock data for a specific symbol from yfinance API.

    Rate limited for unauthenticated users to prevent abuse.
    """
    # Rate limiting for unauthenticated users
    if not current_user:
        client_ip = get_client_ip(request) if request else "unknown"
        if is_rate_limited(
            client_ip, "fresh_data", max_attempts=5, window_seconds=3600
        ):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please authenticate or try again later.",
            )

    data = await market_data_service.fetch_ticker_data(
        symbol=name,
        period=period,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
    )

    if data is None:
        raise HTTPException(
            status_code=404, detail=f"No fresh data available for symbol {name}"
        )

    price_data = []
    for _, row in data.iterrows():
        price_data.append(
            YFinancePriceData(
                date=row.get("Date", row.name),
                open=row.get("Open"),
                high=row.get("High"),
                low=row.get("Low"),
                close=row.get("Close"),
                volume=row.get("Volume"),
                dividends=row.get("Dividends"),
                stock_splits=row.get("Stock Splits"),
            )
        )

    return YFinanceDataResponse(
        symbol=name.upper(),
        period=period,
        interval=interval,
        source="yfinance_fresh",
        data_points=len(data),
        data=price_data,
    )


@router.get("/stock-latest-data", response_model=List[MarketData])
async def get_stock_latest_data(
    symbols: str,
    request: Request,
    current_user=Depends(get_current_user),
) -> List[Optional[MarketData]]:
    """
    Get the latest stock data for a specific symbol.

    """
    client_ip = get_client_ip(request) if request else "unknown"
    log_api_request(
        logger,
        "GET",
        "/stock-latest-data",
        current_user.id,
        client_ip,
        symbols=symbols,
    )
    start_time = time.time()
    symbols_list = symbols.split(",")
    data = await market_data_service.get_symbols_info(symbols_list)
    response_time = time.time() - start_time
    log_api_response(logger, "GET", "/stock-latest-data", 200, response_time)
    return data


@router.get("/major-indices", response_model=List[MajorIndex])
def get_major_indices(
    request: Request,
    current_user=Depends(get_current_user),
):
    client_ip = get_client_ip(request) if request else "unknown"
    major_indices = list_major_indices()
    log_api_request(
        logger,
        "GET",
        "/major-indices",
        current_user.id,
        client_ip,
    )
    return major_indices
