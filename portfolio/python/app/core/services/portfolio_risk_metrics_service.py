import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd  # type: ignore
from sqlalchemy.orm import Session

from core.services.portfolio_calculation_service import (
    PortfolioCalculationService,
)
from core.services.utils import PeriodType

logger = logging.getLogger(__name__)


class PortfolioRiskMetricsService:
    """
    Service for calculating key portfolio risk metrics based on historical daily values.
    """

    def __init__(self, db: Session, calculation_service: PortfolioCalculationService):
        """
        Initializes the risk metrics service.

        Args:
            db: The SQLAlchemy database session.
            calculation_service: An instance of PortfolioCalculationService to reuse
                                 its data-fetching and history generation capabilities.
        """
        self.db = db
        self.calculation_service = calculation_service
        # Define constants used in calculations
        self.TRADING_DAYS_PER_YEAR = 252
        # ASSUMPTION: A constant annualized risk-free rate of 3.0%.
        # For a production system, this should be fetched dynamically from a reliable source
        # (e.g., FRED for US Treasury Bill rates).
        self.ANNUALIZED_RISK_FREE_RATE = 0.03

    async def calculate_portfolio_risk_metrics(
            self,
            portfolio_id: int,
            period: str = PeriodType.INCEPTION,
            benchmark_symbol: str = "^GSPC",  # S&P 500 as default benchmark
            end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates a comprehensive set of risk metrics for a given portfolio and period.

        Args:
            portfolio_id: The ID of the portfolio.
            period: The calculation period (e.g., '1y', '3y', 'inception').
            benchmark_symbol: The market benchmark ticker for Beta calculation.
            end_date: The end date for the calculation (defaults to now).

        Returns:
            A dictionary containing the calculated risk metrics.
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        start_date = PeriodType.get_start_date(period, end_date)

        # Step 1: Reuse the existing service to get the portfolio's daily value history.
        # This is the foundational data for all subsequent risk calculations.
        try:
            # First, fetch all transactions to pass to the history generator
            all_transactions = self.calculation_service.get_transactions(
                portfolio_id, None, end_date
            )
            if not all_transactions:
                return self._empty_risk_result(
                    portfolio_id, period, "No transactions found for this portfolio."
                )

            portfolio_history_df = await self.calculation_service.get_portfolio_history(
                all_transactions, start_date, end_date
            )

            if portfolio_history_df is None or portfolio_history_df.empty:
                return self._empty_risk_result(
                    portfolio_id,
                    period,
                    "Could not generate portfolio value history. Not enough data.",
                )

            # Calculate daily returns ADJUSTED for cash flows
            # Get the previous day's market value
            prev_day_value = portfolio_history_df["value"].shift(1)

            # Calculate the adjusted denominator: Start Value + Net Cash Flow
            # A BUY (positive cash flow) increases the base
            # A SELL (negative cash flow) decreases the base
            denominator = prev_day_value + portfolio_history_df["net_cash_flow"]

            # Calculate the true daily return
            daily_returns = (portfolio_history_df["value"] / denominator - 1).dropna()

            # Replace NaN/inf values that can occur on days with full withdrawal
            daily_returns.replace([np.inf, -np.inf], np.nan, inplace=True)
            daily_returns.dropna(inplace=True)

            if len(daily_returns) < 2:
                return self._empty_risk_result(
                    portfolio_id,
                    period,
                    "Insufficient daily return data to calculate risk metrics.",
                )

        except Exception as e:
            logger.error(
                f"Failed to generate portfolio history for risk calculation: {e}"
            )
            return self._empty_risk_result(
                portfolio_id, period, f"An error occurred: {e}"
            )

        # Step 2: Calculate each risk metric using the daily returns data.
        volatility = self._calculate_volatility(daily_returns)
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        beta = await self._calculate_beta(daily_returns, benchmark_symbol, start_date, end_date)
        value_at_risk_95 = self._calculate_var(daily_returns)

        # Step 3: Assemble the final result dictionary.
        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "benchmark_symbol_for_beta": benchmark_symbol,
            "start_date": start_date,
            "end_date": end_date,
            "calculation_date": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "annualized_volatility_pct": volatility,
                "sharpe_ratio": sharpe_ratio,
                "beta": beta,
                "value_at_risk_95_pct": value_at_risk_95,
            },
        }

    def _calculate_volatility(self, daily_returns: pd.Series) -> Optional[float]:
        """
        Calculates the annualized volatility (standard deviation of returns).

        Volatility measures the degree of variation of a trading price series over time.
        It is annualized by multiplying the daily standard deviation by the square
        root of the number of trading days in a year (252).
        """
        try:
            # Calculate the standard deviation of daily returns
            daily_std_dev = daily_returns.std()
            # Annualize the volatility
            annualized_volatility = daily_std_dev * np.sqrt(self.TRADING_DAYS_PER_YEAR)
            return float(annualized_volatility * 100)  # Return as a percentage
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None

    def _calculate_sharpe_ratio(self, daily_returns: pd.Series) -> Optional[float]:
        """
        Calculates the annualized Sharpe Ratio.

        The Sharpe Ratio measures risk-adjusted return. It is the average return earned
        in excess of the risk-free rate per unit of volatility. A higher Sharpe Ratio
        indicates better performance for the amount of risk taken.
        """
        try:
            # Calculate excess returns over the daily risk-free rate
            daily_risk_free_rate = (1 + self.ANNUALIZED_RISK_FREE_RATE) ** (
                    1 / self.TRADING_DAYS_PER_YEAR
            ) - 1
            excess_daily_returns = daily_returns - daily_risk_free_rate

            # Calculate the mean and standard deviation of excess returns
            avg_excess_return = excess_daily_returns.mean()
            std_dev_excess_return = excess_daily_returns.std()

            if std_dev_excess_return == 0:
                return 0.0

            # Calculate and annualize the Sharpe Ratio
            daily_sharpe_ratio = avg_excess_return / std_dev_excess_return
            annualized_sharpe_ratio = daily_sharpe_ratio * np.sqrt(
                self.TRADING_DAYS_PER_YEAR
            )

            return float(annualized_sharpe_ratio)
        except Exception as e:
            logger.error(f"Error calculating Sharpe Ratio: {e}")
            return None

    async def _calculate_beta(
            self,
            portfolio_daily_returns: pd.Series,
            benchmark_symbol: str,
            start_date: Optional[datetime],
            end_date: datetime,
    ) -> Optional[float]:
        """
        Calculates Beta, a measure of a portfolio's volatility relative to the market.

        Beta = Covariance(Portfolio Returns, Benchmark Returns) / Variance(Benchmark Returns)
        - Beta > 1: More volatile than the market.
        - Beta < 1: Less volatile than the market.
        - Beta = 1: Moves in line with the market.
        """
        try:
            # Fetch benchmark price data
            benchmark_data = await self.calculation_service.get_price_data(benchmark_symbol)
            if benchmark_data is None or benchmark_data.empty:
                logger.warning(f"Could not fetch benchmark data for {benchmark_symbol}")
                return None

            # Filter benchmark data for the relevant period
            if start_date:
                benchmark_data = benchmark_data[benchmark_data.index >= start_date.date()]
            benchmark_data = benchmark_data[benchmark_data.index <= end_date.date()]

            # Calculate benchmark daily returns
            benchmark_daily_returns = benchmark_data["Close"].pct_change().dropna()

            # Align portfolio and benchmark returns data
            combined_df = pd.DataFrame(
                {
                    "portfolio": portfolio_daily_returns,
                    "benchmark": benchmark_daily_returns,
                }
            ).dropna()

            if len(combined_df) < 2:
                logger.warning("Not enough overlapping data points to calculate Beta.")
                return None

            # Calculate covariance and variance
            covariance = combined_df["portfolio"].cov(combined_df["benchmark"])
            variance = combined_df["benchmark"].var()

            if variance == 0:
                return 0.0

            beta = covariance / variance
            return float(beta)
        except Exception as e:
            logger.error(f"Error calculating Beta: {e}")
            return None

    def _calculate_var(
            self, daily_returns: pd.Series, confidence_level: float = 0.95
    ) -> Optional[float]:
        """
        Calculates the Value at Risk (VaR) using the historical simulation method.

        VaR estimates the potential loss in value of a portfolio over a defined
        period for a given confidence interval. A 95% VaR indicates the threshold
        that losses are not expected to exceed on 95% of trading days.
        """
        try:
            # The VaR is the quantile of the historical returns distribution.
            # For a 95% confidence level, we look at the 5th percentile.
            var = daily_returns.quantile(1 - confidence_level)
            return float(var * 100)  # Return as a percentage loss
        except Exception as e:
            logger.error(f"Error calculating Value at Risk (VaR): {e}")
            return None

    def _empty_risk_result(
            self, portfolio_id: int, period: str, error_message: str
    ) -> Dict[str, Any]:
        """Returns a standardized empty/error result dictionary."""
        logger.warning(f"Portfolio {portfolio_id} ({period}): {error_message}")
        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "error": error_message,
            "metrics": {
                "annualized_volatility_pct": None,
                "sharpe_ratio": None,
                "beta": None,
                "value_at_risk_95_pct": None,
            },
        }