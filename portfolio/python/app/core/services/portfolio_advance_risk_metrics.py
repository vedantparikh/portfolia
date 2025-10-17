import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd  # type: ignore
from sqlalchemy.orm import Session

# Import the services it will depend on
from core.services.portfolio_calculation_service import PortfolioCalculationService
from core.services.portfolio_service import PortfolioService
from core.services.utils import PeriodType

logger = logging.getLogger(__name__)


class PortfolioAdvanceRiskMetricsService:
    """
    Service for calculating advanced portfolio risk and diversification metrics.
    These metrics focus on risk-adjusted returns, concentration, and the
    effectiveness of diversification within the portfolio.
    """

    def __init__(self, db: Session):
        """
        Initializes the advanced risk metrics service.

        Args:
            db: The SQLAlchemy database session.
        """
        self.db = db
        # Instantiate the services this service depends on
        self.calculation_service = PortfolioCalculationService(db)
        self.portfolio_service = PortfolioService(db)
        # Define constants used in calculations
        self.TRADING_DAYS_PER_YEAR = 252
        self.ANNUALIZED_RISK_FREE_RATE = 0.03  # ASSUMPTION: Constant risk-free rate

    async def calculate_advanced_metrics(
            self,
            portfolio_id: int,
            period: str = PeriodType.YTD,
            benchmark_symbol: str = "^GSPC",  # S&P 500 as default
    ) -> Dict[str, Any]:
        """
        Calculates a suite of advanced risk metrics for a portfolio.

        Args:
            portfolio_id: The ID of the portfolio.
            user_id: The ID of the user to verify ownership.
            period: The calculation period (e.g., 'ytd', '1y').
            benchmark_symbol: The market benchmark ticker.

        Returns:
            A dictionary containing the calculated advanced metrics.
        """
        end_date = datetime.now(timezone.utc)
        start_date = PeriodType.get_start_date(period, end_date)

        # --- Step 1: Fetch Foundational Data using other Services ---
        try:
            # 1a. Get Portfolio's True Daily Returns using PortfolioCalculationService
            # This correctly accounts for cash flows and is the basis for Beta/Alpha
            all_transactions = self.calculation_service.get_transactions(portfolio_id, None, end_date)
            if not all_transactions:
                return self._empty_result(portfolio_id, "Portfolio has no transactions.", period)

            portfolio_history_df = await self.calculation_service.get_portfolio_history(
                all_transactions, start_date, end_date
            )
            if portfolio_history_df is None or portfolio_history_df.empty:
                return self._empty_result(portfolio_id, "Could not generate portfolio history.", period)

            # Calculate true daily returns, adjusted for cash flows
            prev_day_value = portfolio_history_df["value"].shift(1)
            denominator = prev_day_value + portfolio_history_df["net_cash_flow"]
            portfolio_daily_returns = (portfolio_history_df["value"] / denominator - 1).replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            # 1b. Get Current Holdings and Weights using PortfolioService
            # This is the basis for concentration and diversification metrics
            holdings = await self.portfolio_service.get_portfolio_holdings(portfolio_id)
            if not holdings:
                return self._empty_result(portfolio_id, "Portfolio has no current holdings.", period)

            total_portfolio_value = sum(h.current_value for h in holdings if h.current_value is not None)
            if total_portfolio_value == 0:
                return self._empty_result(portfolio_id, "Portfolio value is zero.", period)

            asset_symbols = [h.symbol for h in holdings]
            asset_weights = pd.Series(
                {h.symbol: h.current_value / total_portfolio_value for h in holdings if h.current_value is not None}
            )

            # 1c. Get Historical Price Data for all assets and the benchmark
            all_symbols = list(set(asset_symbols + [benchmark_symbol]))
            price_data_dict = {}
            for symbol in all_symbols:
                # Reuse the calculation service's cached price fetcher
                price_data_dict[symbol] = await self.calculation_service.get_price_data(symbol)

            # Combine individual asset prices into a single DataFrame
            asset_prices = pd.concat(
                {s: df['Close'] for s, df in price_data_dict.items() if s in asset_symbols and df is not None}, axis=1
            )
            asset_prices.sort_index(inplace=True)
            asset_prices = asset_prices.truncate(before=start_date.date(), after=end_date.date())
            asset_returns = asset_prices.pct_change().dropna()

            benchmark_prices = price_data_dict.get(benchmark_symbol)
            if benchmark_prices is None:
                logger.warning(f"Could not fetch benchmark data for {benchmark_symbol}")
                benchmark_prices = pd.DataFrame()  # Empty frame to avoid errors
            else:
                benchmark_prices.sort_index(inplace=True)
                benchmark_prices = benchmark_prices.truncate(before=start_date.date(), after=end_date.date())

            if len(asset_returns) < 2 or len(portfolio_daily_returns) < 2:
                return self._empty_result(portfolio_id, "Insufficient historical data for calculations.", period)

        except Exception as e:
            logger.error(f"Failed during data fetching for advanced metrics: {e}", exc_info=True)
            return self._empty_result(portfolio_id, f"An error occurred during data fetching: {e}", period)

        # --- Step 2: Calculate Metrics ---
        beta, alpha = self._calculate_beta_and_alpha(
            portfolio_daily_returns, benchmark_prices
        )

        concentration_risk = self._calculate_concentration_risk(asset_weights)

        diversification_ratio = self._calculate_diversification_ratio(asset_weights, asset_returns)

        effective_assets = 1 / concentration_risk if concentration_risk and concentration_risk > 0 else None

        # --- Step 3: Assemble Result ---
        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "benchmark_symbol": benchmark_symbol,
            "calculation_date": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "beta": beta,
                "jensens_alpha_pct": alpha,
                "concentration_risk_hhi": concentration_risk,
                "diversification_ratio": diversification_ratio,
                "effective_number_of_assets": effective_assets,
            },
        }

    def _calculate_beta_and_alpha(
            self, portfolio_returns: pd.Series, benchmark_prices: pd.DataFrame
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculates Beta and Jensen's Alpha."""
        if benchmark_prices.empty:
            return None, None
        try:
            benchmark_returns = benchmark_prices['Close'].pct_change().dropna()

            port_returns = portfolio_returns.copy()
            bench_returns = benchmark_returns.copy()
            port_returns.index = pd.to_datetime(port_returns.index, errors='coerce')
            bench_returns.index = pd.to_datetime(bench_returns.index, errors='coerce')

            if hasattr(port_returns.index, 'tz') and port_returns.index.tz is not None:
                port_returns.index = port_returns.index.tz_localize(None)

            if hasattr(bench_returns.index, 'tz') and bench_returns.index.tz is not None:
                bench_returns.index = bench_returns.index.tz_localize(None)

            port_returns = port_returns.dropna()
            bench_returns = bench_returns.dropna()

            # At this point, both indices *must* be tz-naive DatetimeIndex
            # The line below is where your error was (approx. line 187)
            combined = pd.DataFrame(
                {
                    "portfolio": port_returns,
                    "benchmark": bench_returns
                }
            ).dropna()

            if len(combined) < 2:
                return None, None

            covariance = combined["portfolio"].cov(combined["benchmark"])
            variance = combined["benchmark"].var()
            beta = covariance / variance if variance != 0 else 0.0

            daily_rf = (1 + self.ANNUALIZED_RISK_FREE_RATE) ** (1 / self.TRADING_DAYS_PER_YEAR) - 1
            avg_portfolio_return = combined["portfolio"].mean()
            avg_benchmark_return = combined["benchmark"].mean()

            expected_return = daily_rf + beta * (avg_benchmark_return - daily_rf)
            alpha_daily = avg_portfolio_return - expected_return

            annualized_alpha = alpha_daily * self.TRADING_DAYS_PER_YEAR

            return float(beta), float(annualized_alpha * 100)
        except Exception as e:
            # This is where the error is being logged
            logger.error(f"Error calculating Beta and Alpha: {e}", exc_info=True)
            return None, None

    def _calculate_concentration_risk(self, weights: pd.Series) -> Optional[float]:
        """Calculates concentration risk using the Herfindahl-Hirschman Index (HHI)."""
        if weights.empty:
            return None
        try:
            # HHI is the sum of the squares of the weights.
            return float((weights ** 2).sum())
        except Exception as e:
            logger.error(f"Error calculating HHI concentration: {e}")
            return None

    def _calculate_diversification_ratio(
            self, weights: pd.Series, asset_returns: pd.DataFrame
    ) -> Optional[float]:
        """Calculates the diversification ratio of the portfolio."""
        if weights.empty or asset_returns.empty:
            return None
        try:
            # Align weights and returns columns
            aligned_weights = weights.reindex(asset_returns.columns).fillna(0)

            # 1. Numerator: Weighted sum of individual asset volatilities
            individual_volatilities = asset_returns.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)
            weighted_avg_volatility = (aligned_weights * individual_volatilities).sum()

            # 2. Denominator: Overall portfolio volatility
            cov_matrix = asset_returns.cov() * self.TRADING_DAYS_PER_YEAR
            portfolio_variance = np.dot(aligned_weights.T, np.dot(cov_matrix, aligned_weights))
            portfolio_volatility = np.sqrt(portfolio_variance)

            if portfolio_volatility == 0:
                return 1.0  # No risk, so no diversification benefit to measure

            return float(weighted_avg_volatility / portfolio_volatility)
        except Exception as e:
            logger.error(f"Error calculating diversification ratio: {e}")
            return None

    def _empty_result(self, portfolio_id: int, error_message: str, period: str) -> Dict[str, Any]:
        """Returns a standardized empty/error result dictionary."""
        logger.warning(f"Portfolio {portfolio_id}: {error_message}")
        return {
            "portfolio_id": portfolio_id,
            "error": error_message,
            "period": period,
            "metrics": {
                "beta": None,
                "jensens_alpha_pct": None,
                "concentration_risk_hhi": None,
                "diversification_ratio": None,
                "effective_number_of_assets": None,
            },
        }
