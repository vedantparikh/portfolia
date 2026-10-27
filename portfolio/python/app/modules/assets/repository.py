"""Asset rows. Does not commit; the request session does."""

from sqlalchemy.orm import Session

from core.database.models import Asset


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_symbol(self, user_id: int, symbol: str) -> Asset | None:
        return (
            self.db.query(Asset)
            .filter(Asset.symbol == symbol, Asset.user_id == user_id)
            .first()
        )

    def symbols_for_user(self, user_id: int, symbols: list[str]) -> set[str]:
        rows = (
            self.db.query(Asset.symbol)
            .filter(Asset.user_id == user_id, Asset.symbol.in_(symbols))
            .all()
        )
        return {row[0] for row in rows}

    def add(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.flush()
        self.db.refresh(asset)
        return asset

    def add_all(self, assets: list[Asset]) -> list[Asset]:
        self.db.add_all(assets)
        self.db.flush()
        for asset in assets:
            self.db.refresh(asset)
        return assets

    def list_active(
        self,
        user_id: int,
        *,
        symbol: str | None,
        asset_type: str | None,
        skip: int,
        limit: int,
    ) -> list[Asset]:
        query = self.db.query(Asset).filter(
            Asset.is_active.is_(True), Asset.user_id == user_id
        )
        if symbol:
            query = query.filter(Asset.symbol.ilike(f"%{symbol.upper()}%"))
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        return query.offset(skip).limit(limit).all()

    def get_active(self, user_id: int, asset_id: int) -> Asset | None:
        return (
            self.db.query(Asset)
            .filter(
                Asset.id == asset_id,
                Asset.is_active.is_(True),
                Asset.user_id == user_id,
            )
            .first()
        )

    def save(self, asset: Asset) -> Asset:
        self.db.flush()
        self.db.refresh(asset)
        return asset
