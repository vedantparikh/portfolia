"""
Portfolio Analytics Router
Comprehensive API endpoints for portfolio analysis, risk management, and performance.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_active_user
from core.database.connection import get_db
from core.database.models import Portfolio, Transaction, User
from core.database.models.portfolio_analytics import (
    AssetCorrelation,
    AssetPerformanceMetrics,
    PortfolioAllocation,
    PortfolioBenchmark,
    PortfolioPerformanceHistory,
    RebalancingEvent,
)
from core.schemas.portfolio_analytics import (
    AllocationAnalysisResponse,
    AssetCorrelationResponse,
    AssetMetricsHistoryResponse,
    AssetMetricsResponse,
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
    RiskCalculationResponse,
    UserAssetsResponse,
    UserDashboardResponse,
)
from core.services.portfolio_analytics_service import PortfolioAnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics")


# Portfolio Performance History
@router.get(
    "/portfolios/{portfolio_id}/performance/snapshot",
    response_model=PerformanceSnapshotResponse,
)
async def get_performance_snapshot(
        portfolio_id: int,
        force_refresh: bool = Query(True, description="Force refresh from yfinance"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get portfolio performance snapshot, always refreshing with yfinance data."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Use force_refresh parameter to ensure latest data
        snapshot = await analytics_service.get_or_create_performance_snapshot(
            portfolio_id, force_refresh
        )
        return snapshot
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.delete(
    "/portfolios/{portfolio_id}/performance/{snapshot_id}",
    response_model=DeleteResponse,
)
async def delete_performance_snapshot(
        portfolio_id: int,
        snapshot_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Delete a performance snapshot."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
        db: Session = Depends(get_db),
):
    """
    Get portfolio performance history.
    This endpoint uses intelligent caching to avoid recalculating fresh data.
    It regenerates history only if it's stale or a new transaction has been added.
    """
    # 1. Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    analytics_service = PortfolioAnalyticsService(db)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        # 2. Determine if a recalculation is necessary
        should_regenerate = False

        # Get the most recently created snapshot for this portfolio
        latest_snapshot = (
            db.query(PortfolioPerformanceHistory)
            .filter(PortfolioPerformanceHistory.portfolio_id == portfolio_id)
            .order_by(PortfolioPerformanceHistory.created_at.desc())
            .first()
        )

        if not latest_snapshot:
            should_regenerate = True
            logger.info(f"No existing history for portfolio {portfolio_id}. Generating.")
        # Check if the last snapshot is from a previous day
        elif latest_snapshot.snapshot_date.date() < end_date.date():
            should_regenerate = True
            logger.info(f"Snapshots are stale (from a previous day) for portfolio {portfolio_id}. Regenerating.")
        else:
            # Snapshots are for today. Now, check for new transactions.
            latest_transaction = (
                db.query(Transaction)
                .filter(Transaction.portfolio_id == portfolio_id)
                .order_by(Transaction.created_at.desc())
                .first()
            )
            # Regenerate if a transaction has been added since the last snapshot was made
            if latest_transaction and latest_transaction.created_at > latest_snapshot.created_at:
                should_regenerate = True
                logger.info(f"New transaction detected for portfolio {portfolio_id}. Regenerating history.")

        # 3. Execute logic: either regenerate or use existing data
        if should_regenerate:
            await analytics_service.generate_historical_performance_snapshots(
                portfolio_id, start_date, end_date
            )
        else:
            logger.info(f"Returning fresh, cached history for portfolio {portfolio_id}.")

        # 4. Query the database one final time to get the definitive history and return it
        final_history = (
            db.query(PortfolioPerformanceHistory)
            .filter(
                PortfolioPerformanceHistory.portfolio_id == portfolio_id,
                PortfolioPerformanceHistory.snapshot_date >= start_date,
            )
            .order_by(PortfolioPerformanceHistory.snapshot_date.desc())
            .all()
        )

        return PortfolioPerformanceHistoryResponse(
            portfolio_id=portfolio_id,
            total_records=len(final_history),
            history=final_history,
        )

    except Exception as e:
        logger.error(f"Failed to get performance history for portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance history: {str(e)}",
        ) from e


# Asset Performance Metrics
@router.get("/assets/{asset_id}/metrics", response_model=AssetMetricsResponse)
async def get_asset_metrics(
        asset_id: int,
        force_refresh: bool = Query(True, description="Force refresh from yfinance"),
        db: Session = Depends(get_db),
):
    """Get asset metrics, always refreshing with latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Use force_refresh parameter to ensure latest data
        metrics = await analytics_service.get_or_calculate_asset_metrics(
            asset_id, force_refresh
        )
        return metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get(
    "/assets/{asset_id}/metrics/history", response_model=AssetMetricsHistoryResponse
)
async def get_asset_metrics_history(
        asset_id: int,
        days: int = Query(30, ge=1, le=10000, description="Number of days to look back"),
        db: Session = Depends(get_db),
):
    """Get asset performance metrics history."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    metrics = (
        db.query(AssetPerformanceMetrics)
        .filter(
            AssetPerformanceMetrics.asset_id == asset_id,
            AssetPerformanceMetrics.calculation_date >= start_date,
        )
        .order_by(AssetPerformanceMetrics.calculation_date.desc())
        .all()
    )

    # Convert to response schemas
    metrics_responses = [
        AssetMetricsResponse(
            id=metric.id,
            asset_id=metric.asset_id,
            calculation_date=metric.calculation_date,
            current_price=metric.current_price,
            price_change=metric.price_change,
            price_change_percent=metric.price_change_percent,
            sma_20=metric.sma_20,
            sma_50=metric.sma_50,
            sma_200=metric.sma_200,
            ema_12=metric.ema_12,
            ema_26=metric.ema_26,
            rsi=metric.rsi,
            macd=metric.macd,
            macd_signal=metric.macd_signal,
            macd_histogram=metric.macd_histogram,
            stochastic_k=metric.stochastic_k,
            stochastic_d=metric.stochastic_d,
            bollinger_upper=metric.bollinger_upper,
            bollinger_middle=metric.bollinger_middle,
            bollinger_lower=metric.bollinger_lower,
            atr=metric.atr,
            volume_sma=metric.volume_sma,
            volume_ratio=metric.volume_ratio,
            obv=metric.obv,
            volatility_20d=metric.volatility_20d,
            volatility_60d=metric.volatility_60d,
            volatility_252d=metric.volatility_252d,
            beta=metric.beta,
            sharpe_ratio=metric.sharpe_ratio,
            total_return_1m=metric.total_return_1m,
            total_return_3m=metric.total_return_3m,
            total_return_1y=metric.total_return_1y,
            created_at=metric.created_at,
        )
        for metric in metrics
    ]

    return AssetMetricsHistoryResponse(
        asset_id=asset_id, total_records=len(metrics), metrics=metrics_responses
    )


# Portfolio Allocation Management
@router.post(
    "/portfolios/{portfolio_id}/allocations",
    response_model=List[PortfolioAllocationResponse],
)
async def set_portfolio_allocations(
        portfolio_id: int,
        allocations: List[PortfolioAllocationCreate],
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Set target allocations for a portfolio."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    analytics_service = PortfolioAnalyticsService(db)
    new_allocations = analytics_service.set_portfolio_allocation(
        portfolio_id, allocations
    )

    return new_allocations


@router.get(
    "/portfolios/{portfolio_id}/allocations",
    response_model=List[PortfolioAllocationResponse],
)
async def get_portfolio_allocations(
        portfolio_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get portfolio target allocations."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
async def update_portfolio_allocation(
        portfolio_id: int,
        allocation_id: int,
        allocation_data: PortfolioAllocationCreate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Update a specific portfolio allocation."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
async def delete_portfolio_allocation(
        portfolio_id: int,
        allocation_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Delete a portfolio allocation."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
        db: Session = Depends(get_db),
):
    """Analyze portfolio allocation and detect drift, always using latest yfinance data."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
        force_refresh: bool = Query(True, description="Force refresh from yfinance"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get portfolio risk metrics, always refreshing with latest yfinance data."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Use force_refresh parameter to ensure latest data
        risk_metrics = await analytics_service.get_or_calculate_portfolio_risk_metrics(
            portfolio_id, force_refresh
        )
        return risk_metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


# Portfolio Benchmarks
@router.post(
    "/portfolios/{portfolio_id}/benchmarks", response_model=PortfolioBenchmarkResponse
)
async def add_portfolio_benchmark(
        portfolio_id: int,
        benchmark_data: PortfolioBenchmarkCreate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Add a benchmark to a portfolio."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
async def get_portfolio_benchmarks(
        portfolio_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get portfolio benchmarks."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
async def create_rebalancing_event(
        portfolio_id: int,
        event_data: RebalancingEventCreate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Create a rebalancing event for a portfolio."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
async def get_rebalancing_events(
        portfolio_id: int,
        days: int = Query(90, ge=1, le=10000, description="Number of days to look back"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get rebalancing events for a portfolio."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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
        db: Session = Depends(get_db),
):
    """Get comprehensive portfolio analytics summary, always refreshing with latest yfinance data."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Force refresh all portfolio data before getting summary
        if force_refresh:
            await analytics_service.force_refresh_all_portfolio_data(portfolio_id)

        summary = await analytics_service.get_portfolio_analytics_summary(portfolio_id)
        return PortfolioAnalyticsSummary(**summary)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get(
    "/portfolios/{portfolio_id}/rebalancing/recommendations",
    response_model=PortfolioRebalancingRecommendation,
)
async def get_rebalancing_recommendations(
        portfolio_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get rebalancing recommendations for a portfolio."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    analytics_service = PortfolioAnalyticsService(db)
    recommendation = await analytics_service.get_rebalancing_recommendation(
        portfolio_id
    )

    return PortfolioRebalancingRecommendation(**recommendation)


# Asset Correlations
@router.get("/assets/correlations", response_model=List[AssetCorrelationResponse])
async def get_asset_correlations(
        asset1_id: Optional[int] = Query(None, description="First asset ID"),
        asset2_id: Optional[int] = Query(None, description="Second asset ID"),
        force_refresh: bool = Query(True, description="Force refresh from yfinance"),
        db: Session = Depends(get_db),
):
    """Get asset correlations, always refreshing with latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    if asset1_id and asset2_id:
        # Get specific correlation between two assets
        try:
            # Use force_refresh parameter to ensure latest data
            correlation = await analytics_service.get_or_calculate_asset_correlation(
                asset1_id, asset2_id, force_refresh
            )
            return [correlation]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
    else:
        # Get historical correlations and refresh recent ones
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        query = db.query(AssetCorrelation).filter(
            AssetCorrelation.calculation_date >= start_date,
        )

        if asset1_id:
            query = query.filter(AssetCorrelation.asset1_id == asset1_id)
        if asset2_id:
            query = query.filter(AssetCorrelation.asset2_id == asset2_id)

        correlations = query.order_by(AssetCorrelation.calculation_date.desc()).all()

        # If force refresh and we have specific assets, update their correlations
        if force_refresh and asset1_id and correlations:
            try:
                # Update correlations for the specific asset with other assets
                for correlation in correlations[:5]:  # Limit to 5 most recent
                    other_asset_id = correlation.asset2_id if correlation.asset1_id == asset1_id else correlation.asset1_id
                    await analytics_service.get_or_calculate_asset_correlation(
                        asset1_id, other_asset_id, True
                    )
            except Exception:
                pass  # Continue even if refresh fails

        return correlations


# Performance Comparison
@router.get(
    "/portfolios/{portfolio_id}/performance/comparison",
    response_model=PerformanceComparisonResponse,
)
async def get_portfolio_performance_comparison(
        portfolio_id: int,
        benchmark_id: Optional[int] = Query(None, description="Benchmark asset ID"),
        days: int = Query(30, ge=1, le=10000, description="Number of days to compare"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get portfolio performance comparison with benchmark."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

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

    # Get benchmark performance if specified
    benchmark_history = None
    if benchmark_id:
        benchmark_history = (
            db.query(AssetPerformanceMetrics)
            .filter(
                AssetPerformanceMetrics.asset_id == benchmark_id,
                AssetPerformanceMetrics.calculation_date >= start_date,
            )
            .order_by(AssetPerformanceMetrics.calculation_date)
            .all()
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

    if benchmark_history:
        comparison_data["benchmark_performance"] = [
            {
                "date": metric.calculation_date,
                "total_return": float(
                    metric.total_return_1m or 0
                ),  # Using 1-month return as proxy
                "volatility": float(metric.volatility_20d or 0),
            }
            for metric in benchmark_history
        ]

    return comparison_data


# Analytics All Endpoint - Update All Portfolio Data
@router.post("/all", status_code=status.HTTP_200_OK)
async def update_all_analytics(
        _force_refresh: bool = Query(False, description="Force refresh all data from yfinance"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Update all analytics data using yfinance and respond with updated calculations."""
    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Get all user portfolios
        user_portfolios = (
            db.query(Portfolio)
            .filter(
                Portfolio.user_id == current_user.id,
                Portfolio.is_active == True,
            )
            .all()
        )

        # Get all user assets
        from app.core.database.models import Asset
        user_assets = (
            db.query(Asset)
            .filter(Asset.user_id == current_user.id, Asset.is_active == True)
            .all()
        )

        updated_data = {
            "user_id": current_user.id,
            "update_timestamp": datetime.now(timezone.utc),
            "portfolios_updated": 0,
            "assets_updated": 0,
            "errors": [],
            "portfolio_summaries": [],
            "asset_metrics": []
        }

        # Update asset metrics for all user assets
        for asset in user_assets:
            try:
                if asset.symbol:  # Only update assets with symbols
                    asset_metrics = await analytics_service.get_or_calculate_asset_metrics(
                        asset.id, force_refresh=True
                    )
                    updated_data["asset_metrics"].append({
                        "asset_id": asset.id,
                        "symbol": asset.symbol,
                        "current_price": float(asset_metrics.current_price) if asset_metrics.current_price else None,
                        "price_change_percent": float(
                            asset_metrics.price_change_percent) if asset_metrics.price_change_percent else None,
                        "updated": True
                    })
                    updated_data["assets_updated"] += 1
            except (ValueError, RuntimeError) as e:
                updated_data["errors"].append(f"Asset {asset.symbol}: {str(e)}")

        # Update portfolio analytics for all user portfolios
        for portfolio in user_portfolios:
            try:
                # Update performance snapshot
                await analytics_service.get_or_create_performance_snapshot(
                    portfolio.id, force_refresh=True
                )

                # Update risk metrics
                risk_metrics = await analytics_service.get_or_calculate_portfolio_risk_metrics(
                    portfolio.id, force_refresh=True
                )

                # Get comprehensive summary
                portfolio_summary = await analytics_service.get_portfolio_analytics_summary(portfolio.id)

                updated_data["portfolio_summaries"].append({
                    "portfolio_id": portfolio.id,
                    "portfolio_name": portfolio.name,
                    "total_value": float(portfolio_summary["total_value"]) if portfolio_summary["total_value"] else 0,
                    "total_unrealized_pnl": float(portfolio_summary["total_unrealized_pnl"]) if portfolio_summary[
                        "total_unrealized_pnl"] else 0,
                    "total_unrealized_pnl_percent": float(portfolio_summary["total_unrealized_pnl_percent"]) if
                    portfolio_summary["total_unrealized_pnl_percent"] else 0,
                    "risk_level": risk_metrics.risk_level if hasattr(risk_metrics, 'risk_level') else None,
                    "portfolio_volatility": float(risk_metrics.portfolio_volatility) if hasattr(risk_metrics,
                                                                                                'portfolio_volatility') and risk_metrics.portfolio_volatility else None,
                    "updated": True
                })
                updated_data["portfolios_updated"] += 1

            except (ValueError, RuntimeError) as e:
                updated_data["errors"].append(f"Portfolio {portfolio.name}: {str(e)}")

        # Update correlations for pairs of user assets (limit to prevent too many calculations)
        if len(user_assets) >= 2:
            asset_pairs_to_update = min(10, len(user_assets) * (len(user_assets) - 1) // 2)  # Limit to 10 pairs
            pairs_updated = 0

            for i, asset1 in enumerate(user_assets[:5]):  # Limit to first 5 assets
                for asset2 in user_assets[i + 1:6]:  # Pair with next 5 assets
                    if pairs_updated >= asset_pairs_to_update:
                        break
                    try:
                        if asset1.symbol and asset2.symbol:
                            await analytics_service.get_or_calculate_asset_correlation(
                                asset1.id, asset2.id, force_refresh=True
                            )
                            pairs_updated += 1
                    except (ValueError, RuntimeError) as e:
                        updated_data["errors"].append(f"Correlation {asset1.symbol}-{asset2.symbol}: {str(e)}")

        # Calculate summary statistics
        total_portfolio_value = sum(
            p["total_value"] for p in updated_data["portfolio_summaries"]
        )
        total_unrealized_pnl = sum(
            p["total_unrealized_pnl"] for p in updated_data["portfolio_summaries"]
        )

        updated_data["summary"] = {
            "total_portfolio_value": total_portfolio_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_unrealized_pnl_percent": (
                    total_unrealized_pnl / (total_portfolio_value - total_unrealized_pnl) * 100) if (
                                                                                                            total_portfolio_value - total_unrealized_pnl) > 0 else 0,
            "assets_with_current_data": len(
                [a for a in updated_data["asset_metrics"] if a["current_price"] is not None]),
            "successful_updates": updated_data["portfolios_updated"] + updated_data["assets_updated"],
            "total_errors": len(updated_data["errors"])
        }

        return {
            "message": "Analytics data updated successfully",
            "data": updated_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update analytics data: {str(e)}",
        ) from e


# User Analytics Dashboard
@router.get("/users/dashboard", response_model=UserDashboardResponse)
async def get_user_analytics_dashboard(
        force_refresh: bool = Query(True, description="Force refresh from yfinance"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get comprehensive analytics dashboard for the current user, always refreshing with latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Force refresh user assets and portfolios before getting dashboard
        if force_refresh:
            try:
                # Get all user assets and refresh their data
                from app.core.database.models import Asset
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
                        await analytics_service.force_refresh_all_portfolio_data(portfolio.id)
                    except Exception as e:
                        logger.warning(f"Failed to refresh portfolio {portfolio.id}: {e}")

            except Exception as e:
                logger.warning(f"Failed to refresh user data: {e}")

        dashboard_data = await analytics_service.get_analytics_dashboard_summary(
            current_user.id
        )
        return dashboard_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics dashboard: {str(e)}",
        ) from e


@router.get("/users/assets", response_model=UserAssetsResponse)
async def get_user_assets_analytics(
        force_refresh: bool = Query(True, description="Force refresh from yfinance"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get analytics for all user assets, always refreshing with latest yfinance data."""
    analytics_service = PortfolioAnalyticsService(db)

    try:
        # Force refresh user assets before getting analytics
        if force_refresh:
            try:
                from app.core.database.models import Asset
                user_assets = (
                    db.query(Asset)
                    .filter(Asset.user_id == current_user.id, Asset.is_active == True)
                    .all()
                )

                asset_ids = [asset.id for asset in user_assets if asset.symbol]
                if asset_ids:
                    await analytics_service.bulk_update_asset_prices(asset_ids)

            except Exception as e:
                logger.warning(f"Failed to refresh user assets: {e}")

        assets_data = await analytics_service.get_user_assets_for_analytics(
            current_user.id
        )
        return {
            "user_id": current_user.id,
            "total_assets": len(assets_data),
            "assets": assets_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user assets analytics: {str(e)}",
        ) from e
