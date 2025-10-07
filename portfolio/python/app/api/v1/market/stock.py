"""
Stock Router
API endpoints for stock data operations with separate endpoints for fresh and local data.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from yahooquery import search

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
    log_error_with_context,
)
from core.schemas.market import MajorIndex, MarketData
from core.schemas.market_data import (
    SymbolSearchResult,
    YFinanceDataResponse,
    YFinancePriceData,
)
from core.services.market_data_service import market_data_service

logger = get_logger(__name__)

router = APIRouter()


@router.get("/symbols", response_model=List[SymbolSearchResult])
async def get_symbols(
        name: str,
        request: Request,
        current_user=Depends(get_optional_current_user),
):
    """
    Get stock symbols matching the search name.

    Rate limited for unauthenticated users to prevent abuse.
    """
    start_time = time.time()
    client_ip = get_client_ip(request) if request else "unknown"
    user_id = current_user.id if current_user else None

    # Log API request
    log_api_request(
        logger,
        "GET",
        f"/symbols?name={name}",
        str(user_id) if user_id else None,
        client_ip,
        symbol=name,
    )

    logger.info(
        f"🔍 Symbol search initiated for '{name}' | User: {user_id} | IP: {client_ip}"
    )

    # Rate limiting for unauthenticated users
    if not current_user:
        logger.debug(f"Rate limiting check for unauthenticated user | IP: {client_ip}")
        if is_rate_limited(
                client_ip, "symbol_search", max_attempts=10, window_seconds=3600
        ):
            logger.warning(
                f"🚫 Rate limit exceeded for symbol search | IP: {client_ip}"
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please authenticate or try again later.",
            )
        logger.debug(f"Rate limit check passed | IP: {client_ip}")

    try:
        # Search for symbols
        logger.debug(f"Searching for symbols with yahooquery | Query: '{name}'")
        search_start_time = time.time()
        data = search(name)
        search_time = time.time() - search_start_time

        logger.debug(
            f"Yahooquery search completed in {search_time:.4f}s | Results: {len(data.get('quotes', [])) if data and 'quotes' in data else 0}"
        )

        if not data or "quotes" not in data or len(data["quotes"]) == 0:
            logger.info(f"❌ No symbols found for query '{name}'")
            raise HTTPException(status_code=404, detail="No symbols found")

        quotes = data.get("quotes", [])
        if not isinstance(quotes, list):
            logger.error(
                f"🚨 Malformed response from yahooquery | Expected list, got {type(quotes)}"
            )
            raise HTTPException(
                status_code=500, detail="Malformed response from symbol search"
            )

        response_time = time.time() - start_time
        logger.info(
            f"✅ Symbol search successful | Query: '{name}' | Results: {len(quotes)} | Time: {response_time:.4f}s"
        )

        # Log API response
        log_api_response(
            logger,
            "GET",
            f"/symbols?name={name}",
            200,
            response_time,
            results_count=len(quotes),
        )

        # Convert to SymbolSearchResult objects
        search_results = []
        for quote in quotes:
            search_results.append(
                SymbolSearchResult(
                    symbol=quote.get("symbol", ""),
                    short_name=quote.get("shortName") or quote.get("shortname"),
                    long_name=quote.get("longName") or quote.get("longname"),
                    quote_type=quote.get("quoteType") or quote.get("quotetype"),
                    exchange=quote.get("exchDisp")
                             or quote.get("exchdisp")
                             or quote.get("exchange"),
                    market=quote.get("market"),
                    currency=quote.get("currency"),
                    sector=quote.get("sectorDisp") or quote.get("sector"),
                    industry=quote.get("industryDisp") or quote.get("industry"),
                    market_cap=quote.get("marketCap"),
                )
            )

        return search_results

    except HTTPException:
        # Re-raise HTTP exceptions without logging (they're expected)
        raise
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(
            f"❌ Symbol search failed | Query: '{name}' | Error: {str(e)} | Time: {response_time:.4f}s"
        )

        # Log error with context
        log_error_with_context(
            logger, e, f"Symbol search for '{name}'", user_id=user_id, ip=client_ip
        )

        # Log API response
        log_api_response(
            logger, "GET", f"/symbols?name={name}", 500, response_time, error=str(e)
        )

        raise HTTPException(
            status_code=500, detail=f"Error searching for symbols: {str(e)}"
        )


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

    try:
        # Fetch fresh data from yfinance (always max period for comprehensive coverage)
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

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving fresh data for {name}: {str(e)}"
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
    try:
        symbols_list = symbols.split(",")
        data = await market_data_service.get_stock_latest_data(symbols_list)
        response_time = time.time() - start_time
        log_api_response(logger, "GET", "/stock-latest-data", 200, response_time)
        return data
    except Exception as e:
        logger.error(f"Error retrieving latest data for {symbols}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving latest data for {symbols}: {str(e)}",
        )


@router.get("/major-indices", response_model=List[MajorIndex])
async def get_major_indices(
        request: Request,
        current_user=Depends(get_current_user),
):
    client_ip = get_client_ip(request) if request else "unknown"
    major_indices = market_data_service.get_major_indices()
    log_api_request(
        logger,
        "GET",
        "/major-indices",
        current_user.id,
        client_ip,
    )
    return major_indices
