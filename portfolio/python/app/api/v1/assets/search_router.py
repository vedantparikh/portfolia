"""
Asset Search Router
Advanced asset search and discovery API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_active_user
from core.database.connection import get_db
from core.database.models import User
from core.database.models.asset import AssetType
from core.schemas.market_data import (
    AssetDetailsResponse,
    AssetSearchResponse,
    AssetTypeBreakdownResponse,
    ExchangeBreakdownResponse,
    PopularAssetsResponse,
    SearchSuggestionsResponse,
    SectorBreakdownResponse,
)
from core.services.asset_search_service import AssetSearchService

router = APIRouter(prefix="/assets/search", tags=["asset-search"])


@router.get("/", response_model=AssetSearchResponse)
async def search_assets(
    q: Optional[str] = Query(
        None, description="Search query for symbol, name, or description"
    ),
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    country: Optional[str] = Query(None, description="Filter by country"),
    sort_by: str = Query("symbol", description="Sort by field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Search assets with advanced filtering and sorting."""
    search_service = AssetSearchService(db)

    try:
        results = search_service.search_assets(
            query=q,
            asset_type=asset_type,
            sector=sector,
            exchange=exchange,
            country=country,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/{asset_id}", response_model=AssetDetailsResponse)
async def get_asset_details(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Get detailed asset information with performance metrics."""
    search_service = AssetSearchService(db)

    try:
        asset_details = search_service.get_asset_details(asset_id)
        if not asset_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
            )
        return asset_details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/popular", response_model=PopularAssetsResponse)
async def get_popular_assets(
    limit: int = Query(
        20, ge=1, le=100, description="Number of popular assets to return"
    ),
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Get popular assets based on portfolio holdings."""
    search_service = AssetSearchService(db)

    try:
        popular_assets = search_service.get_popular_assets(limit)
        return PopularAssetsResponse(assets=popular_assets)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/breakdown/sectors", response_model=SectorBreakdownResponse)
async def get_sector_breakdown(
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Get asset breakdown by sector."""
    search_service = AssetSearchService(db)

    try:
        sector_breakdown = search_service.get_sector_breakdown()
        return SectorBreakdownResponse(sectors=sector_breakdown)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/breakdown/types", response_model=AssetTypeBreakdownResponse)
async def get_asset_type_breakdown(
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Get asset breakdown by type."""
    search_service = AssetSearchService(db)

    try:
        type_breakdown = search_service.get_asset_type_breakdown()
        return AssetTypeBreakdownResponse(types=type_breakdown)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/breakdown/exchanges", response_model=ExchangeBreakdownResponse)
async def get_exchange_breakdown(
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Get asset breakdown by exchange."""
    search_service = AssetSearchService(db)

    try:
        exchange_breakdown = search_service.get_exchange_breakdown()
        return ExchangeBreakdownResponse(exchanges=exchange_breakdown)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions to return"),
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """Get search suggestions based on partial query."""
    search_service = AssetSearchService(db)

    try:
        suggestions = search_service.get_search_suggestions(q, limit)
        return SearchSuggestionsResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
