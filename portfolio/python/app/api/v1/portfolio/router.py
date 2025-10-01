"""
Portfolio management router with full authentication.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import (
    get_current_active_user,
    get_current_verified_user,
)
from app.core.database.connection import get_db
from app.core.database.models import User
from app.core.schemas.portfolio import (
    AssetCreate,
    Portfolio,
    PortfolioAsset,
    PortfolioAssetCreate,
    PortfolioAssetUpdate,
    PortfolioAssetWithDetails,
    PortfolioCreate,
    PortfolioHolding,
    PortfolioPerformance,
    PortfolioStatistics,
    PortfolioSummary,
    PortfolioUpdate,
    Transaction,
    TransactionCreate,
)
from app.core.schemas.portfolio_performance import (
    PortfolioDiscoverResponse,
    PortfolioRefreshResponse,
    PortfolioSearchResponse,
)
from app.core.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("/", response_model=Portfolio, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Create a new portfolio for the authenticated user."""

    portfolio_service = PortfolioService(db)
    new_portfolio = portfolio_service.create_portfolio(
        portfolio_data, user_id=current_user.id
    )
    return new_portfolio


@router.get("/", response_model=List[Portfolio])
async def get_user_portfolios(
    current_user: User = Depends(get_current_active_user),
    include_inactive: bool = Query(False, description="Include inactive portfolios"),
    db: Session = Depends(get_db),
):
    """Get all portfolios for the authenticated user."""
    portfolio_service = PortfolioService(db)
    portfolios = portfolio_service.get_user_portfolios(
        int(current_user.id), include_inactive=include_inactive
    )
    return portfolios


@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific portfolio by ID (user must own it)."""
    portfolio_service = PortfolioService(db)
    portfolio = portfolio_service.get_portfolio(portfolio_id, int(current_user.id))

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return portfolio


@router.put("/{portfolio_id}", response_model=Portfolio)
async def update_portfolio(
    portfolio_id: int,
    portfolio_update: PortfolioUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a portfolio (user must own it)."""
    portfolio_service = PortfolioService(db)
    portfolio = portfolio_service.update_portfolio(
        portfolio_id, portfolio_update, int(current_user.id)
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a portfolio (user must own it)."""
    portfolio_service = PortfolioService(db)
    success = portfolio_service.delete_portfolio(portfolio_id, int(current_user.id))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return None


@router.delete("/{portfolio_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a portfolio and all associated data (user must own it)."""
    portfolio_service = PortfolioService(db)
    success = portfolio_service.hard_delete_portfolio(portfolio_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return None


@router.post(
    "/{portfolio_id}/assets",
    response_model=PortfolioAsset,
    status_code=status.HTTP_201_CREATED,
)
async def add_asset_to_portfolio(
    portfolio_id: int,
    asset_data: PortfolioAssetCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Add an asset to a portfolio (user must own the portfolio)."""
    portfolio_service = PortfolioService(db)
    portfolio_asset = await portfolio_service.add_asset_to_portfolio(
        portfolio_id, asset_data, current_user.id
    )

    if not portfolio_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return portfolio_asset


@router.get("/{portfolio_id}/assets", response_model=List[PortfolioAsset])
async def get_portfolio_assets(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all assets in a portfolio (user must own the portfolio)."""
    portfolio_service = PortfolioService(db)
    assets = portfolio_service.get_portfolio_assets(portfolio_id, current_user.id)
    return assets


@router.get(
    "/{portfolio_id}/assets/details", response_model=List[PortfolioAssetWithDetails]
)
async def get_portfolio_assets_with_details(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get portfolio assets with detailed information including current values and P&L."""
    portfolio_service = PortfolioService(db)
    assets = await portfolio_service.get_portfolio_assets_with_details(
        portfolio_id, current_user.id
    )
    return assets


@router.put("/{portfolio_id}/assets/{asset_id}", response_model=PortfolioAsset)
async def update_portfolio_asset(
    portfolio_id: int,
    asset_id: int,
    asset_update: PortfolioAssetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an asset in a portfolio (user must own the portfolio)."""
    portfolio_service = PortfolioService(db)
    portfolio_asset = await portfolio_service.update_portfolio_asset(
        portfolio_id, asset_id, asset_update, current_user.id
    )

    if not portfolio_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found in portfolio"
        )

    return portfolio_asset


@router.delete(
    "/{portfolio_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_asset_from_portfolio(
    portfolio_id: int,
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove an asset from a portfolio (user must own the portfolio)."""
    portfolio_service = PortfolioService(db)
    success = portfolio_service.remove_asset_from_portfolio(
        portfolio_id, asset_id, current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found in portfolio"
        )

    return None


@router.post(
    "/{portfolio_id}/transactions",
    response_model=Transaction,
    status_code=status.HTTP_201_CREATED,
)
async def add_transaction(
    portfolio_id: int,
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Add a transaction to a portfolio (user must own the portfolio)."""
    portfolio_service = PortfolioService(db)
    transaction = portfolio_service.add_transaction(
        portfolio_id, transaction_data, current_user.id
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return transaction


@router.get("/{portfolio_id}/transactions", response_model=List[Transaction])
async def get_portfolio_transactions(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of transactions to return"
    ),
    offset: int = Query(0, ge=0, description="Number of transactions to skip"),
    db: Session = Depends(get_db),
):
    """Get transactions for a portfolio (user must own the portfolio)."""
    portfolio_service = PortfolioService(db)
    transactions = portfolio_service.get_portfolio_transactions(
        portfolio_id, current_user.id, limit=limit, offset=offset
    )
    return transactions


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get portfolio summary with total value and performance metrics."""
    portfolio_service = PortfolioService(db)
    summary = await portfolio_service.get_portfolio_summary(portfolio_id, current_user.id)

    if not summary.portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return summary


@router.get("/{portfolio_id}/holdings", response_model=List[PortfolioHolding])
async def get_portfolio_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed portfolio holdings with current values and P&L."""
    portfolio_service = PortfolioService(db)
    holdings = await portfolio_service.get_portfolio_holdings(portfolio_id, current_user.id)
    return holdings


@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformance)
async def get_portfolio_performance(
    portfolio_id: int,
    days: int = Query(
        30, ge=1, le=365, description="Number of days for performance calculation"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get portfolio performance metrics over a specified period."""
    portfolio_service = PortfolioService(db)
    performance = portfolio_service.get_portfolio_performance(
        portfolio_id, current_user.id, days=days
    )

    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return performance


@router.post(
    "/{portfolio_id}/refresh",
    response_model=PortfolioRefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_portfolio_values(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Refresh current values and P&L for all assets in a portfolio."""
    portfolio_service = PortfolioService(db)
    success = await portfolio_service.refresh_portfolio_values(portfolio_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return PortfolioRefreshResponse(message="Portfolio values refreshed successfully")


@router.get("/search", response_model=PortfolioSearchResponse)
async def search_portfolios(
    search_term: Optional[str] = Query(
        None, description="Search term for portfolio names"
    ),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Search portfolios with filters."""
    portfolio_service = PortfolioService(db)
    portfolios = portfolio_service.search_portfolios(
        current_user.id, search_term=search_term, currency=currency
    )
    return PortfolioSearchResponse(
        portfolios=portfolios,
        total_count=len(portfolios),
        search_term=search_term,
        currency=currency,
    )


@router.get("/statistics/overview", response_model=PortfolioStatistics)
async def get_portfolio_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get overall portfolio statistics for the authenticated user."""
    portfolio_service = PortfolioService(db)
    statistics = portfolio_service.get_portfolio_statistics(current_user.id)
    return statistics


@router.get("/public/discover", response_model=PortfolioDiscoverResponse)
async def discover_public_portfolios(
    limit: int = Query(50, ge=1, le=100, description="Number of portfolios to return"),
    offset: int = Query(0, ge=0, description="Number of portfolios to skip"),
    db: Session = Depends(get_db),
):
    """Discover public portfolios (no authentication required)."""
    portfolio_service = PortfolioService(db)
    portfolios = portfolio_service.get_public_portfolios(limit=limit, offset=offset)
    return PortfolioDiscoverResponse(
        portfolios=portfolios, total_count=len(portfolios), limit=limit, offset=offset
    )


# Legacy endpoints for backward compatibility
@router.post(
    "/{portfolio_id}/assets/legacy",
    response_model=PortfolioAsset,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def add_asset_to_portfolio_legacy(
    portfolio_id: int,
    asset_data: AssetCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Legacy endpoint: Add an asset to a portfolio using old schema."""
    # Convert AssetCreate to PortfolioAssetCreate
    portfolio_asset_data = PortfolioAssetCreate(
        portfolio_id=portfolio_id,
        asset_id=asset_data.asset_id,
        quantity=asset_data.quantity,
        cost_basis=asset_data.purchase_price,
    )

    portfolio_service = PortfolioService(db)
    portfolio_asset = await portfolio_service.add_asset_to_portfolio(
        portfolio_id, portfolio_asset_data, current_user.id
    )

    if not portfolio_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    return portfolio_asset
