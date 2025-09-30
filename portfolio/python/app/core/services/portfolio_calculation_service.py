"""
Portfolio Calculation Service - Rewritten
Comprehensive service for calculating portfolio performance metrics with focus on:
- CAGR (Compound Annual Growth Rate)
- XIRR (Extended Internal Rate of Return)
- TWR (Time-Weighted Return) - Implemented
- MWR (Money-Weighted Return) - Aliased to XIRR

Supports period-based calculations and benchmark comparisons.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NamedTuple, Optional

import numpy as np
import pandas as pd  # type: ignore
import pyxirr  # type: ignore
from dateutil.relativedelta import relativedelta  # type: ignore
from sqlalchemy.orm import Session

from app.core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionType,
)
from app.core.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class CashFlow(NamedTuple):
    """Represents a cash flow with date and amount."""

    date: datetime
    amount: float  # Positive for inflows, negative for outflows


class PeriodType:
    """Standard period types for calculations."""

    LAST_3_MONTHS = "3m"
    LAST_6_MONTHS = "6m"
    LAST_1_YEAR = "1y"
    LAST_2_YEARS = "2y"
    LAST_3_YEARS = "3y"
    LAST_5_YEARS = "5y"
    YTD = "ytd"
    INCEPTION = "inception"

    @classmethod
    def get_start_date(
            cls, period: str, base_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Get start date for a given period using proper calendar calculations."""
        if base_date is None:
            base_date = datetime.now(timezone.utc)

        if period == cls.LAST_3_MONTHS:
            return base_date - relativedelta(months=3)
        elif period == cls.LAST_6_MONTHS:
            return base_date - relativedelta(months=6)
        elif period == cls.LAST_1_YEAR:
            return base_date - relativedelta(years=1)
        elif period == cls.LAST_2_YEARS:
            return base_date - relativedelta(years=2)
        elif period == cls.LAST_3_YEARS:
            return base_date - relativedelta(years=3)
        elif period == cls.LAST_5_YEARS:
            return base_date - relativedelta(years=5)
        elif period == cls.YTD:
            return datetime(base_date.year, 1, 1, tzinfo=timezone.utc)
        elif period == cls.INCEPTION:
            return None  # No start date filter
        else:
            raise ValueError(f"Unknown period type: {period}")


class PortfolioCalculationService:
    """Service for comprehensive portfolio performance calculations."""

    def __init__(self, db: Session):
        self.db = db
        self.market_data_service = MarketDataService()
        # Cache for price data to avoid multiple API calls
        self._price_cache = {}
        self._price_cache_time = {}

    async def calculate_portfolio_performance(
            self,
            portfolio_id: int,
            user_id: int,
            period: str = PeriodType.INCEPTION,
            end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio performance metrics.

        Args:
            portfolio_id: Portfolio ID
            user_id: User ID for ownership verification
            period: Period for calculation
            end_date: End date for calculation (defaults to now)

        Returns:
            Dictionary containing all performance metrics
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        start_date = PeriodType.get_start_date(period, end_date)

        # Get portfolio and verify ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found or not accessible")

        # Get all transactions for the portfolio
        all_transactions = self._get_transactions(portfolio_id, None, end_date)

        if not all_transactions:
            return self._empty_performance_result(portfolio_id, period)

        # Check portfolio age vs requested period
        first_transaction_date = min(t.transaction_date for t in all_transactions)
        portfolio_age_days = (end_date - first_transaction_date).days

        # Determine if we should use inception period instead
        actual_period = period
        actual_start_date = start_date
        period_adjustment_info = None

        if start_date and first_transaction_date > start_date:
            # Portfolio is younger than requested period
            actual_period = PeriodType.INCEPTION
            actual_start_date = None
            requested_period_days = (end_date - start_date).days
            period_adjustment_info = {
                "requested_period": period,
                "requested_period_days": requested_period_days,
                "portfolio_age_days": portfolio_age_days,
                "adjustment_reason": (
                    f"Portfolio age ({portfolio_age_days} days) is less than "
                    f"requested period ({requested_period_days} days). "
                    "Using inception period instead."
                ),
            }
            logger.info(
                "Portfolio %s: Using inception period instead of %s due to portfolio age",
                portfolio_id,
                period,
            )

        # Get current portfolio value
        current_value, value_errors = self.get_current_portfolio_value(portfolio_id)

        if value_errors:
            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "period": actual_period,
                "start_date": actual_start_date,
                "end_date": end_date,
                "current_value": current_value,
                "errors": value_errors,
                "period_adjustment": period_adjustment_info,
                "metrics": {
                    "cagr": None,
                    "xirr": None,
                    "twr": None,
                    "mwr": None,
                },
                "calculation_date": datetime.now(timezone.utc).isoformat(),
            }
        # Generate daily portfolio value history for risk calculations
        portfolio_history_df = await self._get_portfolio_history(
            portfolio_id, all_transactions, actual_start_date, end_date
        )

        volatility = self._calculate_volatility(portfolio_history_df)
        max_drawdown = self._calculate_max_drawdown(portfolio_history_df)
        # Calculate CAGR
        cagr = await self._calculate_cagr(
            portfolio_id, all_transactions, current_value, actual_start_date, end_date
        )

        # Calculate XIRR
        xirr_value = await self._calculate_xirr(
            portfolio_id, all_transactions, current_value, actual_start_date, end_date
        )

        # Calculate TWR
        twr_value = await self._calculate_twr(
            portfolio_id, all_transactions, current_value, actual_start_date, end_date
        )

        result = {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "period": actual_period,
            "start_date": actual_start_date,
            "end_date": end_date,
            "current_value": current_value,
            "metrics": {
                "cagr": cagr,
                "xirr": xirr_value,
                "twr": twr_value,
                "mwr": xirr_value,  # MWR is essentially XIRR,
                "volatility": volatility,
                "max_drawdown": max_drawdown
            },
            "calculation_date": datetime.now(timezone.utc).isoformat(),
        }

        if period_adjustment_info:
            result["period_adjustment"] = period_adjustment_info

        return result

    async def calculate_benchmark_performance(
            self,
            benchmark_symbol: str,
            cash_flows: List[CashFlow],
            period: str = PeriodType.INCEPTION,
            end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate hypothetical performance if money was invested in benchmark.

        Args:
            benchmark_symbol: Benchmark symbol (e.g., '^GSPC' for S&P 500)
            cash_flows: List of cash flows to apply to benchmark
            period: Period for calculation
            end_date: End date for calculation

        Returns:
            Dictionary containing benchmark performance metrics
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        start_date = PeriodType.get_start_date(period, end_date)

        # Filter cash flows for the period
        if start_date:
            period_cash_flows = [cf for cf in cash_flows if cf.date >= start_date]
        else:
            period_cash_flows = cash_flows

        if not period_cash_flows:
            return self._empty_benchmark_performance_result(benchmark_symbol, period)

        try:
            # Get price data for benchmark
            price_data = await self._get_price_data(benchmark_symbol)
            if price_data.empty:
                raise ValueError(
                    f"No price data available for benchmark {benchmark_symbol}"
                )

            # Calculate current value of benchmark investment
            current_value = self._calculate_benchmark_value(
                cash_flows, price_data, end_date
            )

            # Calculate CAGR
            cagr = await self._calculate_benchmark_cagr(
                cash_flows, price_data, current_value, start_date, end_date
            )

            # Calculate XIRR
            xirr_value = self._calculate_benchmark_xirr(
                period_cash_flows, current_value, start_date, end_date
            )

            # Calculate TWR
            twr_value = await self._calculate_benchmark_twr(
                period_cash_flows, price_data, start_date, end_date
            )

            return {
                "benchmark_symbol": benchmark_symbol,
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "current_value": current_value,
                "metrics": {
                    "cagr": cagr,
                    "xirr": xirr_value,
                    "twr": twr_value,
                    "mwr": xirr_value,
                },
                "calculation_date": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Error calculating benchmark performance: %s", e)
            return self._empty_benchmark_performance_result(benchmark_symbol, period)

    async def compare_portfolio_to_benchmark(
            self,
            portfolio_id: int,
            user_id: int,
            benchmark_symbol: str,
            period: str = PeriodType.INCEPTION,
            end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Compare portfolio performance to benchmark using same cash flows.

        Args:
            portfolio_id: Portfolio ID
            user_id: User ID for ownership verification
            benchmark_symbol: Benchmark symbol
            period: Period for comparison
            end_date: End date for comparison

        Returns:
            Dictionary containing comparison metrics
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        # Get portfolio performance
        portfolio_performance = await self.calculate_portfolio_performance(
            portfolio_id, user_id, period, end_date
        )

        actual_period_for_benchmark = portfolio_performance.get("period", period)

        # Create cash flows from portfolio transactions
        all_transactions = self._get_transactions(portfolio_id, None, end_date)
        cash_flows = self._create_cash_flows_from_transactions(all_transactions)

        # Get benchmark performance with same cash flows
        benchmark_performance = await self.calculate_benchmark_performance(
            benchmark_symbol, cash_flows, actual_period_for_benchmark, end_date
        )

        # Check for errors in either calculation
        portfolio_errors = portfolio_performance.get("errors", [])
        benchmark_errors = benchmark_performance.get("errors", [])

        if portfolio_errors or benchmark_errors:
            return {
                "portfolio_id": portfolio_id,
                "benchmark_symbol": benchmark_symbol,
                "period": actual_period_for_benchmark,
                "portfolio_performance": portfolio_performance,
                "benchmark_performance": benchmark_performance,
                "errors": portfolio_errors + benchmark_errors,
                "comparison": {
                    "cagr_difference": None,
                    "xirr_difference": None,
                    "outperforming_cagr": None,
                    "outperforming_xirr": None,
                },
                "calculation_date": datetime.now(timezone.utc).isoformat(),
            }

        # Calculate comparison metrics
        portfolio_metrics = portfolio_performance.get("metrics", {})
        benchmark_metrics = benchmark_performance.get("metrics", {})

        comparison = {
            "portfolio_id": portfolio_id,
            "benchmark_symbol": benchmark_symbol,
            "period": actual_period_for_benchmark,
            "portfolio_performance": portfolio_performance,
            "benchmark_performance": benchmark_performance,
            "comparison": {
                "cagr_difference": self._safe_subtract(
                    portfolio_metrics.get("cagr"), benchmark_metrics.get("cagr")
                ),
                "xirr_difference": self._safe_subtract(
                    portfolio_metrics.get("xirr"), benchmark_metrics.get("xirr")
                ),
                "twr_difference": self._safe_subtract(
                    portfolio_metrics.get("twr"), benchmark_metrics.get("twr")
                ),
                "outperforming_cagr": self._is_outperforming(
                    portfolio_metrics.get("cagr"), benchmark_metrics.get("cagr")
                ),
                "outperforming_xirr": self._is_outperforming(
                    portfolio_metrics.get("xirr"), benchmark_metrics.get("xirr")
                ),
                "outperforming_twr": self._is_outperforming(
                    portfolio_metrics.get("twr"), benchmark_metrics.get("twr")
                ),
            },
            "calculation_date": datetime.now(timezone.utc).isoformat(),
        }
        return comparison

    # CAGR Calculation Methods
    async def _calculate_cagr(
            self,
            portfolio_id: int,
            all_transactions: List[Transaction],
            current_value: float,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate (CAGR).

        CAGR Formula: (Ending Value / Beginning Value)^(1/Number of Years) - 1

        For periods <= 1 year, returns simple return.
        For periods > 1 year, returns annualized CAGR.
        """
        try:
            # Get beginning value
            beginning_value = await self._get_portfolio_value_at_date(
                portfolio_id, all_transactions, start_date
            )

            if beginning_value <= 0:
                logger.warning(
                    "Beginning value is zero or negative, cannot calculate CAGR"
                )
                return None

            if current_value < 0:
                return -100.0  # Total loss

            # Calculate time period in years
            if start_date:
                years = (end_date - start_date).days / 365.25
            else:
                # For inception, use first transaction date
                first_transaction_date = min(
                    t.transaction_date for t in all_transactions
                )
                years = (end_date - first_transaction_date).days / 365.25

            if years <= 0:
                return 0.0

            # Calculate total return
            total_return = (current_value / beginning_value) - 1

            # For periods > 1 year, annualize the return
            if years > 1:
                cagr = ((1 + total_return) ** (1 / years)) - 1
            else:
                # For periods <= 1 year, return simple total return
                cagr = total_return

            return float(cagr * 100)  # Return as percentage

        except Exception as e:
            logger.error("Error calculating CAGR: %s", e)
            return None

    async def _calculate_benchmark_cagr(
            self,
            cash_flows: List[CashFlow],
            price_data: pd.DataFrame,
            current_value: float,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[float]:
        """Calculate CAGR for benchmark investment."""
        try:
            # Get beginning value
            if start_date:
                # Calculate value at start date
                beginning_value = self._calculate_benchmark_value(
                    [cf for cf in cash_flows if cf.date < start_date],
                    price_data,
                    start_date,
                )
                years = (end_date - start_date).days / 365.25
            else:
                # For inception, beginning value is 0 (before any investments)
                beginning_value = 0.0
                first_investment_date = min(cf.date for cf in cash_flows)
                years = (end_date - first_investment_date).days / 365.25

            if beginning_value <= 0:
                # If no beginning value, use first investment as beginning
                first_investment = min(cash_flows, key=lambda cf: cf.date)
                beginning_value = abs(first_investment.amount)
                years = (end_date - first_investment.date).days / 365.25

            if beginning_value <= 0 or years <= 0:
                return None

            # Calculate total return
            total_return = (current_value / beginning_value) - 1

            # For periods > 1 year, annualize the return
            if years > 1:
                cagr = ((1 + total_return) ** (1 / years)) - 1
            else:
                cagr = total_return

            return float(cagr * 100)

        except Exception as e:
            logger.error("Error calculating benchmark CAGR: %s", e)
            return None

    # XIRR Calculation Methods
    async def _calculate_xirr(
            self,
            portfolio_id: int,
            all_transactions: List[Transaction],
            current_value: float,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[float]:
        """
        Calculate Extended Internal Rate of Return (XIRR).

        XIRR calculates the internal rate of return for irregular cash flows.
        """
        try:
            dates = []
            amounts = []

            if start_date:
                # For period calculations, add initial portfolio value as outflow
                initial_value = await self._get_portfolio_value_at_date(
                    portfolio_id, all_transactions, start_date
                )
                if initial_value > 0:
                    dates.append(start_date)
                    amounts.append(-initial_value)  # Outflow (investment)

                # Add transactions within the period
                period_transactions = [
                    t for t in all_transactions if t.transaction_date >= start_date
                ]
            else:
                # For inception, use all transactions
                period_transactions = all_transactions

            # Add cash flows from transactions
            for transaction in period_transactions:
                dates.append(transaction.transaction_date)
                if transaction.transaction_type == TransactionType.BUY:
                    amounts.append(-float(transaction.total_amount))  # Outflow
                elif transaction.transaction_type == TransactionType.SELL:
                    amounts.append(float(transaction.total_amount))  # Inflow

            # Add current value as final inflow
            dates.append(end_date)
            amounts.append(current_value)

            # Validate data for XIRR calculation
            if len(dates) < 2:
                logger.warning("Not enough data points for XIRR calculation")
                return None

            # Check for mixed positive and negative flows
            has_positive = any(a > 0 for a in amounts)
            has_negative = any(a < 0 for a in amounts)

            if not (has_positive and has_negative):
                logger.warning("XIRR requires both positive and negative cash flows")
                return None

            # Calculate XIRR using pyxirr
            xirr_result = pyxirr.xirr(dates, amounts)

            if xirr_result is None:
                logger.warning("XIRR calculation failed to converge")
                return None

            return float(xirr_result * 100)  # Return as percentage

        except Exception as e:
            logger.error("Error calculating XIRR: %s", e)
            return None

    def _calculate_benchmark_xirr(
            self,
            cash_flows: List[CashFlow],
            current_value: float,
            start_date: Optional[datetime],  # pylint: disable=unused-argument
            end_date: datetime,
    ) -> Optional[float]:
        """Calculate XIRR for benchmark investment."""
        try:
            dates = []
            amounts = []

            # Add cash flows
            for cf in cash_flows:
                dates.append(cf.date)
                amounts.append(cf.amount)

            # Add current value as final inflow
            dates.append(end_date)
            amounts.append(current_value)

            # Validate data
            if len(dates) < 2:
                return None

            has_positive = any(a > 0 for a in amounts)
            has_negative = any(a < 0 for a in amounts)

            if not (has_positive and has_negative):
                return None

            # Calculate XIRR
            xirr_result = pyxirr.xirr(dates, amounts)

            if xirr_result is None:
                return None

            return float(xirr_result * 100)

        except Exception as e:
            logger.error("Error calculating benchmark XIRR: %s", e)
            return None

    # TWR Calculation Methods
    async def _calculate_twr(
            self,
            portfolio_id: int,
            all_transactions: List[Transaction],
            current_value: float,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[float]:
        """
        Calculate Time-Weighted Rate of Return (TWR).

        TWR measures the compound rate of growth of a portfolio by eliminating
        the distorting effects of cash flows. It's calculated by:
        1. Breaking the measurement period into sub-periods at each cash flow
        2. Calculating the return for each sub-period
        3. Linking the sub-period returns geometrically

        Formula: TWR = [(1 + R1) × (1 + R2) × ... × (1 + Rn)] - 1
        Where Ri is the return for sub-period i
        """
        try:
            # Get all cash flow dates within the period
            cash_flow_dates = self._get_cash_flow_dates(
                all_transactions, start_date, end_date
            )

            if not cash_flow_dates:
                # No cash flows, calculate simple return
                if start_date:
                    initial_value = await self._get_portfolio_value_at_date(
                        portfolio_id, all_transactions, start_date
                    )
                    if initial_value is None or initial_value <= 0:
                        logger.warning("Cannot calculate TWR: invalid initial value")
                        return None

                    simple_return = (current_value / initial_value) - 1
                    return float(simple_return * 100)
                else:
                    # Inception with no intermediate cash flows
                    inception_twr = await self._calculate_inception_twr(
                        all_transactions, current_value
                    )

                    if inception_twr is None:
                        return None

                    return inception_twr

            # Calculate TWR with cash flows
            return await self._calculate_twr_with_cash_flows(
                portfolio_id,
                all_transactions,
                current_value,
                start_date,
                end_date,
                cash_flow_dates,
            )

        except Exception as e:
            logger.error("Error calculating TWR: %s", e)
            return None

    def _get_cash_flow_dates(
            self,
            all_transactions: List[Transaction],
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> List[datetime]:
        """Get sorted list of intermediate cash flow dates within the period."""
        cash_flow_dates = []

        for transaction in all_transactions:
            txn_date = transaction.transaction_date

            # Skip transactions outside the period
            if start_date and txn_date <= start_date:
                continue  # Don't include start date transactions
            if txn_date >= end_date:
                continue  # Don't include end date transactions

            cash_flow_dates.append(txn_date)

        # Remove duplicates and sort
        cash_flow_dates = sorted(list(set(cash_flow_dates)))
        return cash_flow_dates

    async def _calculate_inception_twr(
            self,
            all_transactions: List[Transaction],
            current_value: float,
    ) -> Optional[float]:
        """Calculate TWR from inception when there are no intermediate cash flows."""
        try:
            # Get the first transaction date
            if not all_transactions:
                return None

            first_transaction = min(all_transactions, key=lambda t: t.transaction_date)
            first_date = first_transaction.transaction_date

            # Calculate total initial investment
            initial_investment = sum(
                float(t.total_amount)
                for t in all_transactions
                if t.transaction_type == TransactionType.BUY
            ) - sum(
                float(t.total_amount)
                for t in all_transactions
                if t.transaction_type == TransactionType.SELL
            )

            if initial_investment <= 0:
                logger.warning(
                    "Cannot calculate inception TWR: invalid initial investment"
                )
                return None

            # Calculate total return (not annualized)
            total_return = (current_value / initial_investment) - 1

            # Return the total geometric return for the period
            # Annualization will be handled by the main TWR function if needed
            return float(total_return * 100)

        except Exception as e:
            logger.error("Error calculating inception TWR: %s", e)
            return None

    async def _calculate_twr_with_cash_flows(
            self,
            portfolio_id: int,
            all_transactions: List[Transaction],
            current_value: float,  # pylint: disable=unused-argument
            start_date: Optional[datetime],
            end_date: datetime,
            cash_flow_dates: List[datetime],
    ) -> Optional[float]:
        """Calculate TWR with intermediate cash flows."""
        try:
            # Create sub-periods
            sub_periods = self._create_sub_periods(
                start_date, end_date, cash_flow_dates
            )

            if not sub_periods:
                return None

            # Calculate return for each sub-period
            sub_period_returns = []

            for i, (period_start, period_end) in enumerate(sub_periods):
                sub_return = await self._calculate_sub_period_return(
                    portfolio_id, all_transactions, period_start, period_end
                )

                if sub_return is None:
                    logger.warning("Could not calculate return for sub-period %d", i)
                    continue

                sub_period_returns.append(sub_return)

            if not sub_period_returns:
                logger.warning("No valid sub-period returns calculated")
                return None

            # Link sub-period returns geometrically
            twr = self._link_sub_period_returns(sub_period_returns)

            return float(twr * 100)

        except Exception as e:
            logger.error("Error calculating TWR with cash flows: %s", e)
            return None

    def _create_sub_periods(
            self,
            start_date: Optional[datetime],
            end_date: datetime,
            cash_flow_dates: List[datetime],
    ) -> List[tuple]:
        """Create sub-periods based on cash flow dates."""
        sub_periods = []

        # Determine the actual start date
        actual_start = start_date if start_date else cash_flow_dates[0]

        # Create periods between cash flows
        period_dates = [actual_start] + cash_flow_dates + [end_date]
        period_dates = sorted(list(set(period_dates)))

        for i in range(len(period_dates) - 1):
            period_start = period_dates[i]
            period_end = period_dates[i + 1]

            # Skip zero-length periods
            if period_start != period_end:
                sub_periods.append((period_start, period_end))

        return sub_periods

    async def _calculate_sub_period_return(
            self,
            portfolio_id: int,
            all_transactions: List[Transaction],
            period_start: datetime,
            period_end: datetime,
    ) -> Optional[float]:
        """Calculate return for a single sub-period using the correct TWR formula."""
        try:
            # Market Value at the beginning of the sub-period (before any cash flows)
            start_value_before_cf = await self._get_portfolio_value_at_date(
                portfolio_id, all_transactions, period_start
            )

            # Market Value at the end of the sub-period
            end_value = await self._get_portfolio_value_at_date(
                portfolio_id, all_transactions, period_end
            )

            # Cash flows that happen at the beginning of this period (at period_start)
            cash_flows_at_start = self._get_cash_flows_at_date(
                all_transactions, period_start
            )

            # Calculate the adjusted start value (after cash flows at period start)
            start_value = start_value_before_cf + cash_flows_at_start

            # Handle edge cases
            if start_value is None or start_value <= 0:
                if cash_flows_at_start > 0:
                    return 0.0  # New money invested, no growth yet
                return None

            if end_value is None:
                return None

            # TWR formula: Return = (End Value) / (Start Value + Cash Flows at Start) - 1
            # This properly accounts for cash flows that happen at the period boundary
            sub_return = (end_value / start_value) - 1
            return sub_return

        except Exception as e:
            logger.error("Error calculating sub-period return: %s", e)
            return None

    def _get_cash_flows_at_date(
            self,
            all_transactions: List[Transaction],
            target_date: datetime,
    ) -> float:
        """Get net cash flows that occurred exactly at the target date."""
        net_cash_flow = 0.0

        for transaction in all_transactions:
            if transaction.transaction_date.date() == target_date.date():
                if transaction.transaction_type == TransactionType.BUY:
                    net_cash_flow += float(transaction.total_amount)  # Positive inflow
                elif transaction.transaction_type == TransactionType.SELL:
                    net_cash_flow -= float(transaction.total_amount)  # Negative outflow

        return net_cash_flow

    def _get_period_cash_flows(
            self,
            all_transactions: List[Transaction],
            period_start: datetime,
            period_end: datetime,
    ) -> float:
        """Get the net cash flow that occurred during the sub-period."""
        net_cash_flow = 0.0

        for transaction in all_transactions:
            txn_date = transaction.transaction_date

            # For TWR, we only include cash flows that happen AFTER the period starts
            # This prevents double-counting the initial investment in the first period
            # Cash flows at period boundaries are attributed to the period ending at that date
            if period_start < txn_date <= period_end:
                if transaction.transaction_type == TransactionType.BUY:
                    net_cash_flow += float(transaction.total_amount)  # Positive inflow
                elif transaction.transaction_type == TransactionType.SELL:
                    net_cash_flow -= float(transaction.total_amount)  # Negative outflow

        return net_cash_flow

    def _link_sub_period_returns(self, sub_period_returns: List[float]) -> float:
        """Link sub-period returns geometrically."""
        try:
            # TWR = [(1 + R1) × (1 + R2) × ... × (1 + Rn)] - 1
            linked_return = 1.0

            for sub_return in sub_period_returns:
                linked_return *= 1 + sub_return

            return linked_return - 1

        except Exception as e:
            logger.error("Error linking sub-period returns: %s", e)
            return 0.0

    async def _calculate_benchmark_twr(
            self,
            cash_flows: List[CashFlow],
            price_data: pd.DataFrame,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[float]:
        """Calculate proper TWR for benchmark using sub-period analysis."""
        try:
            if price_data.empty:
                return None

            # Get cash flow dates (only investments/divestments)
            cash_flow_dates = [cf.date for cf in cash_flows if cf.amount != 0]
            cash_flow_dates = sorted(list(set(cash_flow_dates)))

            if not cash_flow_dates:
                return None

            # Create sub-periods for benchmark TWR calculation
            actual_start = start_date if start_date else cash_flow_dates[0]
            sub_periods = self._create_benchmark_sub_periods(
                actual_start, end_date, cash_flow_dates
            )

            if not sub_periods:
                return None

            # Calculate return for each sub-period
            sub_period_returns = []
            cumulative_shares = 0.0

            for i, (period_start, period_end) in enumerate(sub_periods):
                sub_return = await self._calculate_benchmark_sub_period_return(
                    cash_flows, price_data, period_start, period_end, cumulative_shares
                )

                if sub_return is not None:
                    sub_period_returns.append(sub_return)

                # Update cumulative shares for next period
                for cf in cash_flows:
                    if period_start < cf.date <= period_end and cf.amount < 0:
                        price_at_date = self._get_price_from_data(price_data, cf.date)
                        if price_at_date:
                            shares_bought = abs(cf.amount) / price_at_date
                            cumulative_shares += shares_bought

            if not sub_period_returns:
                logger.warning("No valid benchmark sub-period returns calculated")
                return None

            # Link sub-period returns geometrically
            twr = self._link_sub_period_returns(sub_period_returns)

            return float(twr * 100)

        except Exception as e:
            logger.error("Error calculating benchmark TWR: %s", e)
            return None

    def _create_benchmark_sub_periods(
            self,
            start_date: datetime,
            end_date: datetime,
            cash_flow_dates: List[datetime],
    ) -> List[tuple]:
        """Create sub-periods for benchmark TWR calculation."""
        period_dates = [start_date] + cash_flow_dates + [end_date]
        period_dates = sorted(list(set(period_dates)))

        sub_periods = []
        for i in range(len(period_dates) - 1):
            period_start = period_dates[i]
            period_end = period_dates[i + 1]

            if period_start != period_end:
                sub_periods.append((period_start, period_end))

        return sub_periods

    async def _calculate_benchmark_sub_period_return(
            self,
            cash_flows: List[CashFlow],
            price_data: pd.DataFrame,
            period_start: datetime,
            period_end: datetime,
            cumulative_shares_at_start: float,
    ) -> Optional[float]:
        """Calculate return for a single benchmark sub-period."""
        try:
            # Get prices at start and end of period
            start_price = self._get_price_from_data(price_data, period_start)
            end_price = self._get_price_from_data(price_data, period_end)

            if not start_price or not end_price:
                return None

            # Calculate benchmark portfolio value at start
            start_value = cumulative_shares_at_start * start_price

            # Calculate net cash flow during the period
            net_cash_flow = 0.0
            for cf in cash_flows:
                if period_start < cf.date <= period_end:
                    net_cash_flow += (
                        abs(cf.amount) if cf.amount < 0 else -abs(cf.amount)
                    )

            # Calculate benchmark portfolio value at end (before considering cash flows)
            end_value = cumulative_shares_at_start * end_price

            # Handle edge cases
            if start_value <= 0:
                if net_cash_flow > 0:
                    return 0.0  # New money invested, no growth yet
                return None

            # Correct TWR formula for benchmark
            sub_return = (end_value - net_cash_flow) / start_value - 1
            return sub_return

        except Exception as e:
            logger.error("Error calculating benchmark sub-period return: %s", e)
            return None

    # Helper Methods
    async def _get_portfolio_value_at_date(
            self,
            portfolio_id: int,  # pylint: disable=unused-argument
            all_transactions: List[Transaction],
            target_date: Optional[datetime],
    ) -> float:
        """Get portfolio market value at a specific date."""
        try:
            if target_date is None:
                # For inception, portfolio value was 0 before any investments
                return 0.0

            # Get transactions up to target date
            transactions_up_to_date = [
                t for t in all_transactions if t.transaction_date <= target_date
            ]

            if not transactions_up_to_date:
                return 0.0

            # Calculate holdings at target date
            holdings = {}
            for transaction in transactions_up_to_date:
                asset_id = transaction.asset_id
                quantity = float(transaction.quantity)

                if asset_id not in holdings:
                    holdings[asset_id] = 0.0

                if transaction.transaction_type == TransactionType.BUY:
                    holdings[asset_id] += quantity
                elif transaction.transaction_type == TransactionType.SELL:
                    holdings[asset_id] -= quantity

            # Remove zero holdings
            holdings = {k: v for k, v in holdings.items() if v > 1e-9}

            if not holdings:
                return 0.0

            # Calculate market value using prices at target date
            total_value = 0.0
            missing_price_errors = []

            for asset_id, quantity in holdings.items():
                asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
                if not asset:
                    error_msg = f"Asset with ID {asset_id} not found in database"
                    logger.error(error_msg)
                    missing_price_errors.append(error_msg)
                    continue

                price_data = await self._get_price_data(asset.symbol)
                if price_data is None or price_data.empty:
                    error_msg = f"No price data available for {asset.symbol}"
                    logger.error(error_msg)
                    missing_price_errors.append(error_msg)
                    continue

                price = self._get_price_for_date(price_data, target_date.date())
                if price is not None:
                    total_value += quantity * price
                else:
                    error_msg = (
                        f"No price available for {asset.symbol} on {target_date.date()}"
                    )
                    logger.error(error_msg)
                    missing_price_errors.append(error_msg)

            if missing_price_errors:
                logger.warning(
                    "Portfolio value calculation incomplete due to missing price data: %s",
                    missing_price_errors,
                )

            return total_value

        except Exception as e:
            logger.error("Error getting portfolio value at date: %s", e)
            return 0.0

    def _calculate_benchmark_value(
            self,
            cash_flows: List[CashFlow],
            price_data: pd.DataFrame,
            as_of_date: datetime,
    ) -> float:
        """Calculate value of benchmark investment at a specific date."""
        try:
            total_shares = 0.0

            # Process each cash flow
            for cf in cash_flows:
                if cf.date > as_of_date:
                    continue

                price = self._get_price_for_date(price_data, cf.date.date())
                if price is None or price <= 0:
                    continue

                if cf.amount < 0:  # Outflow (buying)
                    shares = abs(cf.amount) / price
                    total_shares += shares
                else:  # Inflow (selling)
                    shares = cf.amount / price
                    total_shares = max(0, total_shares - shares)

            # Get current price
            current_price = self._get_price_for_date(price_data, as_of_date.date())
            if current_price is None:
                return 0.0

            return total_shares * current_price

        except Exception as e:
            logger.error("Error calculating benchmark value: %s", e)
            return 0.0

    async def _get_price_data(self, symbol: str) -> pd.DataFrame:
        """Get price data for a symbol with caching."""
        try:
            # Check cache
            current_time = datetime.now(timezone.utc)
            if (
                    symbol in self._price_cache
                    and symbol in self._price_cache_time
                    and (current_time - self._price_cache_time[symbol]).seconds < 3600
            ):
                return self._price_cache[symbol]

            # Fetch new data
            price_data = await self.market_data_service.fetch_ticker_data(
                symbol=symbol, period="max", interval="1d"
            )

            if price_data is not None and not price_data.empty:
                # Standardize index to dates
                if "Date" in price_data.columns:
                    price_data["Date"] = pd.to_datetime(price_data["Date"]).dt.date
                    price_data = price_data.set_index("Date")
                elif isinstance(price_data.index, pd.DatetimeIndex):
                    price_data.index = price_data.index.date

                price_data = price_data.sort_index()

                # Cache the data
                self._price_cache[symbol] = price_data
                self._price_cache_time[symbol] = current_time

            return price_data

        except Exception as e:
            logger.error("Error getting price data for %s: %s", symbol, e)
            return pd.DataFrame()

    def _get_price_for_date(
            self, price_data: pd.DataFrame, target_date: datetime.date
    ) -> Optional[float]:
        """Get closing price for a specific date."""
        try:
            if price_data.empty:
                return None

            # Use asof to find the last available price on or before target date
            price_row = price_data.asof(target_date)

            if pd.notna(price_row["Close"]):
                return float(price_row["Close"])

            return None

        except Exception as e:
            logger.warning("Could not get price for date %s: %s", target_date, e)
            return None

    def _create_cash_flows_from_transactions(
            self, transactions: List[Transaction]
    ) -> List[CashFlow]:
        """Create cash flows from portfolio transactions."""
        cash_flows = []

        for transaction in transactions:
            if transaction.transaction_type == TransactionType.BUY:
                # Buy is an outflow (negative)
                cash_flows.append(
                    CashFlow(
                        transaction.transaction_date, -float(transaction.total_amount)
                    )
                )
            elif transaction.transaction_type == TransactionType.SELL:
                # Sell is an inflow (positive)
                cash_flows.append(
                    CashFlow(
                        transaction.transaction_date, float(transaction.total_amount)
                    )
                )

        return cash_flows

    # Database Helper Methods
    def get_portfolio(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        """Get portfolio and verify ownership."""
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .first()
        )

    def _get_transactions(
            self,
            portfolio_id: int,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> List[Transaction]:
        """Get transactions for a portfolio within date range."""
        query = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_date <= end_date,
        )

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)

        return query.order_by(Transaction.transaction_date).all()

    def get_current_portfolio_value(
            self, portfolio_id: int
    ) -> tuple[float, list[str]]:
        """
        Get current total value of portfolio.

        Returns:
            Tuple of (total_value, error_messages)
        """
        try:
            assets = (
                self.db.query(PortfolioAsset)
                .filter(PortfolioAsset.portfolio_id == portfolio_id)
                .all()
            )

            total_value = 0.0
            errors = []

            for asset in assets:
                if asset.current_value is not None:
                    total_value += float(asset.current_value)
                elif asset.quantity and asset.quantity > 0:
                    # Never use cost basis as fallback - log error instead
                    asset_obj = (
                        self.db.query(Asset).filter(Asset.id == asset.asset_id).first()
                    )
                    symbol = (
                        asset_obj.symbol if asset_obj else f"Asset ID {asset.asset_id}"
                    )
                    error_msg = (
                        f"No current market value available for {symbol} "
                        f"(quantity: {asset.quantity})"
                    )
                    logger.error(error_msg)
                    errors.append(error_msg)

            return total_value, errors

        except Exception as e:
            error_msg = f"Error getting current portfolio value: {e}"
            logger.error(error_msg)
            return 0.0, [error_msg]

    # Utility Methods
    def _get_price_from_data(
            self, price_data: pd.DataFrame, target_date: datetime
    ) -> Optional[float]:
        """Get price from price data DataFrame at a specific date."""
        try:
            if price_data.empty:
                return None

            # Convert target_date to pandas timestamp if needed
            if not isinstance(target_date, pd.Timestamp):
                target_date = pd.Timestamp(target_date)

            # Use asof to find the last available price on or before target date
            price_row = price_data.asof(target_date.date())

            if pd.notna(price_row["Close"]):
                return float(price_row["Close"])

            return None
        except Exception as e:
            logger.warning("Could not get price for date %s: %s", target_date, e)
            return None

    def _safe_subtract(self, a: Optional[float], b: Optional[float]) -> Optional[float]:
        """Safely subtract two optional float values."""
        if a is not None and b is not None:
            return a - b
        return None

    def _is_outperforming(
            self, portfolio_return: Optional[float], benchmark_return: Optional[float]
    ) -> Optional[bool]:
        """Check if portfolio is outperforming benchmark."""
        if portfolio_return is not None and benchmark_return is not None:
            return portfolio_return > benchmark_return
        return None

    def _empty_performance_result(
            self, portfolio_id: int, period: str
    ) -> Dict[str, Any]:
        """Return empty performance result."""
        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "start_date": None,
            "end_date": datetime.now(timezone.utc),
            "current_value": 0.0,
            "errors": ["No transactions found for the specified period or portfolio"],
            "metrics": {
                "cagr": None,
                "xirr": None,
                "twr": None,
                "mwr": None,
                "volatility": None,
                "max_drawdown": None,
            },
            "calculation_date": datetime.now(timezone.utc).isoformat(),
        }

    def _empty_benchmark_performance_result(
            self, benchmark_symbol: str, period: str
    ) -> Dict[str, Any]:
        """Return empty benchmark performance result."""
        return {
            "benchmark_symbol": benchmark_symbol,
            "period": period,
            "error": "No investment data or price data available",
            "metrics": {
                "cagr": None,
                "xirr": None,
                "twr": None,
                "mwr": None,
            },
        }

    def _calculate_volatility(
            self, portfolio_history: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate annualized volatility from a series of portfolio values.
        Volatility is the standard deviation of daily returns.
        """
        if portfolio_history is None or portfolio_history.empty or len(portfolio_history) < 2:
            return None

        try:
            # Calculate daily returns
            daily_returns = portfolio_history["value"].pct_change().dropna()

            if daily_returns.empty:
                return 0.0

            # Calculate annualized volatility (252 trading days in a year)
            volatility = daily_returns.std() * np.sqrt(252)
            return float(volatility * 100)  # Return as percentage
        except Exception as e:
            logger.error("Error calculating volatility: %s", e)
            return None

    def _calculate_max_drawdown(
            self, portfolio_history: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate the Max Drawdown from a series of portfolio values.
        Max Drawdown is the largest percentage drop from a peak to a trough.
        """
        if portfolio_history is None or portfolio_history.empty:
            return None

        try:
            # Calculate the running maximum (cumulative high)
            running_max = portfolio_history["value"].cummax()
            # Calculate the drawdown (percentage drop from the running max)
            drawdown = (portfolio_history["value"] - running_max) / running_max
            # The max drawdown is the minimum value of the drawdown series
            max_drawdown = drawdown.min()
            return float(max_drawdown * 100)  # Return as percentage
        except Exception as e:
            logger.error("Error calculating max drawdown: %s", e)
            return None

    async def _get_portfolio_history(
            self,
            portfolio_id: int,
            all_transactions: List[Transaction],
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[pd.DataFrame]:
        """
        Generates a daily time series of the portfolio's total market value.
        This is a computationally intensive operation.
        """
        try:
            if not all_transactions:
                return None

            first_date = min(t.transaction_date for t in all_transactions)
            period_start = start_date or first_date

            if period_start > end_date:
                return None

            # Create a date range for the history
            date_range = pd.date_range(start=period_start, end=end_date, freq="D")
            history = []

            # Group transactions by date for efficiency
            transactions_by_date = {}
            for t in all_transactions:
                date_key = t.transaction_date.date()
                if date_key not in transactions_by_date:
                    transactions_by_date[date_key] = []
                transactions_by_date[date_key].append(t)

            # Get initial holdings before the start date
            holdings = await self._get_holdings_at_date(
                all_transactions, period_start - timedelta(days=1)
            )
            asset_map = {}  # Cache asset objects

            for date in date_range:
                # Update holdings with transactions for the current day
                date_key = date.date()
                if date_key in transactions_by_date:
                    for transaction in transactions_by_date[date_key]:
                        asset_id = transaction.asset_id
                        quantity = float(transaction.quantity)
                        if asset_id not in holdings:
                            holdings[asset_id] = 0.0

                        if transaction.transaction_type == TransactionType.BUY:
                            holdings[asset_id] += quantity
                        elif transaction.transaction_type == TransactionType.SELL:
                            holdings[asset_id] -= quantity

                # Calculate portfolio value for the current day
                total_value = 0.0
                for asset_id, quantity in holdings.items():
                    if quantity > 1e-9:
                        # Fetch asset from cache or DB
                        if asset_id not in asset_map:
                            asset_map[asset_id] = (
                                self.db.query(Asset)
                                .filter(Asset.id == asset_id)
                                .first()
                            )
                        asset = asset_map[asset_id]
                        if not asset:
                            continue

                        price_data = await self._get_price_data(asset.symbol)
                        price = self._get_price_for_date(price_data, date.date())
                        if price:
                            total_value += quantity * price

                history.append({"date": date, "value": total_value})

            if not history:
                return None

            df = pd.DataFrame(history).set_index("date")
            return df

        except Exception as e:
            logger.error("Error generating portfolio history: %s", e)
            return None

    async def _get_holdings_at_date(
            self, transactions: List[Transaction], target_date: datetime
    ) -> Dict[int, float]:
        """Calculates asset holdings on a specific date."""
        holdings = {}
        for t in transactions:
            if t.transaction_date <= target_date:
                asset_id = t.asset_id
                quantity = float(t.quantity)
                if asset_id not in holdings:
                    holdings[asset_id] = 0.0

                if t.transaction_type == TransactionType.BUY:
                    holdings[asset_id] += quantity
                elif t.transaction_type == TransactionType.SELL:
                    holdings[asset_id] -= quantity
        return {k: v for k, v in holdings.items() if v > 1e-9}

    def _get_current_portfolio_value_from_db(
            self, portfolio_id: int
    ) -> tuple[float, list[str]]:
        """
        Get current total value of portfolio from PortfolioAsset table.
        This is faster than calculating from scratch but relies on updated data.
        """
        # This is the existing method, renamed for clarity
        # ... (implementation from previous version) ...
        try:
            assets = (
                self.db.query(PortfolioAsset)
                .filter(PortfolioAsset.portfolio_id == portfolio_id)
                .all()
            )

            total_value = 0.0
            errors = []

            for asset in assets:
                if asset.current_value is not None:
                    total_value += float(asset.current_value)
                elif asset.quantity and asset.quantity > 0:
                    asset_obj = (
                        self.db.query(Asset).filter(Asset.id == asset.asset_id).first()
                    )
                    symbol = (
                        asset_obj.symbol if asset_obj else f"Asset ID {asset.asset_id}"
                    )
                    error_msg = (
                        f"No current market value available for {symbol}"
                    )
                    logger.error(error_msg)
                    errors.append(error_msg)

            return total_value, errors

        except Exception as e:
            error_msg = f"Error getting current portfolio value: {e}"
            logger.error(error_msg)
            return 0.0, [error_msg]
