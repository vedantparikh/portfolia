from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionType,
)
from app.core.database.utils import get_portfolio_performance_summary
from app.core.schemas.portfolio import (
    PortfolioAssetCreate,
    PortfolioAssetUpdate,
    PortfolioAssetWithDetails,
    PortfolioCreate,
    PortfolioHolding,
    PortfolioStatistics,
    PortfolioSummary,
    PortfolioUpdate,
    TransactionCreate,
    TransactionUpdate,
)
from app.core.services.market_data_service import MarketDataService


class PortfolioService:
    """Service for comprehensive portfolio operations."""

    def __init__(self, db: Session):
        self.db = db
        self.market_data_service = MarketDataService()

    # Portfolio CRUD Operations
    def create_portfolio(
        self, portfolio_data: PortfolioCreate, user_id: int
    ) -> Portfolio:
        """Create a new portfolio."""
        portfolio = Portfolio(
            user_id=user_id,
            name=portfolio_data.name,
            description=portfolio_data.description,
            currency=portfolio_data.currency,
            is_active=portfolio_data.is_active,
            is_public=portfolio_data.is_public,
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def get_user_portfolios(
        self, user_id: int, include_inactive: bool = False
    ) -> List[Portfolio]:
        """Get all portfolios for a user."""
        query = self.db.query(Portfolio).filter(Portfolio.user_id == user_id)
        if not include_inactive:
            query = query.filter(Portfolio.is_active == True)
        return query.all()

    def get_portfolio(
        self, portfolio_id: int, user_id: Optional[int] = None
    ) -> Optional[Portfolio]:
        """Get a specific portfolio by ID, optionally checking ownership."""
        query = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id)
        if user_id:
            query = query.filter(Portfolio.user_id == user_id)
        return query.first()

    def update_portfolio(
        self, portfolio_id: int, portfolio_data: PortfolioUpdate, user_id: int
    ) -> Optional[Portfolio]:
        """Update a portfolio."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if portfolio:
            for field, value in portfolio_data.dict(exclude_unset=True).items():
                setattr(portfolio, field, value)
            # Note: updated_at is handled by SQLAlchemy onupdate trigger
            self.db.commit()
            self.db.refresh(portfolio)
        return portfolio

    def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        """Soft delete a portfolio by setting is_active to False."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if portfolio:
            portfolio.is_active = False
            # Note: updated_at is handled by SQLAlchemy onupdate trigger
            self.db.commit()
            return True
        return False

    def hard_delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        """Permanently delete a portfolio and all associated data."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if portfolio:
            self.db.delete(portfolio)
            self.db.commit()
            return True
        return False

    # Portfolio Asset Management
    async def add_asset_to_portfolio(
        self, portfolio_id: int, asset_data: PortfolioAssetCreate, user_id: int
    ) -> Optional[PortfolioAsset]:
        """Add an asset to a portfolio."""
        # Verify portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        # Check if asset already exists in portfolio
        existing_asset = (
            self.db.query(PortfolioAsset)
            .filter(
                and_(
                    PortfolioAsset.portfolio_id == portfolio_id,
                    PortfolioAsset.asset_id == asset_data.asset_id,
                )
            )
            .first()
        )

        if existing_asset:
            # Update existing asset with new quantity and cost basis
            new_quantity = existing_asset.quantity + asset_data.quantity
            new_cost_basis_total = existing_asset.cost_basis_total + (
                asset_data.cost_basis * asset_data.quantity
            )
            new_cost_basis = new_cost_basis_total / new_quantity

            existing_asset.quantity = new_quantity
            existing_asset.cost_basis = new_cost_basis
            existing_asset.cost_basis_total = new_cost_basis_total

            # Update current value and P&L if available
            await self._update_asset_pnl(existing_asset)

            self.db.commit()
            self.db.refresh(existing_asset)
            return existing_asset

        # Create new portfolio asset
        portfolio_asset = PortfolioAsset(
            portfolio_id=portfolio_id,
            asset_id=asset_data.asset_id,
            quantity=asset_data.quantity,
            cost_basis=asset_data.cost_basis,
            cost_basis_total=asset_data.cost_basis * asset_data.quantity,
        )

        # Calculate initial P&L if current price is available
        portfolio_asset = await self._update_asset_pnl(portfolio_asset)

        self.db.add(portfolio_asset)
        self.db.commit()
        self.db.refresh(portfolio_asset)
        return portfolio_asset

    async def _update_asset_pnl(
        self, portfolio_asset: PortfolioAsset
    ) -> PortfolioAsset:
        """Update unrealized P&L for a portfolio asset using real-time data."""
        try:
            # Get asset information
            asset = (
                self.db.query(Asset)
                .filter(Asset.id == portfolio_asset.asset_id)
                .first()
            )
            if not asset:
                return portfolio_asset

            # Get current price from yfinance
            current_price = await self.market_data_service.get_current_price(
                symbol=asset.symbol
            )
            last_trading_day_price = (
                await self.market_data_service.get_yesterdays_close(
                    symbol=asset.symbol
                )
            )

            if current_price:
                current_value = float(current_price) * float(portfolio_asset.quantity)
                portfolio_asset.current_value = Decimal(str(current_value))

                # Calculate unrealized P&L
                cost_basis_total = float(portfolio_asset.cost_basis_total)
                unrealized_pnl = current_value - cost_basis_total
                portfolio_asset.unrealized_pnl = Decimal(str(unrealized_pnl))

                # Calculate P&L percentage
                if cost_basis_total > 0:
                    pnl_percent = (unrealized_pnl / cost_basis_total) * 100
                    portfolio_asset.unrealized_pnl_percent = Decimal(str(pnl_percent))
                else:
                    portfolio_asset.unrealized_pnl_percent = Decimal("0")

                # Calculate Today's P&L and Percentage
                if last_trading_day_price:
                    previous_day_value = float(last_trading_day_price) * float(
                        portfolio_asset.quantity
                    )
                    todays_pnl_value = current_value - previous_day_value
                    portfolio_asset.todays_pnl = Decimal(str(todays_pnl_value))

                    if previous_day_value > 0:
                        todays_pnl_percent = (
                            todays_pnl_value / previous_day_value
                        ) * 100
                        portfolio_asset.todays_pnl_percent = Decimal(
                            str(todays_pnl_percent)
                        )
                    else:
                        portfolio_asset.todays_pnl_percent = Decimal("0")
                else:
                    # Cannot calculate today's P&L without yesterday's close
                    portfolio_asset.todays_pnl = None
                    portfolio_asset.todays_pnl_percent = None

            else:
                # If we can't get current price, keep existing values or set to None
                portfolio_asset.current_value = None
                portfolio_asset.unrealized_pnl = None
                portfolio_asset.unrealized_pnl_percent = None
                portfolio_asset.todays_pnl = None
                portfolio_asset.todays_pnl_percent = None

            # Calculate realized P&L
            realized_pnl, realized_pnl_percent = self._calculate_realized_pnl(
                portfolio_asset.portfolio_id, portfolio_asset.asset_id
            )
            portfolio_asset.realized_pnl = realized_pnl
            portfolio_asset.realized_pnl_percent = realized_pnl_percent

        except Exception as e:
            # Log error but don't fail the operation
            print(f"Error updating P&L for asset {portfolio_asset.asset_id}: {e}")

        return portfolio_asset

    def _calculate_realized_pnl(
        self, portfolio_id: int, asset_id: int
    ) -> tuple[Decimal, Decimal]:
        """Calculate realized P&L for a specific asset based on sell transactions."""
        # Get all sell transactions for this asset in this portfolio
        sell_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.portfolio_id == portfolio_id,
                    Transaction.asset_id == asset_id,
                    Transaction.transaction_type == TransactionType.SELL,
                )
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        if not sell_transactions:
            return Decimal("0"), Decimal("0")

        # Get all buy transactions for this asset in this portfolio
        buy_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.portfolio_id == portfolio_id,
                    Transaction.asset_id == asset_id,
                    Transaction.transaction_type == TransactionType.BUY,
                )
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        if not buy_transactions:
            return Decimal("0"), Decimal("0")

        # Calculate realized P&L using FIFO (First In, First Out) method
        total_realized_pnl = Decimal("0")
        total_cost_basis_sold = Decimal("0")

        # Create a copy of buy transactions to track remaining quantities
        remaining_buys = []
        for buy in buy_transactions:
            remaining_buys.append(
                {
                    "quantity": buy.quantity,
                    "price": buy.price,
                    "total_amount": buy.total_amount,
                    "date": buy.transaction_date,
                }
            )

        # Process each sell transaction
        for sell in sell_transactions:
            sell_quantity = sell.quantity
            sell_price = sell.price

            # Use FIFO to match sells with buys
            while sell_quantity > 0 and remaining_buys:
                buy = remaining_buys[0]
                available_quantity = buy["quantity"]

                if available_quantity <= 0:
                    remaining_buys.pop(0)
                    continue

                # Calculate how much of this sell to match with this buy
                quantity_to_match = min(sell_quantity, available_quantity)

                # Calculate cost basis for this portion
                cost_basis_portion = (quantity_to_match / buy["quantity"]) * buy[
                    "total_amount"
                ]
                total_cost_basis_sold += cost_basis_portion

                # Calculate realized P&L for this portion
                sell_proceeds = quantity_to_match * sell_price
                realized_pnl_portion = sell_proceeds - cost_basis_portion
                total_realized_pnl += realized_pnl_portion

                # Update remaining quantities
                sell_quantity -= quantity_to_match
                buy["quantity"] -= quantity_to_match
                buy["total_amount"] -= cost_basis_portion

                # Remove buy if fully consumed
                if buy["quantity"] <= 0:
                    remaining_buys.pop(0)

        # Calculate realized P&L percentage
        if total_cost_basis_sold > 0:
            realized_pnl_percent = (total_realized_pnl / total_cost_basis_sold) * 100
        else:
            realized_pnl_percent = Decimal("0")

        return total_realized_pnl, realized_pnl_percent

    async def update_portfolio_asset(
        self,
        portfolio_id: int,
        asset_id: int,
        asset_data: PortfolioAssetUpdate,
        user_id: int,
    ) -> Optional[PortfolioAsset]:
        """Update an asset in a portfolio."""
        portfolio_asset = (
            self.db.query(PortfolioAsset)
            .filter(
                and_(
                    PortfolioAsset.portfolio_id == portfolio_id,
                    PortfolioAsset.asset_id == asset_id,
                )
            )
            .first()
        )

        if not portfolio_asset:
            return None

        # Verify portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        # Update fields
        if asset_data.quantity is not None:
            portfolio_asset.quantity = asset_data.quantity
        if asset_data.cost_basis is not None:
            portfolio_asset.cost_basis = asset_data.cost_basis
            portfolio_asset.cost_basis_total = (
                asset_data.cost_basis * portfolio_asset.quantity
            )
        if asset_data.current_value is not None:
            portfolio_asset.current_value = asset_data.current_value
        if asset_data.unrealized_pnl is not None:
            portfolio_asset.unrealized_pnl = asset_data.unrealized_pnl
        if asset_data.unrealized_pnl_percent is not None:
            portfolio_asset.unrealized_pnl_percent = asset_data.unrealized_pnl_percent
        if asset_data.realized_pnl is not None:
            portfolio_asset.realized_pnl = asset_data.realized_pnl
        if asset_data.realized_pnl_percent is not None:
            portfolio_asset.realized_pnl_percent = asset_data.realized_pnl_percent

        # Update P&L if not manually set
        if asset_data.current_value is None and asset_data.unrealized_pnl is None:
            portfolio_asset = await self._update_asset_pnl(portfolio_asset)

        # Note: last_updated is handled by SQLAlchemy onupdate trigger
        self.db.commit()
        self.db.refresh(portfolio_asset)
        return portfolio_asset

    def remove_asset_from_portfolio(
        self, portfolio_id: int, asset_id: int, user_id: int
    ) -> bool:
        """Remove an asset from a portfolio."""
        portfolio_asset = (
            self.db.query(PortfolioAsset)
            .filter(
                and_(
                    PortfolioAsset.portfolio_id == portfolio_id,
                    PortfolioAsset.asset_id == asset_id,
                )
            )
            .first()
        )

        if not portfolio_asset:
            return False

        # Verify portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        self.db.delete(portfolio_asset)
        self.db.commit()
        return True

    def get_portfolio_assets(
        self, portfolio_id: int, user_id: int
    ) -> List[PortfolioAsset]:
        """Get all assets in a portfolio."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return []

        return (
            self.db.query(PortfolioAsset)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

    async def get_portfolio_assets_with_details(
        self, portfolio_id: int, user_id: int
    ) -> List[PortfolioAssetWithDetails]:
        """Get portfolio assets with additional asset information."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return []

        assets = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        result = []
        for portfolio_asset, asset in assets:
            portfolio_asset = await self._update_asset_pnl(portfolio_asset)
            self.db.add(portfolio_asset)
            self.db.commit()
            self.db.refresh(portfolio_asset)

            asset_details = PortfolioAssetWithDetails(
                id=portfolio_asset.id,
                portfolio_id=portfolio_asset.portfolio_id,
                asset_id=portfolio_asset.asset_id,
                quantity=portfolio_asset.quantity,
                cost_basis=portfolio_asset.cost_basis,
                cost_basis_total=portfolio_asset.cost_basis_total,
                current_value=portfolio_asset.current_value,
                unrealized_pnl=portfolio_asset.unrealized_pnl,
                unrealized_pnl_percent=portfolio_asset.unrealized_pnl_percent,
                realized_pnl=portfolio_asset.realized_pnl,
                realized_pnl_percent=portfolio_asset.realized_pnl_percent,
                last_updated=portfolio_asset.last_updated,
                symbol=asset.symbol,
                asset_name=asset.name,
                market_value=portfolio_asset.current_value,
                total_return=portfolio_asset.unrealized_pnl,
                total_return_percent=portfolio_asset.unrealized_pnl_percent,
            )
            result.append(asset_details)

        return result

    # Transaction Management
    def add_transaction(
        self, portfolio_id: int, transaction_data: TransactionCreate, user_id: int
    ) -> Optional[Transaction]:
        """Add a transaction to a portfolio."""
        # Verify portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        # Create transaction
        transaction = Transaction(
            portfolio_id=portfolio_id,
            asset_id=transaction_data.asset_id,
            transaction_type=transaction_data.transaction_type,
            quantity=transaction_data.quantity,
            price=transaction_data.price,
            currency=transaction_data.currency,
            transaction_date=transaction_data.transaction_date,
            fees=transaction_data.fees or Decimal("0"),
            total_amount=transaction_data.quantity * transaction_data.price,
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        # Update portfolio asset based on transaction
        self._update_portfolio_asset_from_transaction(
            portfolio_id, transaction_data.asset_id, transaction
        )

        return transaction

    async def _update_portfolio_asset_from_transaction(
        self, portfolio_id: int, asset_id: int, transaction: Transaction
    ):
        """Update portfolio asset based on transaction."""
        portfolio_asset = (
            self.db.query(PortfolioAsset)
            .filter(
                and_(
                    PortfolioAsset.portfolio_id == portfolio_id,
                    PortfolioAsset.asset_id == asset_id,
                )
            )
            .first()
        )

        if transaction.transaction_type == TransactionType.BUY:
            if portfolio_asset:
                # Update existing asset
                new_quantity = portfolio_asset.quantity + transaction.quantity
                new_cost_basis_total = (
                    portfolio_asset.cost_basis_total + transaction.total_amount
                )
                new_cost_basis = new_cost_basis_total / new_quantity

                portfolio_asset.quantity = new_quantity
                portfolio_asset.cost_basis = new_cost_basis
                portfolio_asset.cost_basis_total = new_cost_basis_total
            else:
                # Create new portfolio asset
                portfolio_asset = PortfolioAsset(
                    portfolio_id=portfolio_id,
                    asset_id=asset_id,
                    quantity=transaction.quantity,
                    cost_basis=transaction.price,
                    cost_basis_total=transaction.total_amount,
                )
                self.db.add(portfolio_asset)

        elif transaction.transaction_type == TransactionType.SELL:
            if portfolio_asset:
                # Update existing asset
                new_quantity = portfolio_asset.quantity - transaction.quantity
                if new_quantity <= 0:
                    # Remove asset if quantity becomes 0 or negative
                    self.db.delete(portfolio_asset)
                else:
                    # Adjust cost basis proportionally
                    remaining_ratio = new_quantity / portfolio_asset.quantity
                    portfolio_asset.quantity = new_quantity
                    portfolio_asset.cost_basis_total = (
                        portfolio_asset.cost_basis_total * remaining_ratio
                    )

        # Update P&L after transaction
        if portfolio_asset and portfolio_asset in self.db:
            portfolio_asset = await self._update_asset_pnl(portfolio_asset)
            self.db.refresh(portfolio_asset)

        # Note: last_updated is handled by SQLAlchemy onupdate trigger
        self.db.commit()

    def get_portfolio_transactions(
        self, portfolio_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Get transactions for a portfolio."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return []

        return (
            self.db.query(Transaction)
            .filter(Transaction.portfolio_id == portfolio_id)
            .order_by(desc(Transaction.transaction_date))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_transaction(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Get a specific transaction."""
        transaction = (
            self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if transaction:
            # Verify portfolio ownership
            portfolio = self.get_portfolio(transaction.portfolio_id, user_id)
            if not portfolio:
                return None
        return transaction

    def update_transaction(
        self, transaction_id: int, transaction_data: TransactionUpdate, user_id: int
    ) -> Optional[Transaction]:
        """Update a transaction."""
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return None

        # Update fields
        for field, value in transaction_data.dict(exclude_unset=True).items():
            setattr(transaction, field, value)

        if transaction_data.quantity is not None or transaction_data.price is not None:
            # Recalculate total amount
            quantity = transaction_data.quantity or transaction.quantity
            price = transaction_data.price or transaction.price
            transaction.total_amount = quantity * price

        # Note: updated_at is handled by SQLAlchemy onupdate trigger
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """Delete a transaction."""
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return False

        self.db.delete(transaction)
        self.db.commit()
        return True

    # Portfolio Analytics and Performance
    async def get_portfolio_summary(
        self, portfolio_id: int, user_id: int
    ) -> PortfolioSummary:
        """Get comprehensive portfolio summary."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return PortfolioSummary(
                portfolio_id=0,
                portfolio_name="",
                currency="",
                total_assets=0,
                total_cost_basis=0.0,
                total_current_value=0.0,
                today_pnl=0.0,
                today_pnl_percent=0.0,
                total_unrealized_pnl=0.0,
                total_unrealized_pnl_percent=0.0,
                last_updated=None,
                recent_transactions=0,
                is_active=False,
                is_public=False,
            )

        # Get portfolio assets
        assets = self.get_portfolio_assets(portfolio_id, user_id)

        # Initialize summary metrics
        total_cost_basis = Decimal("0")
        total_current_value = Decimal("0")
        total_today_pnl = Decimal("0")

        # Update each asset and aggregate the values
        for asset in assets:
            await self._update_asset_pnl(asset)  # This updates the asset object
            total_cost_basis += asset.cost_basis_total
            total_current_value += asset.current_value or asset.cost_basis_total
            if asset.todays_pnl:
                total_today_pnl += asset.todays_pnl

        # Convert to float for calculations
        total_cost_basis_f = float(total_cost_basis)
        total_current_value_f = float(total_current_value)
        total_today_pnl_f = float(total_today_pnl)

        # Calculate unrealized P&L
        total_unrealized_pnl = total_current_value_f - total_cost_basis_f
        total_unrealized_pnl_percent = (
            (total_unrealized_pnl / total_cost_basis_f * 100)
            if total_cost_basis_f > 0
            else 0
        )

        # Calculate today's P&L percentage
        total_previous_day_value = total_current_value_f - total_today_pnl_f
        total_today_pnl_percent = (
            (total_today_pnl_f / total_previous_day_value * 100)
            if total_previous_day_value > 0
            else 0
        )

        # Get recent transactions
        recent_transactions = self.get_portfolio_transactions(
            portfolio_id, user_id, limit=5
        )

        return PortfolioSummary(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            currency=portfolio.currency,
            total_assets=len(assets),
            total_cost_basis=round(total_cost_basis_f, 2),
            total_current_value=round(total_current_value_f, 2),
            today_pnl=round(total_today_pnl_f, 2),
            today_pnl_percent=round(total_today_pnl_percent, 2),
            total_unrealized_pnl=round(total_unrealized_pnl, 2),
            total_unrealized_pnl_percent=round(total_unrealized_pnl_percent, 2),
            last_updated=portfolio.updated_at,
            recent_transactions=len(recent_transactions),
            is_active=portfolio.is_active,
            is_public=portfolio.is_public,
        )

    def get_portfolio_performance(
        self, portfolio_id: int, user_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """Get portfolio performance metrics."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return {}

        # Use utility function for performance calculation
        return get_portfolio_performance_summary(self.db, portfolio_id, days)

    async def get_portfolio_holdings(
        self, portfolio_id: int, user_id: int
    ) -> List[PortfolioHolding]:
        """Get detailed portfolio holdings with current values."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return []

        assets = self.get_portfolio_assets(portfolio_id, user_id)
        holdings = []

        for asset in assets:
            # Get asset details
            asset_info = self.db.query(Asset).filter(Asset.id == asset.asset_id).first()
            if asset_info:
                asset = await self._update_asset_pnl(asset)
                self.db.commit()

                holding = PortfolioHolding(
                    asset_id=asset.asset_id,
                    symbol=asset_info.symbol,
                    name=asset_info.name,
                    quantity=float(asset.quantity),
                    cost_basis=float(asset.cost_basis),
                    cost_basis_total=float(asset.cost_basis_total),
                    current_value=(
                        float(asset.current_value) if asset.current_value else None
                    ),
                    today_pnl=float(asset.todays_pnl),
                    today_pnl_percent=float(asset.todays_pnl_percent),
                    unrealized_pnl=(
                        float(asset.unrealized_pnl) if asset.unrealized_pnl else None
                    ),
                    unrealized_pnl_percent=(
                        float(asset.unrealized_pnl_percent)
                        if asset.unrealized_pnl_percent
                        else None
                    ),
                    realized_pnl=(
                        float(asset.realized_pnl) if asset.realized_pnl else None
                    ),
                    realized_pnl_percent=(
                        float(asset.realized_pnl_percent)
                        if asset.realized_pnl_percent
                        else None
                    ),
                    last_updated=asset.last_updated,
                )
                holdings.append(holding)

        return holdings

    def search_portfolios(
        self, user_id: int, search_term: str = None, currency: str = None
    ) -> List[Portfolio]:
        """Search portfolios with filters."""
        query = self.db.query(Portfolio).filter(
            Portfolio.user_id == user_id, Portfolio.is_active == True
        )

        if search_term:
            query = query.filter(Portfolio.name.ilike(f"%{search_term}%"))

        if currency:
            query = query.filter(Portfolio.currency == currency)

        return query.all()

    def get_portfolio_statistics(self, user_id: int) -> PortfolioStatistics:
        """Get overall portfolio statistics for a user."""
        portfolios = self.get_user_portfolios(user_id)

        total_portfolios = len(portfolios)
        active_portfolios = len([p for p in portfolios if p.is_active])
        total_assets = 0
        total_value = 0

        for portfolio in portfolios:
            if portfolio.is_active:
                assets = self.get_portfolio_assets(portfolio.id, user_id)
                total_assets += len(assets)
                for asset in assets:
                    if asset.current_value:
                        total_value += float(asset.current_value)
                    else:
                        total_value += float(asset.cost_basis_total)

        return PortfolioStatistics(
            total_portfolios=total_portfolios,
            active_portfolios=active_portfolios,
            total_assets=total_assets,
            total_value=round(total_value, 2),
        )

    async def refresh_portfolio_values(self, portfolio_id: int, user_id: int) -> bool:
        """Refresh current values and P&L for all assets in a portfolio."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        assets = self.get_portfolio_assets(portfolio_id, user_id)
        updated = False

        for asset in assets:
            old_current_value = asset.current_value
            old_unrealized_pnl = asset.unrealized_pnl

            await self._update_asset_pnl(asset)

            if (
                asset.current_value != old_current_value
                or asset.unrealized_pnl != old_unrealized_pnl
            ):
                updated = True

        if updated:
            self.db.commit()
            return True

        return False

    def get_public_portfolios(
        self, limit: int = 50, offset: int = 0
    ) -> List[Portfolio]:
        """Get public portfolios for discovery."""
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.is_public == True, Portfolio.is_active == True)
            .order_by(desc(Portfolio.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )