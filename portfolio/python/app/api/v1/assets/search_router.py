"""
Asset Search Router
Advanced asset search and discovery API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_active_user
from core.database.connection import get_db
from core.database.models import User
from core.schemas.market_data import (
    AssetDetailsResponse,
    AssetTypeBreakdownResponse,
    ExchangeBreakdownResponse,
    PopularAssetsResponse,
    SearchSuggestionsResponse,
    SectorBreakdownResponse,
)
from core.services.asset_search_service import AssetSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets/search", tags=["asset-search"])


@router.get("/popular", response_model=PopularAssetsResponse)
def get_popular_assets(
    limit: int = Query(
        20, ge=1, le=100, description="Number of popular assets to return"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get popular assets based on portfolio holdings."""
    search_service = AssetSearchService(db)

    popular_assets = search_service.get_popular_assets(current_user.id, limit)
    return PopularAssetsResponse(assets=popular_assets)


@router.get("/breakdown/sectors", response_model=SectorBreakdownResponse)
def get_sector_breakdown(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get asset breakdown by sector."""
    search_service = AssetSearchService(db)

    sector_breakdown = search_service.get_sector_breakdown(current_user.id)
    return SectorBreakdownResponse(sectors=sector_breakdown)


@router.get("/breakdown/types", response_model=AssetTypeBreakdownResponse)
def get_asset_type_breakdown(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get asset breakdown by type."""
    search_service = AssetSearchService(db)

    type_breakdown = search_service.get_asset_type_breakdown(current_user.id)
    return AssetTypeBreakdownResponse(types=type_breakdown)


@router.get("/breakdown/exchanges", response_model=ExchangeBreakdownResponse)
def get_exchange_breakdown(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get asset breakdown by exchange."""
    search_service = AssetSearchService(db)

    exchange_breakdown = search_service.get_exchange_breakdown(current_user.id)
    return ExchangeBreakdownResponse(exchanges=exchange_breakdown)


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get search suggestions based on partial query."""
    search_service = AssetSearchService(db)

    suggestions = search_service.get_search_suggestions(current_user.id, q, limit)
    return SearchSuggestionsResponse(suggestions=suggestions)


@router.get("/{asset_id}", response_model=AssetDetailsResponse)
def get_asset_details(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed asset information with performance metrics."""
    search_service = AssetSearchService(db)

    asset_details = search_service.get_asset_details(current_user.id, asset_id)
    if not asset_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return asset_details
