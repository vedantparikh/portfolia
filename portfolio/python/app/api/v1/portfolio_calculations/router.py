"""
Portfolio Calculations API Router

Endpoints for comprehensive portfolio performance calculations including:
- CAGR, XIRR, TWR, MWR calculations
- Period-based calculations (3m, 6m, 1y, YTD, etc.)
- Asset-specific calculations
- Benchmark comparisons
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database.connection import get_db
from app.core.schemas.portfolio_calculations import (
    AvailablePeriodsResponse,
    BenchmarkPerformanceCalculationRequest,
    BenchmarkPerformanceResponse,
    MultiPeriodPerformanceResponse,
    PerformanceCalculationRequest,
    PortfolioBenchmarkComparisonResponse,
    PortfolioPerformanceOverview,
    PortfolioPerformanceResponse,
)
from app.core.services.portfolio_calculation_service import (
    PeriodType,
    PortfolioCalculationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculations")


@router.get("/periods", response_model=AvailablePeriodsResponse)
async def get_available_periods():
    """Get list of available calculation periods."""
    periods = [
        {
            "period_code": PeriodType.LAST_3_MONTHS,
            "period_name": "Last 3 Months",
            "description": "Performance over the last 3 months",
        },
        {
            "period_code": PeriodType.LAST_6_MONTHS,
            "period_name": "Last 6 Months",
            "description": "Performance over the last 6 months",
        },
        {
            "period_code": PeriodType.LAST_1_YEAR,
            "period_name": "Last 1 Year",
            "description": "Performance over the last 12 months",
        },
        {
            "period_code": PeriodType.LAST_2_YEARS,
            "period_name": "Last 2 Years",
            "description": "Performance over the last 2 years",
        },
        {
            "period_code": PeriodType.LAST_3_YEARS,
            "period_name": "Last 3 Years",
            "description": "Performance over the last 3 years",
        },
        {
            "period_code": PeriodType.LAST_5_YEARS,
            "period_name": "Last 5 Years",
            "description": "Performance over the last 5 years",
        },
        {
            "period_code": PeriodType.YTD,
            "period_name": "Year to Date",
            "description": "Performance from January 1st to present",
        },
        {
            "period_code": PeriodType.INCEPTION,
            "period_name": "Since Inception",
            "description": "Performance since portfolio creation",
        },
    ]

    return AvailablePeriodsResponse(periods=periods)


@router.post(
    "/portfolio/{portfolio_id}/performance", response_model=PortfolioPerformanceResponse
)
async def calculate_portfolio_performance(
        portfolio_id: int,
        request: PerformanceCalculationRequest,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Calculate comprehensive portfolio performance metrics.

    Calculates CAGR, XIRR, TWR, MWR, volatility, Sharpe ratio, and max drawdown
    for the specified portfolio and period.
    """
    try:
        service = PortfolioCalculationService(db)

        result = await service.calculate_portfolio_performance(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            period=request.period,
            end_date=request.end_date,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return PortfolioPerformanceResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating portfolio performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/portfolio/{portfolio_id}/performance", response_model=PortfolioPerformanceResponse
)
async def get_portfolio_performance(
        portfolio_id: int,
        period: str = Query(default=PeriodType.INCEPTION, description="Calculation period"),
        end_date: Optional[datetime] = Query(None, description="End date for calculation"),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Get portfolio performance metrics for a specific period.

    Query parameter version of portfolio performance calculation.
    """
    try:
        service = PortfolioCalculationService(db)

        result = await service.calculate_portfolio_performance(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            period=period,
            end_date=end_date,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return PortfolioPerformanceResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating portfolio performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/portfolio/{portfolio_id}/multi-period",
    response_model=MultiPeriodPerformanceResponse,
)
async def get_multi_period_performance(
        portfolio_id: int,
        periods: List[str] = Query(
            default=[
                PeriodType.LAST_3_MONTHS,
                PeriodType.LAST_6_MONTHS,
                PeriodType.LAST_1_YEAR,
                PeriodType.YTD,
                PeriodType.INCEPTION,
            ],
            description="List of periods to calculate",
        ),
        end_date: Optional[datetime] = Query(None, description="End date for calculations"),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Calculate portfolio performance across multiple periods.

    Returns performance metrics for all specified periods in a single response.
    """
    try:
        service = PortfolioCalculationService(db)

        # Get portfolio name
        portfolio = service.get_portfolio(portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        period_summaries = []
        period_names = {
            PeriodType.LAST_3_MONTHS: "Last 3 Months",
            PeriodType.LAST_6_MONTHS: "Last 6 Months",
            PeriodType.LAST_1_YEAR: "Last 1 Year",
            PeriodType.LAST_2_YEARS: "Last 2 Years",
            PeriodType.LAST_3_YEARS: "Last 3 Years",
            PeriodType.LAST_5_YEARS: "Last 5 Years",
            PeriodType.YTD: "Year to Date",
            PeriodType.INCEPTION: "Since Inception",
        }

        for period in periods:
            try:
                result = await service.calculate_portfolio_performance(
                    portfolio_id=portfolio_id,
                    user_id=current_user.id,
                    period=period,
                    end_date=end_date,
                )

                if "error" not in result:
                    period_summaries.append(
                        {
                            "period": period,
                            "period_name": period_names.get(period, period),
                            "start_date": result.get("start_date"),
                            "end_date": result.get("end_date"),
                            "metrics": result.get("metrics", {}),
                        }
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to calculate performance for period {period}: {e}"
                )
                continue

        return MultiPeriodPerformanceResponse(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            periods=period_summaries,
            calculation_date=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating multi-period performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/benchmark/performance", response_model=BenchmarkPerformanceResponse)
async def calculate_benchmark_performance(
        request: BenchmarkPerformanceCalculationRequest,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Calculate hypothetical performance if money was invested in benchmark.

    Calculates what the performance would have been if the same investment
    schedule was applied to a benchmark index or stock.
    """
    try:
        service = PortfolioCalculationService(db)

        # Convert investment schedule to datetime tuples
        investment_amounts = []
        for investment in request.investment_schedule:
            investment_amounts.append(
                (
                    datetime.fromisoformat(investment["date"]),
                    float(investment["amount"]),
                )
            )

        result = await service.calculate_benchmark_performance(
            benchmark_symbol=request.benchmark_symbol,
            cash_flows=investment_amounts,
            period=request.period,
            end_date=request.end_date,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return BenchmarkPerformanceResponse(**result)

    except Exception as e:
        logger.error(f"Error calculating benchmark performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/portfolio/{portfolio_id}/compare/{benchmark_symbol}",
    response_model=PortfolioBenchmarkComparisonResponse,
)
async def compare_portfolio_to_benchmark(
        portfolio_id: int,
        benchmark_symbol: str,
        period: str = Query(default=PeriodType.INCEPTION, description="Comparison period"),
        end_date: Optional[datetime] = Query(None, description="End date for comparison"),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Compare portfolio performance to benchmark using same investment schedule.

    Creates a hypothetical investment in the benchmark using the same dates
    and amounts as the actual portfolio transactions, then compares performance.
    """
    try:
        service = PortfolioCalculationService(db)

        result = await service.compare_portfolio_to_benchmark(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            benchmark_symbol=benchmark_symbol,
            period=period,
            end_date=end_date,
        )

        return PortfolioBenchmarkComparisonResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing portfolio to benchmark: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/portfolio/{portfolio_id}/overview", response_model=PortfolioPerformanceOverview
)
async def get_portfolio_performance_overview(
        portfolio_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """
    Get comprehensive portfolio performance overview.

    Returns portfolio summary, asset summaries, top/worst performers,
    and optionally benchmark comparison in a single response.
    """
    try:
        service = PortfolioCalculationService(db)

        # Verify portfolio
        portfolio = service.get_portfolio(portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        # This is a placeholder implementation
        # In a full implementation, you would:
        # 1. Calculate portfolio summary across all periods
        # 2. Get all assets and their individual performance
        # 3. Identify top and worst performers
        # 4. Optionally compare to benchmark

        # For now, return a basic response
        current_value = service.get_current_portfolio_value(portfolio_id)

        # Get basic portfolio performance
        portfolio_performance = await service.calculate_portfolio_performance(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            period=PeriodType.INCEPTION,
        )

        # Create simplified overview
        overview = {
            "portfolio_summary": {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "current_value": current_value,
                "total_return": portfolio_performance.get("metrics", {}).get("twr"),
                "best_period": None,
                "best_period_return": None,
                "worst_period": None,
                "worst_period_return": None,
                "average_annual_return": portfolio_performance.get("metrics", {}).get(
                    "cagr"
                ),
                "volatility": portfolio_performance.get("metrics", {}).get(
                    "volatility"
                ),
                "sharpe_ratio": portfolio_performance.get("metrics", {}).get(
                    "sharpe_ratio"
                ),
                "calculation_date": datetime.now(),
            },
            "asset_summaries": [],
            "benchmark_comparison": None,
            "top_performers": [],
            "worst_performers": [],
            "calculation_date": datetime.now(),
        }

        return PortfolioPerformanceOverview(**overview)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio overview: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
