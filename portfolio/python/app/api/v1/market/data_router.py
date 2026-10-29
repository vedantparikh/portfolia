"""
Market Data Router - yfinance only
API endpoints for market data operations using yfinance exclusively.
"""

import logging

from fastapi import APIRouter, Depends

from core.auth.dependencies import get_current_active_user
from core.database.models import User
from core.schemas.market_data import (
    MarketStatusResponse,
)
from core.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status(
    _current_user: User = Depends(get_current_active_user),
):
    """
    Get current market status.
    """
    status = await market_data_service.get_market_status()

    return MarketStatusResponse(
        is_open=status.get("is_open"),
        current_time_et=status.get("current_time_et"),
        timezone=status.get("timezone", "US/Eastern"),
        next_open=status.get("next_open"),
        next_close=status.get("next_close"),
        error=status.get("error"),
    )
