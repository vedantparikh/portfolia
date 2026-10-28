"""
Portfolio Analytics Service
Comprehensive service for portfolio analysis, risk management, and performance tracking.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
)
from core.database.models.portfolio_analytics import (
    PortfolioAllocation,
    PortfolioPerformanceHistory,
)
from core.domain.returns import (
    compute_daily_returns,
    period_summary,
    split_period,
    value_at_risk_pct,
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
from modules.analytics.calculations import PortfolioCalculationService
from modules.portfolios.service import PortfolioService

logger = logging.getLogger(__name__)


def _decimal(value: Optional[float]) -> Optional[Decimal]:
    return None if value is None else Decimal(str(round(value, 8)))


def _totals_by_currency(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Portfolios in different currencies are never added together."""
    totals: Dict[str, Dict[str, float]] = {}
    for summary in summaries:
        bucket = totals.setdefault(
            summary["currency"], {"total_value": 0.0, "total_unrealized_pnl": 0.0}
        )
        bucket["total_value"] += float(summary["total_value"])
        bucket["total_unrealized_pnl"] += float(summary["total_unrealized_pnl"])
    return [
        {"currency": currency, **values} for currency, values in sorted(totals.items())
    ]


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

    async def engine_metrics(
        self, portfolio_id: int, as_of: datetime
    ) -> Dict[str, Any]:
        """Value and FIFO cost at the last close, and one-year metrics, from the engine."""
        calculations = PortfolioCalculationService(self.db)
        transactions = calculations.get_transactions(portfolio_id, None, as_of)
        if not transactions:
            raise DomainError("Portfolio has no transactions")
        series = await calculations.get_portfolio_series(transactions, as_of)
        last = series.iloc[-1]
        value = float(last["value"])
        cost = float(last["cost_basis"])
        start = (as_of - timedelta(days=365)).date()
        year = period_summary(series, start)
        window, opening_value, _ = split_period(series, start)
        returns = compute_daily_returns(window, opening_value)
        daily = returns.dropna()
        return {
            "total_value": value,
            "total_cost_basis": cost,
            "total_unrealized_pnl": value - cost,
            "total_unrealized_pnl_percent": (value - cost) / cost * 100
            if cost
            else 0.0,
            "daily_return": float(daily.iloc[-1] * 100) if not daily.empty else None,
            "cumulative_return": year.get("twr_pct"),
            "annualized_return": year.get("twr_annualized_pct"),
            "volatility": year.get("volatility_pct"),
            "sharpe_ratio": year.get("sharpe_ratio"),
            "max_drawdown": year.get("max_drawdown_pct"),
            "var_95": value_at_risk_pct(returns, 0.95),
            "var_99": value_at_risk_pct(returns, 0.99),
        }

    async def create_performance_snapshot(
        self, portfolio_id: int, snapshot_date: Optional[datetime] = None
    ) -> PerformanceSnapshotResponse:
        """Store today's engine numbers for a portfolio (the worker is the caller)."""
        if snapshot_date is None:
            snapshot_date = datetime.now(timezone.utc)
        metrics = await self.engine_metrics(portfolio_id, snapshot_date)
        snapshot = PortfolioPerformanceHistory(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            **{key: _decimal(value) for key, value in metrics.items()},
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
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
        """Engine numbers for one portfolio: value at the last close and one-year returns."""
        now = datetime.now(timezone.utc)
        metrics = await self.engine_metrics(portfolio_id, now)
        portfolio = (
            self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        )
        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name if portfolio else "Unknown",
            "currency": getattr(portfolio, "currency", None) or "USD",
            "calculation_date": now,
            "total_value": _decimal(metrics["total_value"]),
            "total_cost_basis": _decimal(metrics["total_cost_basis"]),
            "total_unrealized_pnl": _decimal(metrics["total_unrealized_pnl"]),
            "total_unrealized_pnl_percent": _decimal(
                metrics["total_unrealized_pnl_percent"]
            ),
            "total_return": _decimal(metrics["cumulative_return"]),
            "annualized_return": _decimal(metrics["annualized_return"]),
        }

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
                    "totals": _totals_by_currency(portfolio_summaries),
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
