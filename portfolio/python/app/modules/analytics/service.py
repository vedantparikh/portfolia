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

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
)
from core.database.models.portfolio_analytics import (
    PortfolioAllocation,
    PortfolioPerformanceHistory,
)
from core.errors import DomainError
from core.schemas.portfolio_analytics import (
    AllocationAnalysisResponse,
    AllocationDrift,
    AllocationItem,
    PerformanceSnapshotResponse,
    PortfolioAllocationCreate,
)
from core.services.market_data_service import market_data_service
from modules.portfolios.service import PortfolioService

logger = logging.getLogger(__name__)


class PortfolioAnalyticsService:
    """Service for comprehensive portfolio analytics and risk management."""

    def __init__(self, db: Session):
        self.db = db

    # Portfolio Performance History
    def latest_performance_snapshot(
        self, portfolio_id: int
    ) -> Optional[PerformanceSnapshotResponse]:
        """The newest stored snapshot. The worker is the only writer."""
        existing_snapshot = (
            self.db.query(PortfolioPerformanceHistory)
            .filter(PortfolioPerformanceHistory.portfolio_id == portfolio_id)
            .order_by(PortfolioPerformanceHistory.snapshot_date.desc())
            .first()
        )
        if existing_snapshot is None:
            return None
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
            raise DomainError("Portfolio has no assets")

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
        daily_returns = await self._get_historical_portfolio_values(
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
        daily_volatility = daily_returns.ffill().pct_change().std()
        annualized_volatility = daily_volatility * math.sqrt(252)
        metrics["volatility"] = Decimal(str(annualized_volatility))

        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        metrics["sharpe_ratio"] = Decimal(str(sharpe_ratio))

        # Maximum drawdown
        cumulative_returns = (1 + daily_returns.ffill().pct_change()).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        metrics["max_drawdown"] = Decimal(str(max_drawdown))

        # Value at Risk (95% and 99%)
        returns = daily_returns.ffill().pct_change().dropna()
        var_95 = returns.quantile(0.05)
        var_99 = returns.quantile(0.01)
        metrics["var_95"] = Decimal(str(var_95))
        metrics["var_99"] = Decimal(str(var_99))

        return metrics

    async def _get_historical_portfolio_values(
        self, portfolio_id: int, start_date: datetime, end_date: datetime
    ) -> pd.Series:
        """
        Retrieves the transaction-aware historical total values for a portfolio
        from the database.
        """
        logger.info(
            f"Fetching historical values for portfolio {portfolio_id} from {start_date.date()} to {end_date.date()}"
        )

        # Query the database for the pre-calculated, correct historical snapshots
        history_records = (
            self.db.query(
                PortfolioPerformanceHistory.snapshot_date,
                PortfolioPerformanceHistory.total_value,
            )
            .filter(
                PortfolioPerformanceHistory.portfolio_id == portfolio_id,
                PortfolioPerformanceHistory.snapshot_date >= start_date,
                PortfolioPerformanceHistory.snapshot_date <= end_date,
            )
            .order_by(PortfolioPerformanceHistory.snapshot_date)
            .all()
        )

        if not history_records:
            logger.warning(
                f"No historical performance records found for portfolio {portfolio_id} in the given date range."
            )
            return pd.Series(dtype=float)

        # Convert the records to a pandas Series, which is the required format for calculations
        dates = [record.snapshot_date for record in history_records]
        values = [float(record.total_value) for record in history_records]

        return pd.Series(values, index=pd.to_datetime(dates))

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
            returns = price_data["Close"].ffill().pct_change().dropna()

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
        """
        Current weights from live holdings, and drift against the active targets.
        Positions without a live price are left out rather than valued at cost.
        """
        holdings = [
            h
            for h in await PortfolioService(self.db).get_portfolio_holdings(
                portfolio_id
            )
            if h.quantity > 0 and h.current_value is not None
        ]
        targets = {
            t.asset_id: t
            for t in self.db.query(PortfolioAllocation)
            .filter(
                PortfolioAllocation.portfolio_id == portfolio_id,
                PortfolioAllocation.is_active == True,
            )
            .all()
        }
        if not holdings and not targets:
            raise DomainError("Portfolio has no assets")

        total_value = sum((Decimal(str(h.current_value)) for h in holdings), Decimal(0))
        by_asset = {h.asset_id: h for h in holdings}
        names = {
            a.id: a
            for a in self.db.query(Asset)
            .filter(Asset.id.in_(set(by_asset) | set(targets)))
            .all()
        }

        allocation_items = []
        allocation_drifts = []
        total_drift = Decimal("0")
        rebalancing_needed = False
        for asset_id in list(by_asset) + [a for a in targets if a not in by_asset]:
            holding = by_asset.get(asset_id)
            asset = names.get(asset_id)
            value = Decimal(str(holding.current_value)) if holding else Decimal(0)
            current_percentage = (
                value / total_value * 100 if total_value > 0 else Decimal(0)
            )
            target = targets.get(asset_id)
            target_percentage = target.target_percentage if target else None
            symbol = asset.symbol if asset else "Unknown"

            allocation_items.append(
                AllocationItem(
                    asset_id=asset_id,
                    asset_symbol=symbol,
                    asset_name=asset.name if asset else None,
                    current_percentage=current_percentage,
                    target_percentage=target_percentage,
                    current_value=value,
                    quantity=Decimal(str(holding.quantity)) if holding else Decimal(0),
                )
            )
            if target_percentage is None:
                continue

            drift_percentage = current_percentage - target_percentage
            threshold = target.rebalance_threshold or Decimal("5")
            requires_rebalancing = abs(drift_percentage) > threshold
            rebalancing_needed = rebalancing_needed or requires_rebalancing
            total_drift += abs(drift_percentage)
            allocation_drifts.append(
                AllocationDrift(
                    asset_id=asset_id,
                    asset_symbol=symbol,
                    current_percentage=current_percentage,
                    target_percentage=target_percentage,
                    drift_percentage=drift_percentage,
                    drift_amount=total_value * drift_percentage / 100,
                    requires_rebalancing=requires_rebalancing,
                    recommended_action="buy"
                    if drift_percentage < 0
                    else "sell"
                    if drift_percentage > 0
                    else "hold",
                )
            )

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

    def _calculate_risk_metrics(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate risk metrics for an asset."""
        metrics = {}

        # Volatility calculations
        returns = price_data["close"].ffill().pct_change().dropna()
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
                raise DomainError("Portfolio has no assets")

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

            # Whole-portfolio value is unchanged by rebalancing, so each action is
            # the drift amount converted to shares at the current price
            quantities = {
                item.asset_id: item.quantity or Decimal(0)
                for item in allocation_analysis.current_allocations
            }
            values = {
                item.asset_id: item.current_value
                for item in allocation_analysis.current_allocations
            }
            rebalancing_actions = []
            estimated_cost = Decimal("0")
            for drift in allocation_analysis.allocation_drift:
                if not drift.requires_rebalancing:
                    continue
                quantity = quantities.get(drift.asset_id, Decimal(0))
                if quantity > 0:
                    price = values[drift.asset_id] / quantity
                else:
                    live = await market_data_service.get_current_price(
                        drift.asset_symbol
                    )
                    price = Decimal(str(live)) if live else None
                if not price:
                    continue
                shares = (abs(drift.drift_amount) / price).quantize(Decimal("0.0001"))
                action_type = "sell" if drift.drift_percentage > 0 else "buy"
                # Commission assumption: 0.1% of the traded value
                transaction_cost = abs(drift.drift_amount) * Decimal("0.001")
                estimated_cost += transaction_cost
                rebalancing_actions.append(
                    {
                        "asset_id": drift.asset_id,
                        "asset_symbol": drift.asset_symbol,
                        "action_type": action_type,
                        "current_quantity": quantity,
                        "target_quantity": quantity - shares
                        if action_type == "sell"
                        else quantity + shares,
                        "quantity_change": shares,
                        "trade_value": abs(drift.drift_amount),
                        "price": price,
                        "estimated_cost": transaction_cost,
                        "priority": (
                            "high" if abs(drift.drift_percentage) > 10 else "medium"
                        ),
                    }
                )
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
                "tax_impact": None,
                "expected_allocations": expected_allocations,
                "expected_risk_reduction": None,
                "expected_return_impact": None,
                "priority": priority,
                "recommended_timing": recommended_timing,
                "urgency_score": urgency_score,
            }

        except Exception as e:
            logger.error(f"Failed to get rebalancing recommendation: {e}")
            raise

    async def get_analytics_dashboard_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive analytics dashboard summary for a user."""
        try:
            # Get user's portfolios
            user_portfolios = (
                self.db.query(Portfolio)
                .filter(Portfolio.user_id == user_id, Portfolio.is_active == True)
                .all()
            )

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
                "analytics": {
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
                },
            }

        except Exception as e:
            logger.error(f"Failed to get analytics dashboard summary: {e}")
            raise
