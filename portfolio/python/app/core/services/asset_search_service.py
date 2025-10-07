"""
Asset Search Service
Advanced asset search and discovery service with filtering and ranking.
"""

from datetime import timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from core.database.models import Asset
from core.database.models.asset import AssetType
from core.database.models.portfolio_analytics import AssetPerformanceMetrics


class AssetSearchService:
    """Service for advanced asset search and discovery."""

    def __init__(self, db: Session):
        self.db = db

    def search_assets(
        self,
        query: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        sector: Optional[str] = None,
        exchange: Optional[str] = None,
        country: Optional[str] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        sort_by: str = "symbol",
        sort_order: str = "asc",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search assets with advanced filtering and sorting."""
        # Build base query
        base_query = self.db.query(Asset).filter(Asset.is_active == True)

        # Apply filters
        if query:
            search_filter = or_(
                Asset.symbol.ilike(f"%{query}%"),
                Asset.name.ilike(f"%{query}%"),
                Asset.description.ilike(f"%{query}%"),
            )
            base_query = base_query.filter(search_filter)

        if asset_type:
            base_query = base_query.filter(Asset.asset_type == asset_type)

        if sector:
            base_query = base_query.filter(Asset.sector.ilike(f"%{sector}%"))

        if exchange:
            base_query = base_query.filter(Asset.exchange.ilike(f"%{exchange}%"))

        if country:
            base_query = base_query.filter(Asset.country.ilike(f"%{country}%"))

        # Apply sorting
        if sort_by == "symbol":
            order_column = Asset.symbol
        elif sort_by == "name":
            order_column = Asset.name
        elif sort_by == "asset_type":
            order_column = Asset.asset_type
        elif sort_by == "sector":
            order_column = Asset.sector
        elif sort_by == "created_at":
            order_column = Asset.created_at
        else:
            order_column = Asset.symbol

        if sort_order == "desc":
            order_column = desc(order_column)

        base_query = base_query.order_by(order_column)

        # Get total count
        total_count = base_query.count()

        # Apply pagination
        assets = base_query.offset(offset).limit(limit).all()

        # Enhance with performance data
        enhanced_assets = self._enhance_assets_with_performance(assets)

        return {
            "assets": enhanced_assets,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def get_asset_details(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed asset information with performance metrics."""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return None

        # Get latest performance metrics
        latest_metrics = (
            self.db.query(AssetPerformanceMetrics)
            .filter(AssetPerformanceMetrics.asset_id == asset_id)
            .order_by(desc(AssetPerformanceMetrics.calculation_date))
            .first()
        )

        # Get price history summary
        price_summary = self._get_price_summary(asset_id)

        return {
            "id": asset.id,
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_type": asset.asset_type.value,
            "currency": asset.currency,
            "exchange": asset.exchange,
            "isin": asset.isin,
            "cusip": asset.cusip,
            "sector": asset.sector,
            "industry": asset.industry,
            "country": asset.country,
            "description": asset.description,
            "is_active": asset.is_active,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
            "performance_metrics": self._format_performance_metrics(latest_metrics),
            "price_summary": price_summary,
        }

    def get_popular_assets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular assets based on portfolio holdings."""
        # Count how many portfolios hold each asset
        popular_assets = (
            self.db.query(
                Asset.id,
                Asset.symbol,
                Asset.name,
                Asset.asset_type,
                Asset.sector,
                func.count().label("portfolio_count"),
            )
            .join(Asset.portfolio_holdings)
            .group_by(
                Asset.id, Asset.symbol, Asset.name, Asset.asset_type, Asset.sector
            )
            .order_by(desc("portfolio_count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_type": asset.asset_type.value,
                "sector": asset.sector,
                "portfolio_count": asset.portfolio_count,
            }
            for asset in popular_assets
        ]

    def get_sector_breakdown(self) -> List[Dict[str, Any]]:
        """Get asset breakdown by sector."""
        sector_data = (
            self.db.query(
                Asset.sector,
                func.count(Asset.id).label("asset_count"),
                func.count(Asset.portfolio_holdings).label("portfolio_count"),
            )
            .outerjoin(Asset.portfolio_holdings)
            .filter(Asset.is_active == True, Asset.sector.isnot(None))
            .group_by(Asset.sector)
            .order_by(desc("asset_count"))
            .all()
        )

        return [
            {
                "sector": sector.sector,
                "asset_count": sector.asset_count,
                "portfolio_count": sector.portfolio_count,
            }
            for sector in sector_data
        ]

    def get_asset_type_breakdown(self) -> List[Dict[str, Any]]:
        """Get asset breakdown by type."""
        type_data = (
            self.db.query(
                Asset.asset_type,
                func.count(Asset.id).label("asset_count"),
                func.count(Asset.portfolio_holdings).label("portfolio_count"),
            )
            .outerjoin(Asset.portfolio_holdings)
            .filter(Asset.is_active == True)
            .group_by(Asset.asset_type)
            .order_by(desc("asset_count"))
            .all()
        )

        return [
            {
                "asset_type": asset_type.asset_type.value,
                "asset_count": asset_type.asset_count,
                "portfolio_count": asset_type.portfolio_count,
            }
            for asset_type in type_data
        ]

    def get_exchange_breakdown(self) -> List[Dict[str, Any]]:
        """Get asset breakdown by exchange."""
        exchange_data = (
            self.db.query(
                Asset.exchange,
                func.count(Asset.id).label("asset_count"),
                func.count(Asset.portfolio_holdings).label("portfolio_count"),
            )
            .outerjoin(Asset.portfolio_holdings)
            .filter(Asset.is_active == True, Asset.exchange.isnot(None))
            .group_by(Asset.exchange)
            .order_by(desc("asset_count"))
            .all()
        )

        return [
            {
                "exchange": exchange.exchange,
                "asset_count": exchange.asset_count,
                "portfolio_count": exchange.portfolio_count,
            }
            for exchange in exchange_data
        ]

    def get_search_suggestions(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get search suggestions based on partial query."""
        if len(query) < 2:
            return []

        suggestions = (
            self.db.query(Asset.symbol, Asset.name, Asset.asset_type)
            .filter(
                and_(
                    Asset.is_active == True,
                    or_(
                        Asset.symbol.ilike(f"{query}%"),
                        Asset.name.ilike(f"{query}%"),
                    ),
                )
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "symbol": suggestion.symbol,
                "name": suggestion.name,
                "asset_type": suggestion.asset_type.value,
            }
            for suggestion in suggestions
        ]

    def _enhance_assets_with_performance(
        self, assets: List[Asset]
    ) -> List[Dict[str, Any]]:
        """Enhance asset list with performance metrics."""
        if not assets:
            return []

        asset_ids = [asset.id for asset in assets]

        # Get latest performance metrics for all assets
        latest_metrics = (
            self.db.query(AssetPerformanceMetrics)
            .filter(AssetPerformanceMetrics.asset_id.in_(asset_ids))
            .distinct(AssetPerformanceMetrics.asset_id)
            .order_by(
                AssetPerformanceMetrics.asset_id,
                desc(AssetPerformanceMetrics.calculation_date),
            )
            .all()
        )

        metrics_map = {metric.asset_id: metric for metric in latest_metrics}

        enhanced_assets = []
        for asset in assets:
            asset_dict = {
                "id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_type": asset.asset_type.value,
                "currency": asset.currency,
                "exchange": asset.exchange,
                "sector": asset.sector,
                "industry": asset.industry,
                "country": asset.country,
                "is_active": asset.is_active,
                "created_at": asset.created_at,
                "updated_at": asset.updated_at,
            }

            # Add performance metrics if available
            metrics = metrics_map.get(asset.id)
            if metrics:
                asset_dict.update(self._format_performance_metrics(metrics))

            enhanced_assets.append(asset_dict)

        return enhanced_assets

    def _format_performance_metrics(
        self, metrics: AssetPerformanceMetrics
    ) -> Dict[str, Any]:
        """Format performance metrics for API response."""
        if not metrics:
            return {}

        return {
            "current_price": float(metrics.current_price),
            "price_change": float(metrics.price_change or 0),
            "price_change_percent": float(metrics.price_change_percent or 0),
            "rsi": float(metrics.rsi) if metrics.rsi else None,
            "macd": float(metrics.macd) if metrics.macd else None,
            "volatility_20d": (
                float(metrics.volatility_20d) if metrics.volatility_20d else None
            ),
            "volatility_60d": (
                float(metrics.volatility_60d) if metrics.volatility_60d else None
            ),
            "beta": float(metrics.beta) if metrics.beta else None,
            "sharpe_ratio": (
                float(metrics.sharpe_ratio) if metrics.sharpe_ratio else None
            ),
            "total_return_1m": (
                float(metrics.total_return_1m) if metrics.total_return_1m else None
            ),
            "total_return_3m": (
                float(metrics.total_return_3m) if metrics.total_return_3m else None
            ),
            "total_return_1y": (
                float(metrics.total_return_1y) if metrics.total_return_1y else None
            ),
            "calculation_date": metrics.calculation_date,
        }

    def _get_price_summary(self, asset_id: int) -> Dict[str, Any]:
        """Get price summary for an asset."""
        from core.database.models.asset import AssetPrice

        # Get latest price
        latest_price = (
            self.db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id)
            .order_by(desc(AssetPrice.date))
            .first()
        )

        if not latest_price:
            return {}

        # Get price range for last 30 days
        from datetime import datetime, timedelta

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        price_range = (
            self.db.query(
                func.min(AssetPrice.close_price).label("min_price"),
                func.max(AssetPrice.close_price).label("max_price"),
                func.avg(AssetPrice.close_price).label("avg_price"),
            )
            .filter(
                and_(
                    AssetPrice.asset_id == asset_id,
                    AssetPrice.date >= start_date,
                )
            )
            .first()
        )

        return {
            "current_price": float(latest_price.close_price),
            "price_change": float(latest_price.price_change or 0),
            "price_change_percent": float(latest_price.price_change_percent or 0),
            "min_price_30d": (
                float(price_range.min_price) if price_range.min_price else None
            ),
            "max_price_30d": (
                float(price_range.max_price) if price_range.max_price else None
            ),
            "avg_price_30d": (
                float(price_range.avg_price) if price_range.avg_price else None
            ),
            "last_updated": latest_price.date,
        }
