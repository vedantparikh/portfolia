"""
Portfolio Dashboard Service
Comprehensive service for portfolio dashboard data aggregation and presentation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.core.database.models import Asset, Portfolio, PortfolioAsset, Transaction
from app.core.database.models.portfolio_analytics import (
    PortfolioPerformanceHistory,
    PortfolioRiskMetrics,
)
from app.core.schemas.portfolio import PortfolioHolding
from app.core.services.portfolio_service import PortfolioService


class PortfolioDashboardService:
    """Service for portfolio dashboard data aggregation."""

    def __init__(self, db: Session):
        self.db = db

    async def get_dashboard_overview(self, portfolio_id: int, user_id: int) -> Dict[str, Any]:
        """Get comprehensive dashboard overview for a portfolio."""
        # Get portfolio basic info
        portfolio = (
            self.db.query(Portfolio)
            .filter(
                and_(
                    Portfolio.id == portfolio_id,
                    Portfolio.user_id == user_id,
                    Portfolio.is_active == True,
                )
            )
            .first()
        )

        if not portfolio:
            raise ValueError("Portfolio not found")

        # Get current holdings
        holdings = await self._get_portfolio_holdings(portfolio_id)
        
        # Calculate basic metrics
        total_value = sum(float(h.current_value or h.cost_basis_total) for h in holdings)
        total_cost_basis = sum(float(h.cost_basis_total) for h in holdings)
        total_pnl = total_value - total_cost_basis
        total_pnl_percent = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0

        # Get performance metrics
        performance_metrics = self._get_performance_metrics(portfolio_id)
        
        # Get risk metrics
        risk_metrics = self._get_risk_metrics(portfolio_id)
        
        # Get allocation breakdown
        allocation_breakdown = self._get_allocation_breakdown(holdings, total_value)
        
        # Get recent activity
        recent_activity = self._get_recent_activity(portfolio_id, limit=10)

        return {
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "currency": portfolio.currency,
                "created_at": portfolio.created_at,
                "last_updated": portfolio.updated_at,
            },
            "overview": {
                "total_value": round(total_value, 2),
                "total_cost_basis": round(total_cost_basis, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_percent": round(total_pnl_percent, 2),
                "asset_count": len(holdings),
                "last_updated": datetime.now(timezone.utc),
            },
            "performance": performance_metrics,
            "risk": risk_metrics,
            "allocation": allocation_breakdown,
            "holdings": holdings,
            "recent_activity": recent_activity,
        }

    async def _get_portfolio_holdings(self, portfolio_id: int) -> List[PortfolioHolding]:
        """Get detailed portfolio holdings."""
        holdings_data = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        holdings = []
        for portfolio_asset, asset in holdings_data:
            # Update P&L if needed
            if portfolio_asset.current_value is None:
                await self._update_asset_pnl(portfolio_asset)

            holding = PortfolioHolding(
                asset_id=asset.id,
                symbol=asset.symbol,
                name=asset.name,
                quantity=float(portfolio_asset.quantity),
                cost_basis=float(portfolio_asset.cost_basis),
                cost_basis_total=float(portfolio_asset.cost_basis_total),
                current_value=(
                    float(portfolio_asset.current_value)
                    if portfolio_asset.current_value
                    else None
                ),
                today_pnl=float(portfolio_asset.current_value),
                today_pnl_percent=float(portfolio_asset.current_value),
                unrealized_pnl=(
                    float(portfolio_asset.unrealized_pnl)
                    if portfolio_asset.unrealized_pnl
                    else None
                ),
                unrealized_pnl_percent=(
                    float(portfolio_asset.unrealized_pnl_percent)
                    if portfolio_asset.unrealized_pnl_percent
                    else None
                ),
                last_updated=portfolio_asset.last_updated,
            )
            holdings.append(holding)

        return holdings

    def _get_performance_metrics(self, portfolio_id: int) -> Dict[str, Any]:
        """Get portfolio performance metrics."""
        # Get latest performance snapshot
        latest_snapshot = (
            self.db.query(PortfolioPerformanceHistory)
            .filter(PortfolioPerformanceHistory.portfolio_id == portfolio_id)
            .order_by(desc(PortfolioPerformanceHistory.snapshot_date))
            .first()
        )

        if not latest_snapshot:
            return {}

        return {
            "total_return": float(latest_snapshot.cumulative_return or 0),
            "annualized_return": float(latest_snapshot.annualized_return or 0),
            "volatility": float(latest_snapshot.volatility or 0),
            "sharpe_ratio": float(latest_snapshot.sharpe_ratio or 0),
            "max_drawdown": float(latest_snapshot.max_drawdown or 0),
            "var_95": float(latest_snapshot.var_95 or 0),
            "beta": float(latest_snapshot.beta or 0),
            "alpha": float(latest_snapshot.alpha or 0),
        }

    def _get_risk_metrics(self, portfolio_id: int) -> Dict[str, Any]:
        """Get portfolio risk metrics."""
        latest_risk = (
            self.db.query(PortfolioRiskMetrics)
            .filter(PortfolioRiskMetrics.portfolio_id == portfolio_id)
            .order_by(desc(PortfolioRiskMetrics.calculation_date))
            .first()
        )

        if not latest_risk:
            return {}

        return {
            "risk_level": latest_risk.risk_level.value if latest_risk.risk_level else None,
            "risk_score": float(latest_risk.risk_score or 0),
            "portfolio_volatility": float(latest_risk.portfolio_volatility or 0),
            "concentration_risk": float(latest_risk.concentration_risk or 0),
            "effective_assets": float(latest_risk.effective_number_of_assets or 0),
            "max_drawdown": float(latest_risk.max_drawdown or 0),
            "var_95_1d": float(latest_risk.var_95_1d or 0),
            "var_99_1d": float(latest_risk.var_99_1d or 0),
        }

    def _get_allocation_breakdown(self, holdings: List[PortfolioHolding], total_value: float) -> Dict[str, Any]:
        """Get portfolio allocation breakdown by asset type and sector."""
        if total_value == 0:
            return {"by_type": {}, "by_sector": {}, "by_asset": []}

        # Get asset details for holdings
        asset_ids = [h.asset_id for h in holdings]
        assets = (
            self.db.query(Asset)
            .filter(Asset.id.in_(asset_ids))
            .all()
        )
        asset_map = {asset.id: asset for asset in assets}

        # Calculate allocations
        by_type = {}
        by_sector = {}
        by_asset = []

        for holding in holdings:
            asset = asset_map.get(holding.asset_id)
            if not asset:
                continue

            value = float(holding.current_value or holding.cost_basis_total)
            allocation_percent = (value / total_value) * 100

            # By asset type
            asset_type = asset.asset_type.value
            by_type[asset_type] = by_type.get(asset_type, 0) + allocation_percent

            # By sector
            if asset.sector:
                by_sector[asset.sector] = by_sector.get(asset.sector, 0) + allocation_percent

            # Individual assets
            by_asset.append({
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_type": asset_type,
                "sector": asset.sector,
                "allocation_percent": round(allocation_percent, 2),
                "value": round(value, 2),
            })

        # Sort by allocation percentage
        by_asset.sort(key=lambda x: x["allocation_percent"], reverse=True)

        return {
            "by_type": {k: round(v, 2) for k, v in by_type.items()},
            "by_sector": {k: round(v, 2) for k, v in by_sector.items()},
            "by_asset": by_asset,
        }

    def _get_recent_activity(self, portfolio_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent portfolio activity."""
        recent_transactions = (
            self.db.query(Transaction, Asset)
            .join(Asset, Transaction.asset_id == Asset.id)
            .filter(Transaction.portfolio_id == portfolio_id)
            .order_by(desc(Transaction.transaction_date))
            .limit(limit)
            .all()
        )

        activity = []
        for transaction, asset in recent_transactions:
            activity.append({
                "id": transaction.id,
                "type": transaction.transaction_type.value,
                "symbol": asset.symbol,
                "asset_name": asset.name,
                "quantity": float(transaction.quantity),
                "price": float(transaction.price),
                "total_amount": float(transaction.total_amount),
                "date": transaction.transaction_date,
                "fees": float(transaction.fees),
            })

        return activity

    async def _update_asset_pnl(self, portfolio_asset: PortfolioAsset) -> None:
        """Update unrealized P&L for a portfolio asset."""
        # This would integrate with your existing market data service
        # For now, we'll use a simplified approach

        portfolio_service = PortfolioService(self.db)
        await portfolio_service._update_asset_pnl(portfolio_asset)

    def get_portfolio_performance_chart_data(
        self, portfolio_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """Get portfolio performance chart data."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get performance history
        performance_data = (
            self.db.query(PortfolioPerformanceHistory)
            .filter(
                and_(
                    PortfolioPerformanceHistory.portfolio_id == portfolio_id,
                    PortfolioPerformanceHistory.snapshot_date >= start_date,
                )
            )
            .order_by(PortfolioPerformanceHistory.snapshot_date)
            .all()
        )

        chart_data = {
            "dates": [],
            "values": [],
            "returns": [],
            "cumulative_returns": [],
        }

        for snapshot in performance_data:
            chart_data["dates"].append(snapshot.snapshot_date.isoformat())
            chart_data["values"].append(float(snapshot.total_value))
            chart_data["returns"].append(float(snapshot.daily_return or 0))
            chart_data["cumulative_returns"].append(float(snapshot.cumulative_return or 0))

        return chart_data

    def get_asset_performance_chart_data(
        self, asset_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """Get asset performance chart data."""
        from app.core.database.models.asset import AssetPrice

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get price data
        price_data = (
            self.db.query(AssetPrice)
            .filter(
                and_(
                    AssetPrice.asset_id == asset_id,
                    AssetPrice.date >= start_date,
                )
            )
            .order_by(AssetPrice.date)
            .all()
        )

        chart_data = {
            "dates": [],
            "prices": [],
            "volumes": [],
            "returns": [],
        }

        for price in price_data:
            chart_data["dates"].append(price.date.isoformat())
            chart_data["prices"].append(float(price.close_price))
            chart_data["volumes"].append(float(price.volume or 0))

        # Calculate returns
        if len(chart_data["prices"]) > 1:
            for i in range(1, len(chart_data["prices"])):
                prev_price = chart_data["prices"][i - 1]
                curr_price = chart_data["prices"][i]
                daily_return = (curr_price - prev_price) / prev_price
                chart_data["returns"].append(daily_return)

        return chart_data
