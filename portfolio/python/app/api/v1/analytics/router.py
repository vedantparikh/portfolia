"""
Portfolio Analytics Router
Comprehensive API endpoints for portfolio analysis, risk management, and performance.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_active_user, get_owned_portfolio
from core.database.connection import get_db
from core.database.models import Portfolio, User
from core.database.models.portfolio_analytics import (
    PortfolioAllocation,
    PortfolioBenchmark,
    PortfolioPerformanceHistory,
    RebalancingEvent,
)
from core.domain.positions import OversellError
from core.domain.valuation import MissingPriceError
from core.errors import public_message
from core.schemas.portfolio_advance_risk_metrics import AdvanceRiskCalculationResponse
from core.schemas.portfolio_analytics import (
    AllocationAnalysisResponse,
    DeleteResponse,
    PerformanceComparisonResponse,
    PerformanceSnapshotResponse,
    PortfolioAllocationCreate,
    PortfolioAllocationResponse,
    PortfolioAnalyticsSummary,
    PortfolioBenchmarkCreate,
    PortfolioBenchmarkResponse,
    PortfolioPerformanceHistoryResponse,
    PortfolioRebalancingRecommendation,
    RebalancingEventCreate,
    RebalancingEventResponse,
    UserDashboardResponse,
)
from core.schemas.portfolio_risk_metrics import RiskCalculationResponse
from core.services.portfolio_advance_risk_metrics import (
    PortfolioAdvanceRiskMetricsService,
)
from core.services.portfolio_analytics_service import PortfolioAnalyticsService
from core.services.portfolio_calculation_service import PortfolioCalculationService
from core.services.portfolio_risk_metrics_service import PortfolioRiskMetricsService
from core.services.utils import PeriodType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# Portfolio Performance History
@router.get(
    "/portfolios/{portfolio_id}/performance/snapshot",
    response_model=PerformanceSnapshotResponse,
)
async def get_performance_snapshot(
    portfolio_id: int,
    force_refresh: bool = Query(True, description="Force refresh from yfinance"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get portfolio performance snapshot, always refreshing with yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Use force_refresh parameter to ensure latest data
        snapshot = await analytics_service.get_or_create_performance_snapshot(
            portfolio_id, force_refresh
        )
        return snapshot
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_message(e, "Performance snapshot unavailable"),
        ) from e


@router.delete(
    "/portfolios/{portfolio_id}/performance/{snapshot_id}",
    response_model=DeleteResponse,
)
def delete_performance_snapshot(
    portfolio_id: int,
    snapshot_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Delete a performance snapshot."""
    # Find and delete the snapshot
    snapshot = (
        db.query(PortfolioPerformanceHistory)
        .filter(
            PortfolioPerformanceHistory.id == snapshot_id,
            PortfolioPerformanceHistory.portfolio_id == portfolio_id,
        )
        .first()
    )

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found"
        )

    db.delete(snapshot)
    db.commit()

    return {"message": "Performance snapshot deleted successfully"}


@router.get(
    "/portfolios/{portfolio_id}/performance/history",
    response_model=PortfolioPerformanceHistoryResponse,
)
async def get_performance_history(
    portfolio_id: int,
    days: int = Query(30, ge=1, le=10000, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """
    Daily value and FIFO cost basis for the last `days`, newest first, from the
    canonical engine (see /portfolios/calculations/portfolio/{id}/performance/series).
    """
    calculation = PortfolioCalculationService(db)
    end_date = datetime.now(timezone.utc)
    start = (end_date - timedelta(days=days)).date()
    transactions = calculation.get_transactions(portfolio_id, None, end_date)
    if not transactions:
        return PortfolioPerformanceHistoryResponse(
            portfolio_id=portfolio_id, total_records=0, history=[]
        )
    try:
        series = await calculation.get_portfolio_series(transactions, end_date)
    except (MissingPriceError, OversellError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=public_message(e, "Performance history unavailable"),
        ) from e

    def money(x):
        return Decimal(str(round(x, 2)))

    history = []
    for day, row in series[series.index >= pd.Timestamp(start)][::-1].iterrows():
        value, cost = money(row["value"]), money(row["cost_basis"])
        history.append(
            {
                "portfolio_id": portfolio_id,
                "snapshot_date": day.to_pydatetime().replace(tzinfo=timezone.utc),
                "total_value": value,
                "total_cost_basis": cost,
                "total_unrealized_pnl": value - cost,
                "total_unrealized_pnl_percent": (
                    (value - cost) / cost * 100 if cost else Decimal(0)
                ).quantize(Decimal("0.0001")),
            }
        )
    return PortfolioPerformanceHistoryResponse(
        portfolio_id=portfolio_id, total_records=len(history), history=history
    )


# Portfolio Allocation Management
@router.post(
    "/portfolios/{portfolio_id}/allocations",
    response_model=List[PortfolioAllocationResponse],
)
def set_portfolio_allocations(
    portfolio_id: int,
    allocations: List[PortfolioAllocationCreate],
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Set target allocations for a portfolio."""
    analytics_service = PortfolioAnalyticsService(db)
    new_allocations = analytics_service.set_portfolio_allocation(
        portfolio_id, allocations
    )

    return new_allocations


@router.get(
    "/portfolios/{portfolio_id}/allocations",
    response_model=List[PortfolioAllocationResponse],
)
def get_portfolio_allocations(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get portfolio target allocations."""
    allocations = (
        db.query(PortfolioAllocation)
        .filter(
            PortfolioAllocation.portfolio_id == portfolio_id,
            PortfolioAllocation.is_active,
        )
        .all()
    )

    return allocations


@router.put(
    "/portfolios/{portfolio_id}/allocations/{allocation_id}",
    response_model=PortfolioAllocationResponse,
)
def update_portfolio_allocation(
    portfolio_id: int,
    allocation_id: int,
    allocation_data: PortfolioAllocationCreate,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Update a specific portfolio allocation."""
    # Find the allocation
    allocation = (
        db.query(PortfolioAllocation)
        .filter(
            PortfolioAllocation.id == allocation_id,
            PortfolioAllocation.portfolio_id == portfolio_id,
        )
        .first()
    )

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found"
        )

    # Update allocation fields
    allocation.target_percentage = allocation_data.target_percentage
    allocation.min_percentage = allocation_data.min_percentage
    allocation.max_percentage = allocation_data.max_percentage
    allocation.rebalance_threshold = allocation_data.rebalance_threshold
    allocation.rebalance_frequency = allocation_data.rebalance_frequency
    allocation.is_active = allocation_data.is_active

    db.commit()
    db.refresh(allocation)

    return allocation


@router.delete(
    "/portfolios/{portfolio_id}/allocations/{allocation_id}",
    response_model=DeleteResponse,
)
def delete_portfolio_allocation(
    portfolio_id: int,
    allocation_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Delete a portfolio allocation."""
    # Find and delete the allocation
    allocation = (
        db.query(PortfolioAllocation)
        .filter(
            PortfolioAllocation.id == allocation_id,
            PortfolioAllocation.portfolio_id == portfolio_id,
        )
        .first()
    )

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found"
        )

    db.delete(allocation)
    db.commit()

    return {"message": "Portfolio allocation deleted successfully"}


@router.get(
    "/portfolios/{portfolio_id}/allocations/analysis",
    response_model=AllocationAnalysisResponse,
)
async def analyze_portfolio_allocation(
    portfolio_id: int,
    force_refresh: bool = Query(True, description="Force refresh from yfinance"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Analyze portfolio allocation and detect drift, always using latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    # Force refresh portfolio asset prices before analysis
    if force_refresh:
        try:
            await analytics_service.force_refresh_all_portfolio_data(portfolio_id)
        except Exception as e:
            logger.warning(f"Failed to refresh portfolio data: {e}")

    analysis = await analytics_service.analyze_portfolio_allocation(portfolio_id)

    return analysis


# Portfolio Risk Analysis
@router.get("/portfolios/{portfolio_id}/risk", response_model=RiskCalculationResponse)
async def get_portfolio_risk_metrics(
    portfolio_id: int,
    period: str = Query(default=PeriodType.INCEPTION, description="Calculation period"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get portfolio risk metrics."""
    portfolio_risk_metric_service = PortfolioRiskMetricsService(db)

    try:
        # Use force_refresh parameter to ensure latest data
        risk_metrics = (
            await portfolio_risk_metric_service.calculate_portfolio_risk_metrics(
                portfolio_id, period
            )
        )

        return risk_metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_message(e, "Risk metrics unavailable"),
        ) from e


@router.get(
    "/portfolios/{portfolio_id}/advance-risk",
    response_model=AdvanceRiskCalculationResponse,
)
async def get_portfolio_advance_risk_metrics(
    portfolio_id: int,
    period: str = Query(default=PeriodType.INCEPTION, description="Calculation period"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get portfolio advance risk metrics."""
    portfolio_advance_risk_metric_service = PortfolioAdvanceRiskMetricsService(db)

    try:
        advance_risk_metrics = (
            await portfolio_advance_risk_metric_service.calculate_advanced_metrics(
                portfolio_id, period
            )
        )

        return advance_risk_metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_message(e, "Risk metrics unavailable"),
        ) from e


# Portfolio Benchmarks
@router.post(
    "/portfolios/{portfolio_id}/benchmarks", response_model=PortfolioBenchmarkResponse
)
def add_portfolio_benchmark(
    portfolio_id: int,
    benchmark_data: PortfolioBenchmarkCreate,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Add a benchmark to a portfolio."""
    # If this is set as primary, unset other primary benchmarks
    if benchmark_data.is_primary:
        db.query(PortfolioBenchmark).filter(
            PortfolioBenchmark.portfolio_id == portfolio_id
        ).update({"is_primary": False})

    benchmark = PortfolioBenchmark(
        portfolio_id=portfolio_id,
        benchmark_asset_id=benchmark_data.benchmark_asset_id,
        benchmark_name=benchmark_data.benchmark_name,
        benchmark_type=benchmark_data.benchmark_type,
        tracking_error=benchmark_data.tracking_error,
        information_ratio=benchmark_data.information_ratio,
        beta=benchmark_data.beta,
        alpha=benchmark_data.alpha,
        excess_return=benchmark_data.excess_return,
        excess_return_percent=benchmark_data.excess_return_percent,
        is_active=benchmark_data.is_active,
        is_primary=benchmark_data.is_primary,
    )

    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)

    return benchmark


@router.get(
    "/portfolios/{portfolio_id}/benchmarks",
    response_model=List[PortfolioBenchmarkResponse],
)
def get_portfolio_benchmarks(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get portfolio benchmarks."""
    benchmarks = (
        db.query(PortfolioBenchmark)
        .filter(
            PortfolioBenchmark.portfolio_id == portfolio_id,
            PortfolioBenchmark.is_active,
        )
        .all()
    )

    return benchmarks


# Rebalancing Events
@router.post(
    "/portfolios/{portfolio_id}/rebalancing/events",
    response_model=RebalancingEventResponse,
)
def create_rebalancing_event(
    portfolio_id: int,
    event_data: RebalancingEventCreate,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Create a rebalancing event for a portfolio."""
    event = RebalancingEvent(
        portfolio_id=portfolio_id,
        event_date=event_data.event_date,
        event_type=event_data.event_type,
        trigger_reason=event_data.trigger_reason,
        pre_rebalance_value=event_data.pre_rebalance_value,
        pre_rebalance_allocations=event_data.pre_rebalance_allocations,
        rebalancing_actions=event_data.rebalancing_actions,
        post_rebalance_value=event_data.post_rebalance_value,
        post_rebalance_allocations=event_data.post_rebalance_allocations,
        rebalancing_cost=event_data.rebalancing_cost,
        tax_impact=event_data.tax_impact,
        status=event_data.status,
        execution_notes=event_data.execution_notes,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


@router.get(
    "/portfolios/{portfolio_id}/rebalancing/events",
    response_model=List[RebalancingEventResponse],
)
def get_rebalancing_events(
    portfolio_id: int,
    days: int = Query(90, ge=1, le=10000, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get rebalancing events for a portfolio."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    events = (
        db.query(RebalancingEvent)
        .filter(
            RebalancingEvent.portfolio_id == portfolio_id,
            RebalancingEvent.event_date >= start_date,
        )
        .order_by(RebalancingEvent.event_date.desc())
        .all()
    )

    return events


# Comprehensive Analytics
@router.get(
    "/portfolios/{portfolio_id}/summary", response_model=PortfolioAnalyticsSummary
)
async def get_portfolio_analytics_summary(
    portfolio_id: int,
    force_refresh: bool = Query(True, description="Force refresh from yfinance"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get comprehensive portfolio analytics summary, always refreshing with latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Force refresh all portfolio data before getting summary
        if force_refresh:
            await analytics_service.force_refresh_all_portfolio_data(portfolio_id)

        summary = await analytics_service.get_portfolio_analytics_summary(portfolio_id)
        return PortfolioAnalyticsSummary(**summary)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_message(e, "Analytics summary unavailable"),
        ) from e


@router.get(
    "/portfolios/{portfolio_id}/rebalancing/recommendations",
    response_model=PortfolioRebalancingRecommendation,
)
async def get_rebalancing_recommendations(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get rebalancing recommendations for a portfolio."""
    analytics_service = PortfolioAnalyticsService(db)
    recommendation = await analytics_service.get_rebalancing_recommendation(
        portfolio_id
    )

    return PortfolioRebalancingRecommendation(**recommendation)


# Performance Comparison
@router.get(
    "/portfolios/{portfolio_id}/performance/comparison",
    response_model=PerformanceComparisonResponse,
)
def get_portfolio_performance_comparison(
    portfolio_id: int,
    benchmark_id: Optional[int] = Query(None, description="Benchmark asset ID"),
    days: int = Query(30, ge=1, le=10000, description="Number of days to compare"),
    current_user: User = Depends(get_current_active_user),
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
):
    """Get portfolio performance comparison with benchmark."""
    # Get portfolio performance history
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    portfolio_history = (
        db.query(PortfolioPerformanceHistory)
        .filter(
            PortfolioPerformanceHistory.portfolio_id == portfolio_id,
            PortfolioPerformanceHistory.snapshot_date >= start_date,
        )
        .order_by(PortfolioPerformanceHistory.snapshot_date)
        .all()
    )

    if not portfolio_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No performance data found"
        )

    # Build comparison data
    comparison_data = {
        "portfolio_id": portfolio_id,
        "period_days": days,
        "start_date": start_date,
        "end_date": end_date,
        "portfolio_performance": [
            {
                "date": snapshot.snapshot_date,
                "total_return": float(snapshot.cumulative_return or 0),
                "volatility": float(snapshot.volatility or 0),
                "sharpe_ratio": float(snapshot.sharpe_ratio or 0),
            }
            for snapshot in portfolio_history
        ],
    }

    return comparison_data


# User Analytics Dashboard
@router.get("/users/dashboard", response_model=UserDashboardResponse)
async def get_user_analytics_dashboard(
    force_refresh: bool = Query(True, description="Force refresh from yfinance"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get comprehensive analytics dashboard for the current user, always refreshing with latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    if force_refresh:
        try:
            # Get all user assets and refresh their data
            from core.database.models import Asset

            user_assets = (
                db.query(Asset)
                .filter(Asset.user_id == current_user.id, Asset.is_active == True)
                .all()
            )

            asset_ids = [asset.id for asset in user_assets if asset.symbol]
            if asset_ids:
                await analytics_service.bulk_update_asset_prices(asset_ids)

            # Refresh portfolio data for all user portfolios
            user_portfolios = (
                db.query(Portfolio)
                .filter(
                    Portfolio.user_id == current_user.id,
                    Portfolio.is_active == True,
                )
                .all()
            )

            for portfolio in user_portfolios:
                try:
                    await analytics_service.force_refresh_all_portfolio_data(
                        portfolio.id
                    )
                except Exception as e:
                    logger.warning(f"Failed to refresh portfolio {portfolio.id}: {e}")

        except Exception as e:
            logger.warning(f"Failed to refresh user data: {e}")

    dashboard_data = await analytics_service.get_analytics_dashboard_summary(
        current_user.id
    )
    return dashboard_data
