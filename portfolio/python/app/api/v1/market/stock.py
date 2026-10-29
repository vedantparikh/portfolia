"""
Stock Router
API endpoints for stock data operations with separate endpoints for fresh and local data.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

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
from core.schemas.market import MarketData
from core.schemas.market_data import (
    SymbolSearchResult,
)
from core.services.market_data_service import market_data_service

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
