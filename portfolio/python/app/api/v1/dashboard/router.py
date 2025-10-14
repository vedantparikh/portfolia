"""
Portfolio Dashboard Router
Comprehensive API endpoints for portfolio dashboard functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_active_user
from core.database.connection import get_db
from core.database.models import User
from core.schemas.dashboard import (
    AssetChartData,
    PerformanceChartData,
    PortfolioDashboard,
)
from core.services.portfolio_dashboard_service import PortfolioDashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/portfolios/{portfolio_id}/overview", response_model=PortfolioDashboard)
async def get_portfolio_dashboard_overview(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get comprehensive portfolio dashboard overview."""
    dashboard_service = PortfolioDashboardService(db)

    try:
        overview = await dashboard_service.get_dashboard_overview(
            portfolio_id, current_user.id
        )
        return PortfolioDashboard(**overview)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/portfolios/{portfolio_id}/holdings")
async def get_portfolio_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed portfolio holdings."""
    dashboard_service = PortfolioDashboardService(db)

    try:
        overview = await dashboard_service.get_dashboard_overview(
            portfolio_id, current_user.id
        )
        return {
            "holdings": overview["holdings"],
            "allocation": overview["allocation"],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/portfolios/{portfolio_id}/recent-activity")
async def get_portfolio_recent_activity(
    portfolio_id: int,
    limit: int = Query(
        10, ge=1, le=100, description="Number of recent activities to return"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get recent portfolio activity."""
    dashboard_service = PortfolioDashboardService(db)

    try:
        overview = await dashboard_service.get_dashboard_overview(
            portfolio_id, current_user.id
        )
        return {
            "recent_activity": overview["recent_activity"][:limit],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
