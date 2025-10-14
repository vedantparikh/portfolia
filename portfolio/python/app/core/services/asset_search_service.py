"""
Asset Search Service
Advanced asset search and discovery service with filtering and ranking.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_, case
from sqlalchemy.orm import Session

from core.database.models import Asset
from core.database.models.asset import AssetType


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
            search_terms = query.split()
            # 1. Build the filter condition: All terms must be present
            filter_conditions = []
            for term in search_terms:
                term_filter = or_(
                    Asset.symbol.ilike(f"%{term}%"),
                    Asset.name.ilike(f"%{term}%"),
                    Asset.description.ilike(f"%{term}%"),
                )
                filter_conditions.append(term_filter)
            base_query = base_query.filter(and_(*filter_conditions))

            # 2. Build the ranking score
            # We create a sum of scores for each term
            rank_score = 0
            for term in search_terms:
                rank_score += case(
                    # Highest score for exact symbol match
                    (Asset.symbol.ilike(term), 10),
                    # High score for name starting with the term
                    (Asset.name.ilike(f"{term}%"), 5),
                    # Medium score for name containing the term
                    (Asset.name.ilike(f"%{term}%"), 2),
                    # Low score for description match
                    (Asset.description.ilike(f"%{term}%"), 1),
                    else_=0
                )

            # Add the rank score to the query
            base_query = base_query.add_columns(rank_score.label("rank"))

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

        # Format assets for the response
        formatted_assets = [
            {
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
            for asset in assets
        ]

        return {
            "assets": formatted_assets,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def get_asset_details(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed asset information."""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return None

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
