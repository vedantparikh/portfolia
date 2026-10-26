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

from core.auth.dependencies import get_current_user
from core.database.connection import get_db
from core.errors import NotFoundError, public_message
from core.schemas.portfolio_calculations import (
    AvailablePeriodsResponse,
    BenchmarkComparisonResponse,
    BenchmarkOptionsResponse,
    MultiPeriodPerformanceResponse,
    PerformanceCalculationRequest,
    PerformanceSeriesResponse,
    PortfolioPerformanceOverview,
    PortfolioPerformanceResponse,
)
from core.services.portfolio_calculation_service import (
    BENCHMARKS,
    PortfolioCalculationService,
)
from core.services.utils import PeriodType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios/calculations", tags=["portfolio-calculations"])


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

    except NotFoundError as e:
        raise HTTPException(
            status_code=404, detail=public_message(e, "Portfolio not found")
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=public_message(e, "Invalid request")
        ) from e
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

    except NotFoundError as e:
        raise HTTPException(
            status_code=404, detail=public_message(e, "Portfolio not found")
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=public_message(e, "Invalid request")
        ) from e
    except Exception as e:
        logger.error(f"Error calculating portfolio performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/portfolio/{portfolio_id}/performance/series",
    response_model=PerformanceSeriesResponse,
)
async def get_performance_series(
    portfolio_id: int,
    period: str = Query(default=PeriodType.LAST_1_YEAR, description="Period code"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Daily value, net invested and cost basis plus the period's returns and risk."""
    try:
        PeriodType.get_start_date(period)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown period") from None
    try:
        service = PortfolioCalculationService(db)
        return await service.get_performance_series(
            portfolio_id, current_user.id, period
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Portfolio not found") from None


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


@router.get("/benchmarks", response_model=BenchmarkOptionsResponse)
async def get_benchmark_options(
    currency: str = Query("EUR", min_length=3, max_length=3),
    current_user=Depends(get_current_user),  # noqa: ARG001
):
    """Suggested total-return benchmarks for a portfolio currency."""
    currency = currency.upper()
    return BenchmarkOptionsResponse(
        currency=currency, options=BENCHMARKS.get(currency, [])
    )


@router.get(
    "/portfolio/{portfolio_id}/benchmark", response_model=BenchmarkComparisonResponse
)
async def get_benchmark_comparison(
    portfolio_id: int,
    period: str = Query(default=PeriodType.LAST_1_YEAR, description="Period code"),
    symbol: Optional[str] = Query(
        None, description="Yahoo ticker; default: the portfolio's primary benchmark"
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """The portfolio next to the same cash flows invested in a benchmark."""
    try:
        PeriodType.get_start_date(period)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown period") from None
    try:
        return await PortfolioCalculationService(db).get_benchmark_comparison(
            portfolio_id, current_user.id, period, symbol
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Portfolio not found") from e


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

        portfolio_performance = await service.calculate_portfolio_performance(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            period=PeriodType.INCEPTION,
        )
        current_value = portfolio_performance.get("current_value", 0.0)

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
