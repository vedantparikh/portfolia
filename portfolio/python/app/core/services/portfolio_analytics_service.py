"""
Portfolio Analytics Service
Comprehensive service for portfolio analysis, risk management, and performance tracking.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionType,
)
from app.core.database.models.portfolio_analytics import (
    AssetCorrelation,
    AssetPerformanceMetrics,
    PortfolioAllocation,
    PortfolioPerformanceHistory,
    PortfolioRiskMetrics,
    RiskLevel,
)
from app.core.schemas.portfolio_analytics import (
    AllocationAnalysisResponse,
    AllocationDrift,
    AllocationItem,
    AssetMetricsResponse,
    PerformanceSnapshotResponse,
    PortfolioAllocationCreate,
    RiskCalculationResponse,
)
from app.core.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)


class PortfolioAnalyticsService:
    """Service for comprehensive portfolio analytics and risk management."""

    def __init__(self, db: Session):
        self.db = db
        # Data freshness thresholds
        self.asset_metrics_freshness_hours = 24  # Refresh asset metrics daily
        self.portfolio_performance_freshness_hours = (
            6  # Refresh portfolio performance every 6 hours
        )
        self.correlation_freshness_days = 7  # Refresh correlations weekly
        self.risk_metrics_freshness_hours = 12  # Refresh risk metrics every 12 hours

    def _is_data_fresh(self, last_update: datetime, freshness_hours: int) -> bool:
        """Check if data is fresh based on last update time."""
        if not last_update:
            return False

        now = datetime.now(timezone.utc)
        threshold = timedelta(hours=freshness_hours)
        return (now - last_update) < threshold

    # Portfolio Performance History
    async def get_or_create_performance_snapshot(
            self, portfolio_id: int, force_refresh: bool = False
    ) -> PerformanceSnapshotResponse:
        """Get portfolio performance snapshot, auto-refreshing with yfinance if stale."""
        # If force refresh is requested, always create new snapshot
        if force_refresh:
            logger.info(f"Force refreshing performance snapshot for portfolio {portfolio_id}")
            return await self.create_performance_snapshot(portfolio_id, datetime.now(timezone.utc))

        # Check for existing fresh snapshot first
        existing_snapshot = (
            self.db.query(PortfolioPerformanceHistory)
            .filter(PortfolioPerformanceHistory.portfolio_id == portfolio_id)
            .order_by(PortfolioPerformanceHistory.snapshot_date.desc())
            .first()
        )

        if existing_snapshot and self._is_data_fresh(
                existing_snapshot.created_at, self.portfolio_performance_freshness_hours
        ):
            # Return existing fresh data
            return PerformanceSnapshotResponse(
                id=existing_snapshot.id,
                portfolio_id=existing_snapshot.portfolio_id,
                snapshot_date=existing_snapshot.snapshot_date,
                total_value=existing_snapshot.total_value,
                total_cost_basis=existing_snapshot.total_cost_basis,
                total_unrealized_pnl=existing_snapshot.total_unrealized_pnl,
                total_unrealized_pnl_percent=existing_snapshot.total_unrealized_pnl_percent,
                created_at=existing_snapshot.created_at,
            )

        # Data is stale - create new snapshot
        return await self.create_performance_snapshot(portfolio_id, datetime.now(timezone.utc))

    async def create_performance_snapshot(
            self, portfolio_id: int, snapshot_date: Optional[datetime] = None
    ) -> PerformanceSnapshotResponse:
        """Create a performance snapshot for a portfolio."""
        if snapshot_date is None:
            snapshot_date = datetime.now(timezone.utc)

        # Get portfolio assets
        portfolio_assets = (
            self.db.query(PortfolioAsset)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        if not portfolio_assets:
            raise ValueError("Portfolio has no assets")

        # Calculate basic metrics using real-time prices from yfinance
        total_cost_basis = sum(
            float(asset.cost_basis_total) for asset in portfolio_assets
        )
        total_current_value = 0

        # Get current prices for all assets
        for asset in portfolio_assets:
            if asset.asset and asset.asset.symbol:
                current_price = await market_data_service.get_current_price(
                    asset.asset.symbol
                )
                if current_price:
                    total_current_value += float(current_price) * float(asset.quantity)
                else:
                    # Fallback to cost basis if price unavailable
                    total_current_value += float(asset.cost_basis_total)
            else:
                total_current_value += float(asset.cost_basis_total)

        total_unrealized_pnl = total_current_value - total_cost_basis
        total_unrealized_pnl_percent = (
            (total_unrealized_pnl / total_cost_basis * 100)
            if total_cost_basis > 0
            else 0
        )

        # Calculate performance metrics
        performance_metrics = await self._calculate_portfolio_performance_metrics(
            portfolio_id, snapshot_date
        )

        # Create snapshot
        snapshot = PortfolioPerformanceHistory(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            total_value=Decimal(str(total_current_value)),
            total_cost_basis=Decimal(str(total_cost_basis)),
            total_unrealized_pnl=Decimal(str(total_unrealized_pnl)),
            total_unrealized_pnl_percent=Decimal(str(total_unrealized_pnl_percent)),
            **performance_metrics,
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        # Return schema response with all available fields
        return PerformanceSnapshotResponse(
            id=snapshot.id,
            portfolio_id=snapshot.portfolio_id,
            snapshot_date=snapshot.snapshot_date,
            total_value=snapshot.total_value,
            total_cost_basis=snapshot.total_cost_basis,
            total_unrealized_pnl=snapshot.total_unrealized_pnl,
            total_unrealized_pnl_percent=snapshot.total_unrealized_pnl_percent,
            created_at=snapshot.created_at,
        )

    async def _calculate_portfolio_performance_metrics(
            self, portfolio_id: int, snapshot_date: datetime
    ) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        # Get historical performance data
        end_date = snapshot_date
        start_date = end_date - timedelta(days=365)  # 1 year lookback

        # Get daily returns for the portfolio
        daily_returns = await self._get_portfolio_daily_returns(
            portfolio_id, start_date, end_date
        )

        if len(daily_returns) < 30:  # Need at least 30 days of data
            return {}

        # Calculate metrics
        metrics = {}

        # Basic returns
        total_return = (daily_returns.iloc[-1] / daily_returns.iloc[0]) - 1
        metrics["cumulative_return"] = Decimal(str(total_return))

        # Annualized return
        days = len(daily_returns)
        annualized_return = (1 + total_return) ** (365 / days) - 1
        metrics["annualized_return"] = Decimal(str(annualized_return))

        # Volatility (annualized)
        daily_volatility = daily_returns.pct_change().std()
        annualized_volatility = daily_volatility * math.sqrt(252)
        metrics["volatility"] = Decimal(str(annualized_volatility))

        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        metrics["sharpe_ratio"] = Decimal(str(sharpe_ratio))

        # Maximum drawdown
        cumulative_returns = (1 + daily_returns.pct_change()).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        metrics["max_drawdown"] = Decimal(str(max_drawdown))

        # Value at Risk (95% and 99%)
        returns = daily_returns.pct_change().dropna()
        var_95 = returns.quantile(0.05)
        var_99 = returns.quantile(0.01)
        metrics["var_95"] = Decimal(str(var_95))
        metrics["var_99"] = Decimal(str(var_99))

        return metrics

    async def _get_portfolio_daily_returns(
            self, portfolio_id: int, start_date: datetime, end_date: datetime
    ) -> pd.Series:
        """Get daily portfolio returns using yfinance historical data."""
        # Get portfolio assets
        portfolio_assets = (
            self.db.query(PortfolioAsset)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        if not portfolio_assets:
            return pd.Series()

        # Fetch historical data for each asset and calculate portfolio values
        portfolio_values = {}
        total_weights = 0

        for asset in portfolio_assets:
            if asset.asset and asset.asset.symbol:
                try:
                    # Get historical price data
                    end_date_str = end_date.strftime("%Y-%m-%d")
                    start_date_str = start_date.strftime("%Y-%m-%d")

                    price_data = await market_data_service.fetch_ticker_data(
                        symbol=asset.asset.symbol,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        interval="1d",
                    )

                    if price_data is not None and len(price_data) > 0:
                        # Calculate asset value over time
                        asset_quantities = float(asset.quantity)

                        for _, row in price_data.iterrows():
                            date = row["Date"]
                            if isinstance(date, str):
                                date = datetime.strptime(date[:10], "%Y-%m-%d").date()
                            elif hasattr(date, 'date'):
                                date = date.date()

                            asset_value = float(row["Close"]) * asset_quantities

                            if date not in portfolio_values:
                                portfolio_values[date] = 0
                            portfolio_values[date] += asset_value

                        total_weights += float(asset.cost_basis_total)
                    else:
                        # Fallback to cost basis if no historical data
                        logger.warning(f"No historical data for {asset.asset.symbol}, using cost basis")
                        date_range = pd.date_range(start_date, end_date, freq="D")
                        for date in date_range:
                            date_key = date.date()
                            if date_key not in portfolio_values:
                                portfolio_values[date_key] = 0
                            portfolio_values[date_key] += float(asset.cost_basis_total)

                except Exception as e:
                    logger.warning(f"Failed to get historical data for {asset.asset.symbol}: {e}")
                    # Fallback to cost basis
                    date_range = pd.date_range(start_date, end_date, freq="D")
                    for date in date_range:
                        date_key = date.date()
                        if date_key not in portfolio_values:
                            portfolio_values[date_key] = 0
                        portfolio_values[date_key] += float(asset.cost_basis_total)
            else:
                # No symbol, use cost basis
                date_range = pd.date_range(start_date, end_date, freq="D")
                for date in date_range:
                    date_key = date.date()
                    if date_key not in portfolio_values:
                        portfolio_values[date_key] = 0
                    portfolio_values[date_key] += float(asset.cost_basis_total)

        # Convert to pandas Series
        if portfolio_values:
            sorted_dates = sorted(portfolio_values.keys())
            values = [portfolio_values[date] for date in sorted_dates]
            date_index = pd.to_datetime(sorted_dates)
            return pd.Series(values, index=date_index)
        else:
            # Fallback: create a simple series with current portfolio value
            total_current_value = sum(float(asset.cost_basis_total) for asset in portfolio_assets)
            date_range = pd.date_range(start_date, end_date, freq="D")
            values = [total_current_value] * len(date_range)
            return pd.Series(values, index=date_range)

    # Asset Performance Metrics
    async def get_or_calculate_asset_metrics(
            self, asset_id: int, force_refresh: bool = False
    ) -> AssetMetricsResponse:
        """Get asset metrics, automatically refreshing with yfinance data if stale."""
        # If force refresh is requested, always calculate new metrics
        if force_refresh:
            logger.info(f"Force refreshing asset metrics for asset {asset_id}")
            return await self.calculate_asset_metrics(asset_id, datetime.now(timezone.utc))

        # Check for existing fresh metrics first
        existing_metrics = (
            self.db.query(AssetPerformanceMetrics)
            .filter(AssetPerformanceMetrics.asset_id == asset_id)
            .order_by(AssetPerformanceMetrics.calculation_date.desc())
            .first()
        )

        if existing_metrics and self._is_data_fresh(
                existing_metrics.created_at, self.asset_metrics_freshness_hours
        ):
            # Return existing fresh data
            return AssetMetricsResponse(
                id=existing_metrics.id,
                asset_id=existing_metrics.asset_id,
                calculation_date=existing_metrics.calculation_date,
                current_price=existing_metrics.current_price,
                price_change=existing_metrics.price_change,
                price_change_percent=existing_metrics.price_change_percent,
                sma_20=existing_metrics.sma_20,
                sma_50=existing_metrics.sma_50,
                sma_200=existing_metrics.sma_200,
                ema_12=existing_metrics.ema_12,
                ema_26=existing_metrics.ema_26,
                rsi=existing_metrics.rsi,
                macd=existing_metrics.macd,
                macd_signal=existing_metrics.macd_signal,
                macd_histogram=existing_metrics.macd_histogram,
                stochastic_k=existing_metrics.stochastic_k,
                stochastic_d=existing_metrics.stochastic_d,
                bollinger_upper=existing_metrics.bollinger_upper,
                bollinger_middle=existing_metrics.bollinger_middle,
                bollinger_lower=existing_metrics.bollinger_lower,
                atr=existing_metrics.atr,
                volume_sma=existing_metrics.volume_sma,
                volume_ratio=existing_metrics.volume_ratio,
                obv=existing_metrics.obv,
                volatility_20d=existing_metrics.volatility_20d,
                volatility_60d=existing_metrics.volatility_60d,
                volatility_252d=existing_metrics.volatility_252d,
                beta=existing_metrics.beta,
                sharpe_ratio=existing_metrics.sharpe_ratio,
                total_return_1m=existing_metrics.total_return_1m,
                total_return_3m=existing_metrics.total_return_3m,
                total_return_1y=existing_metrics.total_return_1y,
                created_at=existing_metrics.created_at,
            )

        # Data is stale - calculate new metrics
        return await self.calculate_asset_metrics(asset_id, datetime.now(timezone.utc))

    async def calculate_asset_metrics(
            self, asset_id: int, calculation_date: Optional[datetime] = None
    ) -> AssetMetricsResponse:
        """Calculate comprehensive metrics for an asset using yfinance data."""
        if calculation_date is None:
            calculation_date = datetime.now(timezone.utc)

        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset or not asset.symbol:
            raise ValueError("Asset not found or missing symbol")

        # Get historical data from yfinance (1 year lookback)
        end_date_str = calculation_date.strftime("%Y-%m-%d")
        start_date_str = (calculation_date - timedelta(days=365)).strftime("%Y-%m-%d")

        price_data = await market_data_service.fetch_ticker_data(
            symbol=asset.symbol,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d",
        )

        if price_data is None or len(price_data) < 30:
            raise ValueError("Insufficient price data for calculations")

        # Get current price and calculate basic metrics
        current_price = await market_data_service.get_current_price(asset.symbol)
        if not current_price:
            current_price = float(price_data["Close"].iloc[-1])

        # Calculate price change
        previous_close = (
            float(price_data["Close"].iloc[-2])
            if len(price_data) > 1
            else current_price
        )
        price_change = current_price - previous_close
        price_change_percent = (
            (price_change / previous_close) * 100 if previous_close > 0 else 0
        )

        # Calculate technical indicators using the price data
        metrics = self._calculate_technical_indicators_from_yfinance(price_data)

        # Calculate risk and performance metrics
        risk_metrics = self._calculate_risk_metrics_from_yfinance(price_data)
        performance_metrics = self._calculate_performance_metrics_from_yfinance(
            price_data
        )

        # Create and save metrics record
        asset_metrics = AssetPerformanceMetrics(
            asset_id=asset_id,
            calculation_date=calculation_date,
            current_price=Decimal(str(current_price)),
            price_change=Decimal(str(price_change)) if price_change else None,
            price_change_percent=(
                Decimal(str(price_change_percent)) if price_change_percent else None
            ),
            **metrics,
            **risk_metrics,
            **performance_metrics,
        )

        self.db.add(asset_metrics)
        self.db.commit()
        self.db.refresh(asset_metrics)

        # Return comprehensive schema response with all available fields matching database model
        return AssetMetricsResponse(
            id=asset_metrics.id,
            asset_id=asset_metrics.asset_id,
            calculation_date=asset_metrics.calculation_date,
            current_price=asset_metrics.current_price,
            price_change=asset_metrics.price_change,
            price_change_percent=asset_metrics.price_change_percent,
            # Technical indicators
            sma_20=asset_metrics.sma_20,
            sma_50=asset_metrics.sma_50,
            sma_200=asset_metrics.sma_200,
            ema_12=asset_metrics.ema_12,
            ema_26=asset_metrics.ema_26,
            # Momentum indicators
            rsi=asset_metrics.rsi,
            macd=asset_metrics.macd,
            macd_signal=asset_metrics.macd_signal,
            macd_histogram=asset_metrics.macd_histogram,
            stochastic_k=asset_metrics.stochastic_k,
            stochastic_d=asset_metrics.stochastic_d,
            # Volatility indicators
            bollinger_upper=asset_metrics.bollinger_upper,
            bollinger_middle=asset_metrics.bollinger_middle,
            bollinger_lower=asset_metrics.bollinger_lower,
            atr=asset_metrics.atr,
            # Volume indicators
            volume_sma=asset_metrics.volume_sma,
            volume_ratio=asset_metrics.volume_ratio,
            obv=asset_metrics.obv,
            # Risk metrics
            volatility_20d=asset_metrics.volatility_20d,
            volatility_60d=asset_metrics.volatility_60d,
            volatility_252d=asset_metrics.volatility_252d,
            beta=asset_metrics.beta,
            sharpe_ratio=asset_metrics.sharpe_ratio,
            # Performance metrics
            total_return_1m=asset_metrics.total_return_1m,
            total_return_3m=asset_metrics.total_return_3m,
            total_return_1y=asset_metrics.total_return_1y,
            created_at=asset_metrics.created_at,
        )

    def _calculate_technical_indicators_from_yfinance(
            self, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate technical indicators from yfinance data."""
        metrics = {}

        try:
            # Moving averages
            if len(price_data) >= 20:
                metrics["sma_20"] = Decimal(
                    str(price_data["Close"].rolling(20).mean().iloc[-1])
                )
            if len(price_data) >= 50:
                metrics["sma_50"] = Decimal(
                    str(price_data["Close"].rolling(50).mean().iloc[-1])
                )
            if len(price_data) >= 200:
                metrics["sma_200"] = Decimal(
                    str(price_data["Close"].rolling(200).mean().iloc[-1])
                )

            # Exponential moving averages
            if len(price_data) >= 12:
                metrics["ema_12"] = Decimal(
                    str(price_data["Close"].ewm(span=12).mean().iloc[-1])
                )
            if len(price_data) >= 26:
                metrics["ema_26"] = Decimal(
                    str(price_data["Close"].ewm(span=26).mean().iloc[-1])
                )

            # RSI
            if len(price_data) >= 14:
                delta = price_data["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                metrics["rsi"] = Decimal(str(rsi.iloc[-1]))

            # Volume indicators
            if "Volume" in price_data.columns and len(price_data) >= 20:
                metrics["volume_sma"] = Decimal(
                    str(price_data["Volume"].rolling(20).mean().iloc[-1])
                )

        except Exception:
            # If calculation fails, set None values
            pass

        return metrics

    def _calculate_risk_metrics_from_yfinance(
            self, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate risk metrics from yfinance data."""
        metrics = {}

        try:
            # Calculate returns
            returns = price_data["Close"].pct_change().dropna()

            # Volatility
            if len(returns) >= 20:
                metrics["volatility_20d"] = Decimal(
                    str(returns.rolling(20).std().iloc[-1] * np.sqrt(252))
                )
            if len(returns) >= 60:
                metrics["volatility_60d"] = Decimal(
                    str(returns.rolling(60).std().iloc[-1] * np.sqrt(252))
                )

            # Sharpe ratio (assuming risk-free rate of 2%)
            if len(returns) >= 252:
                excess_returns = returns - 0.02 / 252  # Daily risk-free rate
                metrics["sharpe_ratio"] = Decimal(
                    str(excess_returns.mean() / excess_returns.std() * np.sqrt(252))
                )

            # Max drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = Decimal(str(drawdown.min()))

        except Exception:
            # If calculation fails, set None values
            pass

        return metrics

    def _calculate_performance_metrics_from_yfinance(
            self, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate performance metrics from yfinance data."""
        metrics = {}

        try:
            # Calculate returns for different periods
            current_price = price_data["Close"].iloc[-1]

            # 1-day return
            if len(price_data) >= 2:
                metrics["total_return_1d"] = Decimal(
                    str((current_price / price_data["Close"].iloc[-2] - 1) * 100)
                )

            # 1-week return
            if len(price_data) >= 7:
                metrics["total_return_1w"] = Decimal(
                    str((current_price / price_data["Close"].iloc[-7] - 1) * 100)
                )

            # 1-month return
            if len(price_data) >= 30:
                metrics["total_return_1m"] = Decimal(
                    str((current_price / price_data["Close"].iloc[-30] - 1) * 100)
                )

            # 3-month return
            if len(price_data) >= 90:
                metrics["total_return_3m"] = Decimal(
                    str((current_price / price_data["Close"].iloc[-90] - 1) * 100)
                )

            # 1-year return
            if len(price_data) >= 252:
                metrics["total_return_1y"] = Decimal(
                    str((current_price / price_data["Close"].iloc[-252] - 1) * 100)
                )

        except Exception:
            # If calculation fails, set None values
            pass

        return metrics

    async def analyze_portfolio_allocation(
            self, portfolio_id: int
    ) -> AllocationAnalysisResponse:
        """Analyze portfolio allocation and detect drift from targets."""
        # Get portfolio assets with current values
        portfolio_assets = (
            self.db.query(PortfolioAsset)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        if not portfolio_assets:
            raise ValueError("Portfolio has no assets")

        # Calculate current allocations using real-time prices
        current_allocations = []
        total_current_value = 0

        for asset in portfolio_assets:
            if asset.asset and asset.asset.symbol:
                current_price = await market_data_service.get_current_price(
                    asset.asset.symbol
                )
                if current_price:
                    current_value = float(current_price) * float(asset.quantity)
                else:
                    current_value = float(asset.cost_basis_total)
            else:
                current_value = float(asset.cost_basis_total)

            total_current_value += current_value

            current_allocations.append({"asset": asset, "current_value": current_value})

        # Calculate allocation percentages and create AllocationItem objects
        allocation_items = []
        allocation_drifts = []
        total_drift = Decimal("0")
        rebalancing_needed = False

        for allocation in current_allocations:
            asset = allocation["asset"]
            current_value = allocation["current_value"]
            current_percentage = (
                Decimal(str((current_value / total_current_value) * 100))
                if total_current_value > 0
                else Decimal("0")
            )

            # Get target allocation if exists
            target_allocation = (
                self.db.query(PortfolioAllocation)
                .filter(
                    PortfolioAllocation.portfolio_id == portfolio_id,
                    PortfolioAllocation.asset_id == asset.asset_id,
                    PortfolioAllocation.is_active == True,
                )
                .first()
            )

            target_percentage = (
                target_allocation.target_percentage if target_allocation else None
            )

            allocation_item = AllocationItem(
                asset_id=asset.asset_id,
                asset_symbol=asset.asset.symbol if asset.asset else "Unknown",
                asset_name=asset.asset.name if asset.asset else None,
                current_percentage=current_percentage,
                target_percentage=target_percentage,
                current_value=Decimal(str(current_value)),
                quantity=asset.quantity,
            )
            allocation_items.append(allocation_item)

            # Calculate drift if target exists
            if target_percentage:
                drift_percentage = current_percentage - target_percentage
                drift_amount = Decimal(str(total_current_value)) * (
                        drift_percentage / 100
                )
                requires_rebalancing = abs(drift_percentage) > Decimal(
                    "5"
                )  # 5% threshold

                if requires_rebalancing:
                    rebalancing_needed = True

                total_drift += abs(drift_percentage)

                allocation_drift = AllocationDrift(
                    asset_id=asset.asset_id,
                    asset_symbol=asset.asset.symbol if asset.asset else "Unknown",
                    current_percentage=current_percentage,
                    target_percentage=target_percentage,
                    drift_percentage=drift_percentage,
                    drift_amount=drift_amount,
                    requires_rebalancing=requires_rebalancing,
                    recommended_action=(
                        "buy"
                        if drift_percentage < 0
                        else "sell" if drift_percentage > 0 else "hold"
                    ),
                )
                allocation_drifts.append(allocation_drift)

        return AllocationAnalysisResponse(
            portfolio_id=portfolio_id,
            current_allocations=allocation_items,
            target_allocations=[
                item for item in allocation_items if item.target_percentage is not None
            ],
            allocation_drift=allocation_drifts,
            total_drift_percentage=total_drift,
            rebalancing_needed=rebalancing_needed,
            analysis_date=datetime.now(timezone.utc),
        )

    async def get_or_calculate_portfolio_risk_metrics(
            self, portfolio_id: int, force_refresh: bool = False
    ) -> RiskCalculationResponse:
        """Get portfolio risk metrics, auto-refreshing with yfinance if stale."""
        # If force refresh is requested, always calculate new metrics
        if force_refresh:
            logger.info(f"Force refreshing risk metrics for portfolio {portfolio_id}")
            return await self.calculate_portfolio_risk_metrics(
                portfolio_id, datetime.now(timezone.utc)
            )

        # Check for existing fresh risk metrics first
        existing_risk = (
            self.db.query(PortfolioRiskMetrics)
            .filter(PortfolioRiskMetrics.portfolio_id == portfolio_id)
            .order_by(PortfolioRiskMetrics.calculation_date.desc())
            .first()
        )

        if existing_risk and self._is_data_fresh(
                existing_risk.created_at, self.risk_metrics_freshness_hours
        ):
            # Return existing fresh data
            return RiskCalculationResponse(
                portfolio_id=existing_risk.portfolio_id,
                calculation_date=existing_risk.calculation_date,
                risk_level=existing_risk.risk_level,
                portfolio_volatility=existing_risk.portfolio_volatility,
                var_95=existing_risk.var_95_1d,
                var_99=existing_risk.var_99_1d,
                expected_shortfall_95=existing_risk.cvar_95_1d,
                expected_shortfall_99=existing_risk.cvar_99_1d,
                max_drawdown=existing_risk.max_drawdown,
                sharpe_ratio=existing_risk.sharpe_ratio,
                sortino_ratio=existing_risk.sortino_ratio,
                beta=existing_risk.portfolio_beta,
                correlation_to_market=existing_risk.average_correlation,
            )

        # Data is stale - calculate new metrics
        return await self.calculate_portfolio_risk_metrics(
            portfolio_id, datetime.now(timezone.utc)
        )

    async def calculate_portfolio_risk_metrics(
            self, portfolio_id: int, calculation_date: Optional[datetime] = None
    ) -> RiskCalculationResponse:
        """Calculate comprehensive risk metrics for a portfolio."""
        if calculation_date is None:
            calculation_date = datetime.now(timezone.utc)

        # Get portfolio assets
        portfolio_assets = (
            self.db.query(PortfolioAsset)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        if not portfolio_assets:
            raise ValueError("Portfolio has no assets")

        # Calculate portfolio volatility and other risk metrics
        # This is a simplified implementation - in practice you'd want more sophisticated calculations
        portfolio_volatility = Decimal("15.0")  # Placeholder
        var_95 = Decimal("5.0")  # Placeholder
        var_99 = Decimal("8.0")  # Placeholder

        # Create risk metrics record
        risk_metrics = PortfolioRiskMetrics(
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            risk_level=RiskLevel.MODERATE,
            portfolio_volatility=portfolio_volatility,
            var_95_1d=var_95,
            var_99_1d=var_99,
        )

        self.db.add(risk_metrics)
        self.db.commit()
        self.db.refresh(risk_metrics)

        return RiskCalculationResponse(
            portfolio_id=risk_metrics.portfolio_id,
            calculation_date=risk_metrics.calculation_date,
            risk_level=risk_metrics.risk_level,
            portfolio_volatility=risk_metrics.portfolio_volatility,
            var_95=risk_metrics.var_95_1d,
            var_99=risk_metrics.var_99_1d,
            expected_shortfall_95=None,
            expected_shortfall_99=None,
            max_drawdown=None,
            sharpe_ratio=None,
            sortino_ratio=None,
            beta=None,
            correlation_to_market=None,
        )

    def _calculate_technical_indicators(
            self, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate technical indicators for an asset."""
        metrics = {}

        # Moving averages
        metrics["sma_20"] = Decimal(
            str(price_data["close"].rolling(20).mean().iloc[-1])
        )
        metrics["sma_50"] = Decimal(
            str(price_data["close"].rolling(50).mean().iloc[-1])
        )
        metrics["sma_200"] = Decimal(
            str(price_data["close"].rolling(200).mean().iloc[-1])
        )

        # Exponential moving averages
        metrics["ema_12"] = Decimal(
            str(price_data["close"].ewm(span=12).mean().iloc[-1])
        )
        metrics["ema_26"] = Decimal(
            str(price_data["close"].ewm(span=26).mean().iloc[-1])
        )

        # RSI
        delta = price_data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        metrics["rsi"] = Decimal(str(rsi.iloc[-1]))

        # MACD
        ema_12 = price_data["close"].ewm(span=12).mean()
        ema_26 = price_data["close"].ewm(span=26).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9).mean()
        macd_histogram = macd - macd_signal

        metrics["macd"] = Decimal(str(macd.iloc[-1]))
        metrics["macd_signal"] = Decimal(str(macd_signal.iloc[-1]))
        metrics["macd_histogram"] = Decimal(str(macd_histogram.iloc[-1]))

        # Bollinger Bands
        sma_20 = price_data["close"].rolling(20).mean()
        std_20 = price_data["close"].rolling(20).std()
        metrics["bollinger_upper"] = Decimal(str((sma_20 + (std_20 * 2)).iloc[-1]))
        metrics["bollinger_middle"] = Decimal(str(sma_20.iloc[-1]))
        metrics["bollinger_lower"] = Decimal(str((sma_20 - (std_20 * 2)).iloc[-1]))

        # ATR
        high_low = price_data["high"] - price_data["low"]
        high_close = np.abs(price_data["high"] - price_data["close"].shift())
        low_close = np.abs(price_data["low"] - price_data["close"].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean()
        metrics["atr"] = Decimal(str(atr.iloc[-1]))

        return metrics

    def _calculate_risk_metrics(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate risk metrics for an asset."""
        metrics = {}

        # Volatility calculations
        returns = price_data["close"].pct_change().dropna()
        metrics["volatility_20d"] = Decimal(
            str(returns.rolling(20).std().iloc[-1] * math.sqrt(252))
        )
        metrics["volatility_60d"] = Decimal(
            str(returns.rolling(60).std().iloc[-1] * math.sqrt(252))
        )
        metrics["volatility_252d"] = Decimal(str(returns.std() * math.sqrt(252)))

        # Beta calculation (simplified - would need market data)
        # For now, set to 1.0 as placeholder
        metrics["beta"] = Decimal("1.0")

        # Sharpe ratio (simplified)
        annual_return = returns.mean() * 252
        annual_volatility = returns.std() * math.sqrt(252)
        sharpe_ratio = (
            (annual_return - 0.02) / annual_volatility if annual_volatility > 0 else 0
        )
        metrics["sharpe_ratio"] = Decimal(str(sharpe_ratio))

        return metrics

    def _calculate_performance_metrics(
            self, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate performance metrics for an asset."""
        metrics = {}

        current_price = price_data["close"].iloc[-1]

        # Calculate returns for different periods
        periods = {
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "3y": 1095,
            "5y": 1825,
        }

        for period_name, days in periods.items():
            if len(price_data) >= days:
                start_price = price_data["close"].iloc[-days]
                total_return = (current_price / start_price) - 1
                metrics[f"total_return_{period_name}"] = Decimal(str(total_return))
            else:
                metrics[f"total_return_{period_name}"] = None

        return metrics

    # Portfolio Allocation Management
    def set_portfolio_allocation(
            self, portfolio_id: int, allocations: List[PortfolioAllocationCreate]
    ) -> List[PortfolioAllocation]:
        """Set target allocations for a portfolio."""
        # Clear existing allocations
        self.db.query(PortfolioAllocation).filter(
            PortfolioAllocation.portfolio_id == portfolio_id
        ).delete()

        # Create new allocations
        new_allocations = []
        for allocation_data in allocations:
            allocation = PortfolioAllocation(
                portfolio_id=portfolio_id,
                asset_id=allocation_data.asset_id,
                target_percentage=allocation_data.target_percentage,
                min_percentage=allocation_data.min_percentage,
                max_percentage=allocation_data.max_percentage,
                rebalance_threshold=allocation_data.rebalance_threshold,
                rebalance_frequency=allocation_data.rebalance_frequency,
                is_active=allocation_data.is_active,
            )
            self.db.add(allocation)
            new_allocations.append(allocation)

        self.db.commit()
        for allocation in new_allocations:
            self.db.refresh(allocation)

        return new_allocations

    async def get_portfolio_analytics_summary(
            self, portfolio_id: int
    ) -> Dict[str, Any]:
        """Get comprehensive portfolio analytics summary."""
        try:
            # Get portfolio assets
            portfolio_assets = (
                self.db.query(PortfolioAsset)
                .filter(PortfolioAsset.portfolio_id == portfolio_id)
                .all()
            )

            if not portfolio_assets:
                raise ValueError("Portfolio has no assets")

            # Calculate basic metrics using real-time prices
            total_cost_basis = sum(
                float(asset.cost_basis_total) for asset in portfolio_assets
            )
            total_current_value = 0

            # Get current prices for all assets
            for asset in portfolio_assets:
                if asset.asset and asset.asset.symbol:
                    current_price = await market_data_service.get_current_price(
                        asset.asset.symbol
                    )
                    if current_price:
                        total_current_value += float(current_price) * float(
                            asset.quantity
                        )
                    else:
                        total_current_value += float(asset.cost_basis_total)
                else:
                    total_current_value += float(asset.cost_basis_total)

            total_unrealized_pnl = total_current_value - total_cost_basis
            total_unrealized_pnl_percent = (
                (total_unrealized_pnl / total_cost_basis * 100)
                if total_cost_basis > 0
                else 0
            )

            # Get latest performance snapshot
            latest_snapshot = (
                self.db.query(PortfolioPerformanceHistory)
                .filter(PortfolioPerformanceHistory.portfolio_id == portfolio_id)
                .order_by(PortfolioPerformanceHistory.snapshot_date.desc())
                .first()
            )

            # Get latest risk metrics
            latest_risk = (
                self.db.query(PortfolioRiskMetrics)
                .filter(PortfolioRiskMetrics.portfolio_id == portfolio_id)
                .order_by(PortfolioRiskMetrics.calculation_date.desc())
                .first()
            )

            # Get portfolio info
            portfolio = (
                self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            )

            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name if portfolio else "Unknown",
                "calculation_date": datetime.now(timezone.utc),
                "total_value": Decimal(str(total_current_value)),
                "total_cost_basis": Decimal(str(total_cost_basis)),
                "total_unrealized_pnl": Decimal(str(total_unrealized_pnl)),
                "total_unrealized_pnl_percent": Decimal(
                    str(total_unrealized_pnl_percent)
                ),
                # Performance metrics from latest snapshot
                "total_return": (
                    latest_snapshot.cumulative_return if latest_snapshot else None
                ),
                "annualized_return": (
                    latest_snapshot.annualized_return if latest_snapshot else None
                ),
                "volatility": latest_snapshot.volatility if latest_snapshot else None,
                "sharpe_ratio": (
                    latest_snapshot.sharpe_ratio if latest_snapshot else None
                ),
                "sortino_ratio": None,  # Would need to be calculated
                "max_drawdown": (
                    latest_snapshot.max_drawdown if latest_snapshot else None
                ),
                # Risk metrics from latest calculation
                "risk_level": latest_risk.risk_level if latest_risk else None,
                "portfolio_volatility": (
                    latest_risk.portfolio_volatility if latest_risk else None
                ),
                "var_95": latest_risk.var_95_1d if latest_risk else None,
                "var_99": latest_risk.var_99_1d if latest_risk else None,
                "beta": latest_risk.portfolio_beta if latest_risk else None,
                "alpha": latest_risk.portfolio_alpha if latest_risk else None,
                # Diversification metrics
                "concentration_risk": (
                    latest_risk.concentration_risk if latest_risk else None
                ),
                "effective_number_of_assets": (
                    latest_risk.effective_number_of_assets if latest_risk else None
                ),
                "diversification_ratio": (
                    latest_risk.diversification_ratio if latest_risk else None
                ),
                # Benchmark comparison
                "benchmark_name": None,  # Would need to get from benchmark table
                "benchmark_return": (
                    latest_snapshot.benchmark_return if latest_snapshot else None
                ),
                "tracking_error": (
                    latest_snapshot.tracking_error if latest_snapshot else None
                ),
                "information_ratio": (
                    latest_snapshot.information_ratio if latest_snapshot else None
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get portfolio analytics summary: {e}")
            raise

    async def get_rebalancing_recommendation(self, portfolio_id: int) -> Dict[str, Any]:
        """Get rebalancing recommendations for a portfolio."""
        try:
            # Get current allocation analysis
            allocation_analysis = await self.analyze_portfolio_allocation(portfolio_id)

            # Check if rebalancing is needed
            if not allocation_analysis.rebalancing_needed:
                return {
                    "portfolio_id": portfolio_id,
                    "recommendation_date": datetime.now(timezone.utc),
                    "trigger_reason": "no_rebalancing_needed",
                    "current_drift": allocation_analysis.total_drift_percentage,
                    "rebalancing_actions": [],
                    "estimated_cost": Decimal("0"),
                    "tax_impact": None,
                    "expected_allocations": [
                        item.dict() for item in allocation_analysis.current_allocations
                    ],
                    "expected_risk_reduction": None,
                    "expected_return_impact": None,
                    "priority": "low",
                    "recommended_timing": "no_action_needed",
                    "urgency_score": Decimal("0"),
                }

            # Generate rebalancing actions based on drift analysis
            rebalancing_actions = []
            estimated_cost = Decimal("0")

            for drift in allocation_analysis.allocation_drift:
                if drift.requires_rebalancing:
                    # Calculate recommended action
                    if drift.drift_percentage < -5:  # Underweight by more than 5%
                        action_type = "buy"
                        quantity_change = (
                                abs(drift.drift_amount) / 100
                        )  # Simplified calculation
                    elif drift.drift_percentage > 5:  # Overweight by more than 5%
                        action_type = "sell"
                        quantity_change = (
                                abs(drift.drift_amount) / 100
                        )  # Simplified calculation
                    else:
                        action_type = "hold"
                        quantity_change = Decimal("0")

                    # Estimate transaction cost (0.1% of transaction value)
                    transaction_cost = abs(drift.drift_amount) * Decimal("0.001")
                    estimated_cost += transaction_cost

                    rebalancing_action = {
                        "asset_id": drift.asset_id,
                        "asset_symbol": drift.asset_symbol,
                        "action_type": action_type,
                        "current_quantity": Decimal(
                            "0"
                        ),  # Would need to get from portfolio assets
                        "target_quantity": Decimal("0"),  # Would need to calculate
                        "quantity_change": quantity_change,
                        "estimated_cost": transaction_cost,
                        "priority": (
                            "high" if abs(drift.drift_percentage) > 10 else "medium"
                        ),
                    }
                    rebalancing_actions.append(rebalancing_action)

            # Calculate expected allocations after rebalancing
            expected_allocations = []
            for item in allocation_analysis.current_allocations:
                expected_allocation = {
                    "asset_id": item.asset_id,
                    "asset_symbol": item.asset_symbol,
                    "asset_name": item.asset_name,
                    "current_percentage": item.current_percentage,
                    "target_percentage": item.target_percentage
                                         or item.current_percentage,
                    "expected_percentage": item.target_percentage
                                           or item.current_percentage,
                    "current_value": item.current_value,
                    "quantity": item.quantity,
                }
                expected_allocations.append(expected_allocation)

            # Determine priority and urgency
            max_drift = max(
                [
                    abs(drift.drift_percentage)
                    for drift in allocation_analysis.allocation_drift
                ]
            )
            if max_drift > 15:
                priority = "high"
                urgency_score = Decimal("90")
                recommended_timing = "immediate"
            elif max_drift > 10:
                priority = "medium"
                urgency_score = Decimal("60")
                recommended_timing = "within_week"
            else:
                priority = "low"
                urgency_score = Decimal("30")
                recommended_timing = "within_month"

            return {
                "portfolio_id": portfolio_id,
                "recommendation_date": datetime.now(timezone.utc),
                "trigger_reason": f"allocation_drift_exceeds_threshold_{max_drift:.1f}%",
                "current_drift": allocation_analysis.total_drift_percentage,
                "rebalancing_actions": rebalancing_actions,
                "estimated_cost": estimated_cost,
                "tax_impact": estimated_cost
                              * Decimal("0.2"),  # Simplified tax estimate
                "expected_allocations": expected_allocations,
                "expected_risk_reduction": Decimal("5.0"),  # Simplified estimate
                "expected_return_impact": Decimal("0.5"),  # Simplified estimate
                "priority": priority,
                "recommended_timing": recommended_timing,
                "urgency_score": urgency_score,
            }

        except Exception as e:
            logger.error(f"Failed to get rebalancing recommendation: {e}")
            raise

    async def get_or_calculate_asset_correlation(
            self, asset1_id: int, asset2_id: int, force_refresh: bool = False
    ) -> AssetCorrelation:
        """Get asset correlation, auto-refreshing with yfinance if stale."""
        # If force refresh is requested, always calculate new correlation
        if force_refresh:
            logger.info(f"Force refreshing correlation between assets {asset1_id} and {asset2_id}")
            return await self.calculate_asset_correlation(
                asset1_id, asset2_id, datetime.now(timezone.utc)
            )

        # Check for existing fresh correlation first
        existing_correlation = (
            self.db.query(AssetCorrelation)
            .filter(
                AssetCorrelation.asset1_id == asset1_id,
                AssetCorrelation.asset2_id == asset2_id,
            )
            .order_by(AssetCorrelation.calculation_date.desc())
            .first()
        )

        if existing_correlation and self._is_data_fresh(
                existing_correlation.created_at, self.correlation_freshness_days * 24
        ):
            # Return existing fresh data
            return existing_correlation

        # Data is stale - calculate new correlation
        return await self.calculate_asset_correlation(
            asset1_id, asset2_id, datetime.now(timezone.utc)
        )

    async def calculate_asset_correlation(
            self,
            asset1_id: int,
            asset2_id: int,
            calculation_date: Optional[datetime] = None,
    ) -> AssetCorrelation:
        """Calculate correlation between two assets."""
        if calculation_date is None:
            calculation_date = datetime.now(timezone.utc)

        asset1 = self.db.query(Asset).filter(Asset.id == asset1_id).first()
        asset2 = self.db.query(Asset).filter(Asset.id == asset2_id).first()

        if not asset1 or not asset1.symbol:
            raise ValueError(f"Asset with ID {asset1_id} not found or missing symbol")
        if not asset2 or not asset2.symbol:
            raise ValueError(f"Asset with ID {asset2_id} not found or missing symbol")

        # Get historical data for both assets (1 year lookback)
        end_date_str = calculation_date.strftime("%Y-%m-%d")
        start_date_str = (calculation_date - timedelta(days=365)).strftime("%Y-%m-%d")

        # Fetch price data for both assets
        price_data1 = await market_data_service.fetch_ticker_data(
            symbol=asset1.symbol,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d",
        )

        price_data2 = await market_data_service.fetch_ticker_data(
            symbol=asset2.symbol,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d",
        )

        if (
                price_data1 is None
                or price_data2 is None
                or len(price_data1) < 30
                or len(price_data2) < 30
        ):
            raise ValueError("Insufficient price data for correlation calculations")

        # Calculate correlations for different time periods
        correlation_metrics = self._calculate_correlations(price_data1, price_data2)

        # Create and save correlation record
        correlation = AssetCorrelation(
            asset1_id=asset1_id,
            asset2_id=asset2_id,
            calculation_date=calculation_date,
            **correlation_metrics,
        )

        self.db.add(correlation)
        self.db.commit()
        self.db.refresh(correlation)

        return correlation

    def _calculate_correlations(
            self, price_data1: pd.DataFrame, price_data2: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate correlation metrics between two price series."""
        metrics = {}

        try:
            # Align data by dates
            merged_data = pd.merge(
                price_data1[["Close"]].rename(columns={"Close": "asset1_close"}),
                price_data2[["Close"]].rename(columns={"Close": "asset2_close"}),
                left_index=True,
                right_index=True,
                how="inner",
            )

            if len(merged_data) < 30:
                raise ValueError("Insufficient overlapping data points")

            # Calculate returns
            returns1 = merged_data["asset1_close"].pct_change().dropna()
            returns2 = merged_data["asset2_close"].pct_change().dropna()

            # Overall correlation
            if len(returns1) >= 252:  # 1 year
                correlation_1y = returns1.corr(returns2)
                metrics["correlation_1y"] = Decimal(str(correlation_1y))

            # 6-month correlation
            if len(returns1) >= 126:
                correlation_6m = returns1.tail(126).corr(returns2.tail(126))
                metrics["correlation_6m"] = Decimal(str(correlation_6m))

            # 3-month correlation
            if len(returns1) >= 63:
                correlation_3m = returns1.tail(63).corr(returns2.tail(63))
                metrics["correlation_3m"] = Decimal(str(correlation_3m))

            # 1-month correlation
            if len(returns1) >= 21:
                correlation_1m = returns1.tail(21).corr(returns2.tail(21))
                metrics["correlation_1m"] = Decimal(str(correlation_1m))

            # Rolling correlations
            if len(returns1) >= 60:
                rolling_60d = (
                    returns1.rolling(window=60)
                    .corr(returns2.rolling(window=60))
                    .iloc[-1]
                )
                metrics["rolling_correlation_60d"] = Decimal(str(rolling_60d))

            if len(returns1) >= 20:
                rolling_20d = (
                    returns1.rolling(window=20)
                    .corr(returns2.rolling(window=20))
                    .iloc[-1]
                )
                metrics["rolling_correlation_20d"] = Decimal(str(rolling_20d))

            # Statistical significance (simplified)
            if len(returns1) >= 30:
                correlation = returns1.corr(returns2)
                # Simple p-value approximation (for proper stats, use scipy.stats)
                t_stat = correlation * math.sqrt(
                    (len(returns1) - 2) / (1 - correlation ** 2)
                )
                # Simplified p-value calculation
                p_value = 2 * (1 - abs(t_stat) / 2)  # Rough approximation
                metrics["p_value"] = Decimal(str(max(0, min(1, p_value))))
                metrics["is_significant"] = p_value < 0.05

        except Exception as e:
            logger.error(f"Error calculating correlations: {e}")
            # Return empty metrics if calculation fails
            pass

        return metrics

    async def get_user_assets_for_analytics(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all assets belonging to a user for analytics purposes."""
        user_assets = (
            self.db.query(Asset)
            .filter(Asset.user_id == user_id, Asset.is_active == True)
            .all()
        )

        assets_data = []
        for asset in user_assets:
            # Check if asset has any performance metrics
            latest_metrics = (
                self.db.query(AssetPerformanceMetrics)
                .filter(AssetPerformanceMetrics.asset_id == asset.id)
                .order_by(AssetPerformanceMetrics.calculation_date.desc())
                .first()
            )

            # Check if asset is used in any portfolios
            portfolio_usage = (
                self.db.query(PortfolioAsset)
                .filter(PortfolioAsset.asset_id == asset.id)
                .count()
            )

            assets_data.append(
                {
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "currency": asset.currency,
                    "sector": asset.sector,
                    "industry": asset.industry,
                    "has_metrics": latest_metrics is not None,
                    "last_metrics_date": (
                        latest_metrics.calculation_date if latest_metrics else None
                    ),
                    "portfolio_usage_count": portfolio_usage,
                    "created_at": asset.created_at,
                }
            )

        return assets_data

    async def get_analytics_dashboard_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive analytics dashboard summary for a user."""
        try:
            # Get user's portfolios
            user_portfolios = (
                self.db.query(Portfolio)
                .filter(Portfolio.user_id == user_id, Portfolio.is_active == True)
                .all()
            )

            # Get user's assets
            user_assets = await self.get_user_assets_for_analytics(user_id)

            # Portfolio summaries
            portfolio_summaries = []
            for portfolio in user_portfolios:
                try:
                    summary = await self.get_portfolio_analytics_summary(portfolio.id)
                    portfolio_summaries.append(summary)
                except Exception as e:
                    logger.warning(
                        f"Failed to get summary for portfolio {portfolio.id}: {e}"
                    )

            # Asset performance summary
            assets_with_recent_metrics = sum(
                1
                for asset in user_assets
                if asset["has_metrics"]
                and asset["last_metrics_date"]
                and (datetime.now(timezone.utc) - asset["last_metrics_date"]).days <= 7
            )

            # Recent correlations
            recent_correlations = (
                self.db.query(AssetCorrelation)
                .join(Asset, Asset.id == AssetCorrelation.asset1_id)
                .filter(
                    Asset.user_id == user_id,
                    AssetCorrelation.calculation_date
                    >= datetime.now(timezone.utc) - timedelta(days=30),
                )
                .count()
            )

            return {
                "user_id": user_id,
                "summary_date": datetime.now(timezone.utc),
                "portfolios": {
                    "total_count": len(user_portfolios),
                    "summaries": portfolio_summaries,
                    "total_value": sum(
                        float(p.get("total_value", 0)) for p in portfolio_summaries
                    ),
                    "total_unrealized_pnl": sum(
                        float(p.get("total_unrealized_pnl", 0))
                        for p in portfolio_summaries
                    ),
                },
                "assets": {
                    "total_count": len(user_assets),
                    "assets_with_metrics": assets_with_recent_metrics,
                    "assets_in_portfolios": sum(
                        1 for asset in user_assets if asset["portfolio_usage_count"] > 0
                    ),
                    "standalone_assets": sum(
                        1
                        for asset in user_assets
                        if asset["portfolio_usage_count"] == 0
                    ),
                },
                "analytics": {
                    "recent_correlations": recent_correlations,
                    "performance_snapshots_last_week": (
                        self.db.query(PortfolioPerformanceHistory)
                        .join(
                            Portfolio,
                            Portfolio.id == PortfolioPerformanceHistory.portfolio_id,
                        )
                        .filter(
                            Portfolio.user_id == user_id,
                            PortfolioPerformanceHistory.snapshot_date
                            >= datetime.now(timezone.utc) - timedelta(days=7),
                        )
                        .count()
                    ),
                    "risk_calculations_last_week": (
                        self.db.query(PortfolioRiskMetrics)
                        .join(
                            Portfolio, Portfolio.id == PortfolioRiskMetrics.portfolio_id
                        )
                        .filter(
                            Portfolio.user_id == user_id,
                            PortfolioRiskMetrics.calculation_date
                            >= datetime.now(timezone.utc) - timedelta(days=7),
                        )
                        .count()
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get analytics dashboard summary: {e}")
            raise

    async def force_refresh_all_portfolio_data(self, portfolio_id: int) -> Dict[str, Any]:
        """Force refresh all portfolio data from yfinance and update database."""
        try:
            # Get portfolio assets
            portfolio_assets = (
                self.db.query(PortfolioAsset)
                .filter(PortfolioAsset.portfolio_id == portfolio_id)
                .all()
            )

            if not portfolio_assets:
                raise ValueError("Portfolio has no assets")

            updated_data = {
                "portfolio_id": portfolio_id,
                "refresh_timestamp": datetime.now(timezone.utc),
                "assets_refreshed": 0,
                "errors": [],
                "performance_snapshot": None,
                "risk_metrics": None,
                "asset_metrics": []
            }

            # Refresh asset metrics for all portfolio assets
            for portfolio_asset in portfolio_assets:
                if portfolio_asset.asset and portfolio_asset.asset.symbol:
                    try:
                        asset_metrics = await self.calculate_asset_metrics(
                            portfolio_asset.asset.id, datetime.now(timezone.utc)
                        )
                        updated_data["asset_metrics"].append({
                            "asset_id": portfolio_asset.asset.id,
                            "symbol": portfolio_asset.asset.symbol,
                            "current_price": float(
                                asset_metrics.current_price) if asset_metrics.current_price else None,
                            "price_change_percent": float(
                                asset_metrics.price_change_percent) if asset_metrics.price_change_percent else None,
                            "volatility_20d": float(
                                asset_metrics.volatility_20d) if asset_metrics.volatility_20d else None,
                            "refreshed": True
                        })
                        updated_data["assets_refreshed"] += 1
                    except Exception as e:
                        updated_data["errors"].append(f"Asset {portfolio_asset.asset.symbol}: {str(e)}")

            # Refresh portfolio performance snapshot
            try:
                performance_snapshot = await self.create_performance_snapshot(
                    portfolio_id, datetime.now(timezone.utc)
                )
                updated_data["performance_snapshot"] = {
                    "total_value": float(performance_snapshot.total_value) if performance_snapshot.total_value else 0,
                    "total_unrealized_pnl": float(
                        performance_snapshot.total_unrealized_pnl) if performance_snapshot.total_unrealized_pnl else 0,
                    "total_unrealized_pnl_percent": float(
                        performance_snapshot.total_unrealized_pnl_percent) if performance_snapshot.total_unrealized_pnl_percent else 0,
                    "snapshot_date": performance_snapshot.snapshot_date
                }
            except Exception as e:
                updated_data["errors"].append(f"Performance snapshot: {str(e)}")

            # Refresh portfolio risk metrics
            try:
                risk_metrics = await self.calculate_portfolio_risk_metrics(
                    portfolio_id, datetime.now(timezone.utc)
                )
                updated_data["risk_metrics"] = {
                    "risk_level": risk_metrics.risk_level,
                    "portfolio_volatility": float(
                        risk_metrics.portfolio_volatility) if risk_metrics.portfolio_volatility else None,
                    "var_95": float(risk_metrics.var_95) if risk_metrics.var_95 else None,
                    "var_99": float(risk_metrics.var_99) if risk_metrics.var_99 else None,
                    "calculation_date": risk_metrics.calculation_date
                }
            except Exception as e:
                updated_data["errors"].append(f"Risk metrics: {str(e)}")

            return updated_data

        except Exception as e:
            logger.error(f"Failed to force refresh portfolio data: {e}")
            raise

    async def bulk_update_asset_prices(self, asset_ids: List[int]) -> Dict[str, Any]:
        """Bulk update current prices for multiple assets using yfinance."""
        try:
            # Get assets
            assets = (
                self.db.query(Asset)
                .filter(Asset.id.in_(asset_ids), Asset.is_active == True)
                .all()
            )

            if not assets:
                raise ValueError("No assets found")

            # Get symbols
            symbols = [asset.symbol for asset in assets if asset.symbol]

            if not symbols:
                raise ValueError("No symbols found for assets")

            # Bulk fetch current prices
            current_prices = await market_data_service.get_multiple_current_prices(symbols)

            updated_data = {
                "update_timestamp": datetime.now(timezone.utc),
                "assets_updated": 0,
                "price_updates": [],
                "errors": []
            }

            # Update asset records with current prices
            for asset in assets:
                if asset.symbol and asset.symbol in current_prices:
                    current_price = current_prices[asset.symbol]
                    if current_price:
                        try:
                            # Update asset performance metrics with new price
                            await self.calculate_asset_metrics(asset.id, datetime.now(timezone.utc))

                            updated_data["price_updates"].append({
                                "asset_id": asset.id,
                                "symbol": asset.symbol,
                                "current_price": current_price,
                                "updated": True
                            })
                            updated_data["assets_updated"] += 1
                        except Exception as e:
                            updated_data["errors"].append(f"Asset {asset.symbol}: {str(e)}")
                    else:
                        updated_data["errors"].append(f"No price data for {asset.symbol}")

            return updated_data

        except Exception as e:
            logger.error(f"Failed to bulk update asset prices: {e}")
            raise

    async def generate_historical_performance_snapshots(
            self, portfolio_id: int, start_date: datetime, end_date: datetime
    ) -> List[PortfolioPerformanceHistory]:
        """
        Generate historical performance snapshots for a portfolio using yfinance data.
        This method is transaction-aware and reconstructs portfolio holdings for each day.
        """
        try:
            # Normalize start and end dates to midnight. This is the key fix.
            # It ensures the entire function operates on a consistent, date-level basis,
            # preventing multiple snapshots for the same calendar day.
            start_date = datetime.combine(start_date.date(), datetime.min.time())
            end_date = datetime.combine(end_date.date(), datetime.min.time())

            logger.info(
                f"Generating transaction-aware historical snapshots for portfolio {portfolio_id} from {start_date.date()} to {end_date.date()}")

            # 1. DELETE EXISTING SNAPSHOTS in the date range to avoid duplicates.
            (
                self.db.query(PortfolioPerformanceHistory)
                .filter(
                    PortfolioPerformanceHistory.portfolio_id == portfolio_id,
                    PortfolioPerformanceHistory.snapshot_date >= start_date,
                    PortfolioPerformanceHistory.snapshot_date <= end_date,
                )
                .delete(synchronize_session=False)
            )

            # 2. FETCH ALL TRANSACTIONS up to the end of the period.
            transactions = (
                self.db.query(Transaction)
                .filter(
                    Transaction.portfolio_id == portfolio_id,
                    Transaction.transaction_date <= end_date,
                )
                .order_by(Transaction.transaction_date)
                .all()
            )

            if not transactions:
                logger.warning(f"No transactions found for portfolio {portfolio_id}. Cannot generate history.")
                self.db.commit()
                return []

            # 3. FETCH ALL REQUIRED HISTORICAL PRICE DATA in a single batch.
            asset_ids = list({tx.asset_id for tx in transactions})
            assets = self.db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
            asset_map = {asset.id: asset for asset in assets}

            asset_price_data = {}
            for asset_id in asset_ids:
                asset = asset_map.get(asset_id)
                if asset and asset.symbol:
                    try:
                        # Fetch data from one day before start_date to handle initial state correctly
                        fetch_start_date = start_date - timedelta(days=1)
                        price_data = await market_data_service.fetch_ticker_data(
                            symbol=asset.symbol,
                            start_date=fetch_start_date.strftime("%Y-%m-%d"),
                            end_date=end_date.strftime("%Y-%m-%d"),
                            interval="1d",
                        )
                        if price_data is not None and not price_data.empty:
                            asset_price_data[asset_id] = price_data
                    except Exception as e:
                        logger.warning(f"Failed to fetch price data for {asset.symbol}: {e}")

            # 4. PRE-PROCESS TRANSACTIONS by grouping them by date.
            transactions_by_date = {}
            for tx in transactions:
                tx_date = tx.transaction_date.date()
                if tx_date not in transactions_by_date:
                    transactions_by_date[tx_date] = []
                transactions_by_date[tx_date].append(tx)

            # 5. CALCULATE INITIAL HOLDINGS state before the start_date.
            current_holdings = {}
            for tx in transactions:
                if tx.transaction_date.date() < start_date.date():
                    asset_id = tx.asset_id
                    if asset_id not in current_holdings:
                        current_holdings[asset_id] = {'quantity': Decimal(0), 'cost_basis': Decimal(0)}

                    if tx.transaction_type == TransactionType.BUY:
                        current_holdings[asset_id]['quantity'] += tx.quantity
                        current_holdings[asset_id]['cost_basis'] += tx.quantity * tx.price
                    elif tx.transaction_type == TransactionType.SELL:
                        if current_holdings[asset_id]['quantity'] > 0:
                            # Prevent division by zero if quantity is exactly zero before subtraction
                            avg_cost = current_holdings[asset_id]['cost_basis'] / current_holdings[asset_id]['quantity']
                            cost_basis_reduction = tx.quantity * avg_cost
                            current_holdings[asset_id]['cost_basis'] -= cost_basis_reduction
                            current_holdings[asset_id]['quantity'] -= tx.quantity

            # 6. MAIN LOOP to generate a snapshot for each day.
            snapshots = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.date()

                # A. Update holdings with any transactions that occurred on the current day.
                if date_key in transactions_by_date:
                    for tx in transactions_by_date[date_key]:
                        asset_id = tx.asset_id
                        if asset_id not in current_holdings:
                            current_holdings[asset_id] = {'quantity': Decimal(0), 'cost_basis': Decimal(0)}

                        if tx.transaction_type == TransactionType.BUY:
                            current_holdings[asset_id]['quantity'] += tx.quantity
                            current_holdings[asset_id]['cost_basis'] += tx.quantity * tx.price
                        elif tx.transaction_type == TransactionType.SELL:
                            if current_holdings[asset_id]['quantity'] > 0:
                                avg_cost = current_holdings[asset_id]['cost_basis'] / current_holdings[asset_id][
                                    'quantity']
                                cost_basis_reduction = tx.quantity * avg_cost
                                current_holdings[asset_id]['cost_basis'] -= cost_basis_reduction
                                current_holdings[asset_id]['quantity'] -= tx.quantity

                # B. Calculate total value and cost basis for the current day.
                total_value = Decimal(0)
                total_cost_basis = Decimal(0)

                for asset_id, holding in list(current_holdings.items()):
                    quantity = holding['quantity']

                    if quantity <= 0:
                        del current_holdings[asset_id]
                        continue

                    total_cost_basis += holding['cost_basis']

                    price_data = asset_price_data.get(asset_id)
                    if price_data is not None:
                        # Find the most recent price on or before the current snapshot date
                        prev_rows = price_data[price_data['Date'].dt.date <= date_key]
                        if not prev_rows.empty:
                            close_price = Decimal(str(prev_rows.iloc[-1]['Close']))
                            asset_value = close_price * quantity
                        else:
                            # Fallback if no price data is found before this date (e.g., weekends/holidays)
                            asset_value = holding['cost_basis']
                    else:
                        # Fallback if price data for the asset couldn't be fetched
                        asset_value = holding['cost_basis']

                    total_value += asset_value

                # C. ALWAYS create a snapshot, even if values are zero.
                total_unrealized_pnl = total_value - total_cost_basis
                total_unrealized_pnl_percent = (
                    (total_unrealized_pnl / total_cost_basis * 100)
                    if total_cost_basis > 0
                    else Decimal(0)
                )

                snapshot = PortfolioPerformanceHistory(
                    portfolio_id=portfolio_id,
                    snapshot_date=current_date,  # current_date is now always at midnight
                    total_value=total_value,
                    total_cost_basis=total_cost_basis,
                    total_unrealized_pnl=total_unrealized_pnl,
                    total_unrealized_pnl_percent=total_unrealized_pnl_percent,
                )

                self.db.add(snapshot)
                snapshots.append(snapshot)

                current_date += timedelta(days=1)

            # 7. COMMIT all changes to the database.
            self.db.commit()
            for snapshot in snapshots:
                self.db.refresh(snapshot)

            logger.info(f"Generated {len(snapshots)} new historical snapshots for portfolio {portfolio_id}")
            return snapshots

        except Exception as e:
            logger.error(f"Failed to generate historical performance snapshots: {e}")
            self.db.rollback()
            raise
