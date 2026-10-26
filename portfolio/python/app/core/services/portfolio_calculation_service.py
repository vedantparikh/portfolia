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
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd  # type: ignore
import pyxirr  # type: ignore
from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    PortfolioBenchmark,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from core.domain.benchmark import shadow_series
from core.domain.fx import convert_closes, convert_trades
from core.domain.positions import OversellError, Split, to_trades
from core.domain.returns import compute_daily_returns, period_summary, split_period
from core.domain.valuation import MissingPriceError, daily_series
from core.errors import NotFoundError
from core.services.fx import load_rates
from core.services.market_data_service import MarketDataService
from core.services.utils import PeriodType

# Total-return series (accumulating ETFs, TR indices) per portfolio currency; first = default.
BENCHMARKS = {
    "EUR": [
        {"symbol": "EUNL.DE", "name": "MSCI World (iShares Core, Acc)"},
        {"symbol": "VWCE.DE", "name": "FTSE All-World (Vanguard, Acc)"},
        {"symbol": "SXR8.DE", "name": "S&P 500 (iShares Core, Acc)"},
        {"symbol": "SXRV.DE", "name": "Nasdaq-100 (iShares, Acc)"},
    ],
    "USD": [
        {"symbol": "^SP500TR", "name": "S&P 500 Total Return"},
    ],
}

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


class PortfolioCalculationService:
    """Service for comprehensive portfolio performance calculations."""

    def __init__(self, db: Session):
        self.db = db
        self.market_data_service = MarketDataService()
        # Cache for price data to avoid multiple API calls
        self._price_cache = {}
        self._price_cache_time = {}
        self._series_cache = {}

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
            raise NotFoundError(f"Portfolio {portfolio_id} not found")

        # Get all transactions for the portfolio
        all_transactions = self.get_transactions(portfolio_id, None, end_date)

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

        try:
            series = await self.get_portfolio_series(all_transactions, end_date)
        except (MissingPriceError, OversellError) as e:
            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "period": actual_period,
                "start_date": actual_start_date,
                "end_date": end_date,
                "current_value": 0.0,
                "errors": [str(e)],
                "period_adjustment": period_adjustment_info,
                "metrics": {"cagr": None, "xirr": None, "twr": None, "mwr": None},
                "calculation_date": datetime.now(timezone.utc).isoformat(),
            }

        summary = period_summary(
            series, actual_start_date.date() if actual_start_date else None
        )
        twr_value = summary.get("twr_pct")
        # CAGR is the annualised TWR; under a year it is the plain TWR
        cagr = summary.get("twr_annualized_pct")
        if cagr is None:
            cagr = twr_value
        xirr_value = summary.get("mwr_annualized_pct")

        result = {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "period": actual_period,
            "start_date": actual_start_date,
            "end_date": end_date,
            "current_value": summary.get("end_value", 0.0),
            "metrics": {
                "cagr": cagr,
                "xirr": xirr_value,
                "twr": twr_value,
                "mwr": summary.get("mwr_pct"),
                "volatility": summary.get("volatility_pct"),
                "max_drawdown": summary.get("max_drawdown_pct"),
            },
            "calculation_date": datetime.now(timezone.utc).isoformat(),
        }

        if period_adjustment_info:
            result["period_adjustment"] = period_adjustment_info

        return result

    # CAGR Calculation Methods
    def _calculate_cagr(
        self,
        twr_percent: Optional[float],
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[float]:
        """
        Compound Annual Growth Rate, computed as the annualised time-weighted return.

        Using TWR (rather than end value / net invested) keeps deposits and
        withdrawals from being counted as growth. Periods shorter than a year are
        not annualised (standard GIPS practice); the period return is returned.
        """
        if twr_percent is None:
            return None
        years = (end_date - start_date).days / 365.25
        if years <= 0:
            return 0.0
        growth = 1 + twr_percent / 100
        if years < 1:
            return float(twr_percent)
        if growth <= 0:
            return -100.0
        return float((growth ** (1 / years) - 1) * 100)

    # XIRR Calculation Methods
    async def _calculate_xirr(
        self,
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
                # For period calculations, the holdings at the start count as an
                # investment made at start_date. Only transactions strictly before
                # start_date are included so none is counted twice.
                prior_transactions = [
                    t for t in all_transactions if t.transaction_date < start_date
                ]
                initial_value = await self._get_portfolio_value_at_date(
                    prior_transactions, start_date
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

            # Add cash flows from transactions (date and amount always appended together)
            for transaction in period_transactions:
                amount = self._investor_cash_flow(transaction)
                if amount is not None:
                    dates.append(transaction.transaction_date)
                    amounts.append(amount)

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

    @staticmethod
    def _investor_cash_flow(transaction: Transaction) -> Optional[float]:
        """
        Cash flow from the investor's point of view: money in is negative, money
        back (sale proceeds, dividends) is positive. None for non-cash transactions.
        """
        if transaction.transaction_type == TransactionType.BUY:
            return -float(transaction.total_amount)
        if transaction.transaction_type in (
            TransactionType.SELL,
            TransactionType.DIVIDEND,
        ):
            return float(transaction.total_amount)
        return None

    # TWR Calculation Methods
    def _calculate_twr(
        self, portfolio_history: Optional[pd.DataFrame]
    ) -> Optional[float]:
        """
        Time-Weighted Return: geometrically linked cash-flow-adjusted daily returns.

        TWR = [(1 + r_1) x (1 + r_2) x ... x (1 + r_n)] - 1, see compute_daily_returns.
        """
        if portfolio_history is None or portfolio_history.empty:
            return None
        returns = portfolio_history["daily_return"].dropna()
        if returns.empty:
            return None
        return float(((1 + returns).prod() - 1) * 100)

    # Helper Methods
    async def _get_portfolio_value_at_date(
        self,
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

                price_data = await self.get_price_data(asset.symbol)
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

    async def get_price_data(self, symbol: str) -> pd.DataFrame:
        """Get price data for a symbol with caching."""
        try:
            # Check cache
            current_time = datetime.now(timezone.utc)
            if (
                symbol in self._price_cache
                and symbol in self._price_cache_time
                and (current_time - self._price_cache_time[symbol]).total_seconds()
                < 3600
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

    # Database Helper Methods
    def get_portfolio(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        """Get portfolio and verify ownership."""
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .first()
        )

    def get_transactions(
        self,
        portfolio_id: int,
        start_date: Optional[datetime],
        end_date: datetime,
    ) -> List[Transaction]:
        """Get completed transactions for a portfolio within date range."""
        query = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.transaction_date <= end_date,
        )

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)

        return query.order_by(Transaction.transaction_date).all()

    async def get_current_portfolio_value(
        self, portfolio_id: int
    ) -> tuple[float, list[str]]:
        """
        Get the current total value of the portfolio, fetch the latest asset
        prices, and update them in the database.

        Returns:
            Tuple of (total_value, error_messages)
        """
        try:
            # Query all assets belonging to the specified portfolio
            portfolio_assets = (
                self.db.query(PortfolioAsset)
                .filter(PortfolioAsset.portfolio_id == portfolio_id)
                .all()
            )

            total_portfolio_value = 0.0
            errors = []

            for asset in portfolio_assets:
                # Get the base asset info (like its symbol)
                asset_obj = (
                    self.db.query(Asset).filter(Asset.id == asset.asset_id).first()
                )
                if not asset_obj:
                    errors.append(
                        f"Asset metadata not found for PortfolioAsset ID {asset.id}"
                    )
                    continue

                # Fetch the new price from the market data service
                new_price = await self.market_data_service.get_current_price(
                    symbol=asset_obj.symbol
                )

                if new_price is not None:
                    # Calculate the new total value for this specific asset holding
                    new_asset_total_value = float(asset.quantity) * new_price
                    asset.current_value = new_asset_total_value

                    # Add to the running total for the whole portfolio
                    total_portfolio_value += new_asset_total_value
                else:
                    symbol = asset_obj.symbol
                    error_msg = f"Could not fetch new market value for {symbol} (quantity: {asset.quantity})"
                    logger.warning(error_msg)
                    errors.append(error_msg)

                    # Use the stale value for the total, but don't update the DB with it
                    if asset.current_value is not None:
                        total_portfolio_value += float(asset.current_value)

            self.db.commit()

            return total_portfolio_value, errors

        except Exception as e:
            error_msg = f"Error getting current portfolio value: {e}"
            logger.error(error_msg)
            return 0.0, [error_msg]

    # Utility Methods

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

    def _calculate_volatility(self, portfolio_history: pd.DataFrame) -> Optional[float]:
        """Annualised volatility of the cash-flow-adjusted daily returns, in percent."""
        if portfolio_history is None or portfolio_history.empty:
            return None

        daily_returns = portfolio_history["daily_return"].dropna()
        if len(daily_returns) < 2:
            return None
        return float(daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100)

    def _calculate_max_drawdown(
        self, portfolio_history: pd.DataFrame
    ) -> Optional[float]:
        """
        Largest peak-to-trough fall of the cumulative return curve, in percent.

        Uses the compounded cash-flow-adjusted returns, so deposits and withdrawals
        do not show up as gains or drawdowns.
        """
        if portfolio_history is None or portfolio_history.empty:
            return None

        daily_returns = portfolio_history["daily_return"].dropna()
        if daily_returns.empty:
            return None
        equity_curve = (1 + daily_returns).cumprod()
        drawdown = equity_curve / equity_curve.cummax() - 1
        return float(drawdown.min() * 100)

    async def get_market_history(
        self, asset_ids
    ) -> Tuple[
        Dict[int, pd.Series], Dict[int, List[Split]], Dict[int, str], Dict[int, str]
    ]:
        """Split-adjusted closes, split events and symbols for the given assets."""
        closes: Dict[int, pd.Series] = {}
        splits: Dict[int, List[Split]] = {}
        symbols: Dict[int, str] = {}
        currencies: Dict[int, str] = {}
        for asset_id in asset_ids:
            asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
            if not asset:
                raise NotFoundError(f"Asset {asset_id} not found")
            symbols[asset_id] = asset.symbol
            currencies[asset_id] = getattr(asset, "currency", None) or "USD"
            history = await self.market_data_service.get_daily_history(asset.symbol)
            if history is None:
                continue
            closes[asset_id] = history["close"]
            splits[asset_id] = [
                (day.date(), Decimal(str(ratio)))
                for day, ratio in history["splits"].items()
            ]
        return closes, splits, symbols, currencies

    async def get_portfolio_series(
        self, all_transactions: List[Transaction], end_date: datetime
    ) -> pd.DataFrame:
        """The canonical daily series from inception (see core.domain.valuation)."""
        key = (
            tuple(sorted(getattr(t, "id", None) or id(t) for t in all_transactions)),
            end_date.date(),
        )
        if key not in self._series_cache:
            asset_ids = sorted({t.asset_id for t in all_transactions})
            closes, splits, symbols, currencies = await self.get_market_history(
                asset_ids
            )
            portfolio_id = getattr(all_transactions[0], "portfolio_id", None)
            portfolio = (
                self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
                if portfolio_id is not None
                else None
            )
            portfolio_currency = getattr(portfolio, "currency", None) or "USD"
            cash_currency = {
                (getattr(tx, "id", None) or 0): getattr(tx, "currency", None)
                or portfolio_currency
                for tx in all_transactions
            }
            rates = await load_rates(
                self.market_data_service,
                portfolio_currency,
                list(currencies.values()) + list(cash_currency.values()),
            )
            closes = {
                asset_id: convert_closes(
                    series,
                    currencies.get(asset_id, portfolio_currency),
                    portfolio_currency,
                    rates,
                )
                for asset_id, series in closes.items()
            }
            trades = convert_trades(
                to_trades(all_transactions, splits),
                cash_currency,
                portfolio_currency,
                rates,
            )
            self._series_cache[key] = daily_series(
                trades, closes, end_date.date(), symbols
            )
        return self._series_cache[key]

    async def get_performance_series(
        self, portfolio_id: int, user_id: int, period: str
    ) -> Dict[str, Any]:
        """Daily points and the period summary the performance chart shows."""
        if not self.get_portfolio(portfolio_id, user_id):
            raise NotFoundError(f"Portfolio {portfolio_id} not found")
        end = datetime.now(timezone.utc)
        start = PeriodType.get_start_date(period, end)
        result: Dict[str, Any] = {
            "portfolio_id": portfolio_id,
            "period": period,
            "points": [],
        }
        transactions = self.get_transactions(portfolio_id, None, end)
        if not transactions:
            return result
        try:
            series = await self.get_portfolio_series(transactions, end)
        except (MissingPriceError, OversellError) as e:
            result["error"] = str(e)
            return result

        start_day = start.date() if start else None
        window, opening_value, _ = split_period(series, start_day)
        invested = opening_value + (window["inflow"] - window["outflow"]).cumsum()
        result["points"] = [
            {
                "date": day.date(),
                "value": row["value"],
                "invested": invested[day],
                "cost_basis": row["cost_basis"],
                "stale_price": bool(row["stale_price"]),
                "stale_symbols": list(row["stale_symbols"]),
            }
            for day, row in window.iterrows()
        ]
        result["summary"] = period_summary(series, start_day) or None
        return result

    def default_benchmark(self, portfolio: Portfolio) -> str:
        """The portfolio's primary benchmark, else the default for its currency."""
        primary = (
            self.db.query(PortfolioBenchmark)
            .filter(
                PortfolioBenchmark.portfolio_id == portfolio.id,
                PortfolioBenchmark.is_primary == True,
            )
            .first()
        )
        if primary and primary.benchmark_asset:
            return primary.benchmark_asset.symbol
        options = BENCHMARKS.get(portfolio.currency) or BENCHMARKS["USD"]
        return options[0]["symbol"]

    async def get_benchmark_comparison(
        self, portfolio_id: int, user_id: int, period: str, symbol: Optional[str]
    ) -> Dict[str, Any]:
        """The portfolio next to the same cash flows invested in a benchmark."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise NotFoundError(f"Portfolio {portfolio_id} not found")
        symbol = (symbol or self.default_benchmark(portfolio)).strip().upper()
        end = datetime.now(timezone.utc)
        start = PeriodType.get_start_date(period, end)
        info = await self.market_data_service.get_ticker_info(symbol) or {}
        currency = info.get("currency")
        result: Dict[str, Any] = {
            "portfolio_id": portfolio_id,
            "period": period,
            "benchmark": {
                "symbol": symbol,
                "name": info.get("long_name") or info.get("short_name") or symbol,
                "currency": currency,
            },
            "points": [],
            "warnings": [],
        }
        if currency is None:
            result["warnings"].append(
                f"{symbol} has no known currency; its prices are compared unconverted"
            )
        transactions = self.get_transactions(portfolio_id, None, end)
        if not transactions:
            return result
        history = await self.market_data_service.get_daily_history(symbol)
        if not history:
            result["error"] = f"No price history for {symbol}"
            return result
        try:
            series = await self.get_portfolio_series(transactions, end)
            start_day = start.date() if start else None
            benchmark_close = history["close"]
            if currency:
                rates = await load_rates(
                    self.market_data_service, portfolio.currency, [currency]
                )
                benchmark_close = convert_closes(
                    benchmark_close, currency, portfolio.currency, rates
                )
            shadow = shadow_series(series, benchmark_close, start_day)
        except (MissingPriceError, OversellError) as e:
            result["error"] = str(e)
            return result

        window, opening_value, _ = split_period(series, start_day)
        invested = opening_value + (window["inflow"] - window["outflow"]).cumsum()
        result["points"] = [
            {
                "date": day.date(),
                "value": row["value"],
                "benchmark_value": float(shadow.at[day, "value"]),
                "invested": invested[day],
                "stale_price": bool(row["stale_price"]),
                "stale_symbols": list(row["stale_symbols"]),
            }
            for day, row in window.iterrows()
        ]
        result["portfolio"] = period_summary(series, start_day) or None
        result["shadow"] = period_summary(shadow, start_day) or None
        if result["portfolio"] and result["shadow"]:
            result["difference"] = {
                key: None
                if result["portfolio"][key] is None or result["shadow"][key] is None
                else result["portfolio"][key] - result["shadow"][key]
                for key in ("end_value", "profit", "twr_pct", "mwr_pct")
            }
        paid_out = history["dividends"][history["dividends"].index >= shadow.index[0]]
        if not paid_out.empty:
            result["warnings"].append(
                f"{symbol} paid {len(paid_out)} dividends in this period that its price "
                "does not include; pick an accumulating ETF or a total-return index"
            )
        shortfall = float(shadow["shortfall"].iloc[-1])
        if shortfall > 0.005:
            result["warnings"].append(
                f"Withdrawals exceeded the benchmark holding by {shortfall:,.2f}; "
                "the shadow paid out what it had"
            )
        return result

    async def get_portfolio_history(
        self,
        all_transactions: List[Transaction],
        start_date: Optional[datetime],
        end_date: datetime,
    ) -> Optional[pd.DataFrame]:
        """
        Daily (trading-day) series of portfolio value and cash flows for a period.

        Columns:
            value         market value at the day's close
            inflow        cash invested that day (buys, including fees)
            outflow       cash returned that day (net sale proceeds, dividends)
            net_cash_flow inflow - outflow
            daily_return  cash-flow-adjusted return, see compute_daily_returns
        """
        try:
            if not all_transactions:
                return None
            series = await self.get_portfolio_series(all_transactions, end_date)
            window, opening_value, _ = split_period(
                series, start_date.date() if start_date else None
            )
            if window.empty:
                return None
            df = window[["value", "inflow", "outflow"]].copy()
            df["net_cash_flow"] = df["inflow"] - df["outflow"]
            df["daily_return"] = compute_daily_returns(df, opening_value)
            return df

        except Exception as e:
            logger.error("Error generating portfolio history: %s", e)
            return None
