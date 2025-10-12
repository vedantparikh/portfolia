import asyncio
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, case
from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionType,
)
from core.database.utils import get_portfolio_performance_summary
from core.schemas.portfolio import (
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
from core.services.market_data_service import MarketDataService


class PortfolioService:
    """Service for comprehensive portfolio operations."""

    def __init__(self, db: Session):
        self.db = db
        self.market_data_service = MarketDataService()

    # Portfolio CRUD
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

    def get_all_user_transactions(
            self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Get all transactions for a user across all their portfolios."""
        user_portfolios = self.get_user_portfolios(user_id)
        if not user_portfolios:
            return []

        portfolio_ids = [p.id for p in user_portfolios]

        # Then, query for transactions within those portfolio IDs
        return (
            self.db.query(Transaction)
            .filter(Transaction.portfolio_id.in_(portfolio_ids))
            .order_by(desc(Transaction.transaction_date))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_portfolio(
            self, portfolio_id: int, portfolio_data: PortfolioUpdate, user_id: int
    ) -> Optional[Portfolio]:
        """Update a portfolio."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if portfolio:
            for field, value in portfolio_data.dict(exclude_unset=True).items():
                setattr(portfolio, field, value)
            self.db.commit()
            self.db.refresh(portfolio)
        return portfolio

    def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        """Soft delete a portfolio by setting is_active to False."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if portfolio:
            portfolio.is_active = False
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
        """
        FIXED: Adds an asset by creating a BUY transaction, ensuring the
        transaction history is the single source of truth.
        """
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        # Create a transaction from the asset data to ensure data integrity.
        # Note: We assume today's date if not provided in the asset_data schema.
        transaction_date = getattr(asset_data, 'transaction_date', date.today())

        transaction_data = TransactionCreate(
            portfolio_id=portfolio_id,
            asset_id=asset_data.asset_id,
            transaction_type=TransactionType.BUY,
            quantity=asset_data.quantity,
            price=asset_data.cost_basis,
            transaction_date=transaction_date,
            fees=asset_data.fees,
            total_amount=asset_data.cost_basis * asset_data.quantity + asset_data.fees,
            notes=f"Initial holding added for asset ID {asset_data.asset_id}",
        )

        # Use the robust add_transaction method, which handles recalculation.
        await self.add_transaction(portfolio_id, transaction_data, user_id)

        # Return the newly calculated state of the portfolio asset.
        return (
            self.db.query(PortfolioAsset)
            .filter_by(portfolio_id=portfolio_id, asset_id=asset_data.asset_id)
            .first()
        )

    async def _refresh_asset_market_data(
            self, portfolio_asset: PortfolioAsset
    ) -> PortfolioAsset:
        """
        FIXED: Refreshes only market-dependent values (current price, unrealized P&L).
        It no longer calculates realized P&L, which is now handled exclusively
        by recalculate_asset_state to prevent redundancy.
        """
        if portfolio_asset.quantity <= 0:
            return portfolio_asset

        try:
            asset = self.db.query(Asset).filter(Asset.id == portfolio_asset.asset_id).first()
            if not asset:
                return portfolio_asset

            current_price = await self.market_data_service.get_current_price(symbol=asset.symbol)
            last_trading_day_price = await self.market_data_service.get_yesterdays_close(symbol=asset.symbol)

            if current_price:
                current_value = float(current_price) * float(portfolio_asset.quantity)
                portfolio_asset.current_value = Decimal(str(current_value))

                cost_basis_total = float(portfolio_asset.cost_basis_total)
                unrealized_pnl = current_value - cost_basis_total
                portfolio_asset.unrealized_pnl = Decimal(str(unrealized_pnl))

                if cost_basis_total > 0:
                    pnl_percent = (unrealized_pnl / cost_basis_total) * 100
                    portfolio_asset.unrealized_pnl_percent = Decimal(str(pnl_percent))
                else:
                    portfolio_asset.unrealized_pnl_percent = Decimal("0")

                if last_trading_day_price:
                    previous_day_value = float(last_trading_day_price) * float(portfolio_asset.quantity)
                    today_pnl_value = current_value - previous_day_value
                    portfolio_asset.today_pnl = Decimal(str(today_pnl_value))

                    if previous_day_value > 0:
                        today_pnl_percent = (today_pnl_value / previous_day_value) * 100
                        portfolio_asset.today_pnl_percent = Decimal(str(today_pnl_percent))
                    else:
                        portfolio_asset.today_pnl_percent = Decimal("0")
                else:
                    portfolio_asset.today_pnl = Decimal("0")
                    portfolio_asset.today_pnl_percent = Decimal("0")
            else:
                portfolio_asset.current_value = None
                portfolio_asset.unrealized_pnl = None
                portfolio_asset.unrealized_pnl_percent = None
                portfolio_asset.today_pnl = None
                portfolio_asset.today_pnl_percent = None

        except Exception as e:
            print(f"Error refreshing market data for asset {portfolio_asset.asset_id}: {e}")

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
                    today_pnl_value = current_value - previous_day_value
                    portfolio_asset.today_pnl = Decimal(str(today_pnl_value))

                    if previous_day_value > 0:
                        today_pnl_percent = (
                                                    today_pnl_value / previous_day_value
                                            ) * 100
                        portfolio_asset.today_pnl_percent = Decimal(
                            str(today_pnl_percent)
                        )
                    else:
                        portfolio_asset.today_pnl_percent = Decimal("0")
                else:
                    # Cannot calculate today's P&L without yesterday's close
                    portfolio_asset.today_pnl = Decimal("0")
                    portfolio_asset.today_pnl_percent = Decimal("0")

            else:
                # If we can't get current price, keep existing values or set to None
                portfolio_asset.current_value = None
                portfolio_asset.unrealized_pnl = None
                portfolio_asset.unrealized_pnl_percent = None
                portfolio_asset.today_pnl = None
                portfolio_asset.today_pnl_percent = None

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

        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        update_data = asset_data.dict(exclude_unset=True)
        # This method should generally be avoided in favor of creating new transactions.
        # If used, it's a manual override.
        for field, value in update_data.items():
            setattr(portfolio_asset, field, value)

        if asset_data.current_value is None and asset_data.unrealized_pnl is None:
            portfolio_asset = await self._refresh_asset_market_data(portfolio_asset)

        self.db.commit()
        self.db.refresh(portfolio_asset)
        return portfolio_asset

    def remove_asset_from_portfolio(
            self, portfolio_id: int, asset_id: int, user_id: int
    ) -> bool:
        """
        Remove an asset and all its transactions from a portfolio.
        This is a hard delete for a specific holding.
        """
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        # Delete associated transactions first
        self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset_id
        ).delete(synchronize_session=False)

        # Delete the portfolio asset summary
        self.db.query(PortfolioAsset).filter(
            PortfolioAsset.portfolio_id == portfolio_id,
            PortfolioAsset.asset_id == asset_id
        ).delete(synchronize_session=False)

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

        portfolio_assets_with_info = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        symbols = [asset.symbol for pa, asset in portfolio_assets_with_info]
        market_prices = await self.market_data_service.get_current_prices(symbols)

        result = []
        for portfolio_asset, asset_info in portfolio_assets_with_info:
            current_price = market_prices.get(asset_info.symbol)
            current_value = None
            unrealized_pnl = None
            unrealized_pnl_percent = None

            if current_price:
                current_value = current_price * portfolio_asset.quantity
                unrealized_pnl = current_value - portfolio_asset.cost_basis_total
                if portfolio_asset.cost_basis_total > 0:
                    unrealized_pnl_percent = (unrealized_pnl / portfolio_asset.cost_basis_total) * 100

            asset_details = PortfolioAssetWithDetails(
                id=portfolio_asset.id,
                portfolio_id=portfolio_asset.portfolio_id,
                asset_id=portfolio_asset.asset_id,
                quantity=portfolio_asset.quantity,
                cost_basis=portfolio_asset.cost_basis,
                cost_basis_total=portfolio_asset.cost_basis_total,
                current_value=current_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                realized_pnl=portfolio_asset.realized_pnl,
                realized_pnl_percent=portfolio_asset.realized_pnl_percent,
                last_updated=portfolio_asset.last_updated,
                symbol=asset_info.symbol,
                asset_name=asset_info.name,
                market_value=current_value,
                total_return=unrealized_pnl,
                total_return_percent=unrealized_pnl_percent,
            )
            result.append(asset_details)

        return result

    # Transaction Management
    async def add_transaction(
            self, portfolio_id: int, transaction_data: TransactionCreate, user_id: int
    ) -> Optional[Transaction]:
        """Add a transaction and recalculate the corresponding asset's state."""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        transaction_data.total_amount = transaction_data.quantity * transaction_data.price
        transaction = Transaction(**transaction_data.dict())
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        await self.recalculate_asset_state(portfolio_id, transaction.asset_id)
        return transaction

    async def update_transaction(
            self, transaction_id: int, transaction_data: TransactionUpdate, user_id: int
    ) -> Optional[Transaction]:
        """Update a transaction and recalculate the corresponding asset's state."""
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return None

        asset_id_to_recalculate = transaction.asset_id
        portfolio_id_to_recalculate = transaction.portfolio_id

        update_data = transaction_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(transaction, field, value)

        if 'quantity' in update_data or 'price' in update_data:
            transaction.total_amount = transaction.quantity * transaction.price

        self.db.commit()
        self.db.refresh(transaction)

        await self.recalculate_asset_state(
            portfolio_id_to_recalculate, asset_id_to_recalculate
        )
        return transaction

    async def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """Delete a transaction and recalculate the corresponding asset's state."""
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return False

        portfolio_id = transaction.portfolio_id
        asset_id = transaction.asset_id

        self.db.delete(transaction)
        self.db.commit()

        await self.recalculate_asset_state(portfolio_id, asset_id)
        return True

    def get_portfolio_transactions(
            self, portfolio_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Get transactions for a portfolio, ensuring user ownership."""
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
        """Get a specific transaction, ensuring user ownership."""
        transaction = (
            self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if transaction:
            portfolio = self.get_portfolio(transaction.portfolio_id, user_id)
            if not portfolio:
                return None
        return transaction

    async def get_portfolio_summary(
            self, portfolio_id: int, user_id: int
    ) -> PortfolioSummary:
        """
        OPTIMIZED & REVISED: Get comprehensive portfolio summary with more robust
        fallback logic to handle market data failures gracefully.
        """
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return PortfolioSummary()

        # 1. Fetch all assets and their info in ONE database query
        portfolio_assets_with_info = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        if not portfolio_assets_with_info:
            return PortfolioSummary(
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                currency=portfolio.currency,
                total_assets=0,
                total_cost_basis=0.0,
                total_current_value=0.0,
                today_pnl=0.0,
                today_pnl_percent=0.0,
                total_unrealized_pnl=0.0,
                total_unrealized_pnl_percent=0.0,
                last_updated=portfolio.updated_at,
                recent_transactions=0,
                is_active=portfolio.is_active,
                is_public=portfolio.is_public
            )

        # 2. Collect symbols for batch API calls
        symbols = [asset.symbol for pa, asset in portfolio_assets_with_info]

        # 3. Concurrently fetch today's and yesterday's market data
        current_prices, yesterdays_prices = await asyncio.gather(
            self.market_data_service.get_current_prices(symbols),
            self.market_data_service.get_yesterdays_closes(symbols)
        )

        # 4. Calculate totals with explicit variable names for clarity
        total_cost_basis = Decimal("0")
        total_market_value_current = Decimal("0")
        total_market_value_previous = Decimal("0")

        for portfolio_asset, asset_info in portfolio_assets_with_info:
            total_cost_basis += portfolio_asset.cost_basis_total

            current_price = current_prices.get(asset_info.symbol)
            yesterday_price = yesterdays_prices.get(asset_info.symbol)

            # --- Step 4a: Calculate the current market value ---
            # Fallback is cost basis. This is for displaying total portfolio worth.
            if current_price is not None:
                total_market_value_current += current_price * portfolio_asset.quantity
            else:
                total_market_value_current += portfolio_asset.cost_basis_total

            # --- Step 4b: Calculate the previous day's market value ---
            # This has a 2-step fallback to prevent matching the cost basis.
            if yesterday_price is not None:
                # Best case: Use yesterday's actual closing price.
                total_market_value_previous += yesterday_price * portfolio_asset.quantity
            elif current_price is not None:
                # Fallback 1: Use today's price. This assumes 0 change for the day for this asset.
                total_market_value_previous += current_price * portfolio_asset.quantity
            else:
                # Fallback 2 (Last Resort): Use cost basis. This only happens if BOTH prices are unavailable.
                total_market_value_previous += portfolio_asset.cost_basis_total

        # 5. Convert to float and calculate final P&L metrics
        total_current_value_f = float(total_market_value_current)
        total_cost_basis_f = float(total_cost_basis)
        total_previous_day_value_f = float(total_market_value_previous)

        # --- UNREALIZED P&L (Current Value vs. Cost) ---
        total_unrealized_pnl = total_current_value_f - total_cost_basis_f
        total_unrealized_pnl_percent = (
            (total_unrealized_pnl / total_cost_basis_f * 100) if total_cost_basis_f > 0 else 0
        )

        # --- TODAY'S P&L (Current Value vs. Yesterday's Value) ---
        total_today_pnl = total_current_value_f - total_previous_day_value_f
        total_today_pnl_percent = (
            (total_today_pnl / total_previous_day_value_f * 100) if total_previous_day_value_f > 0 else 0
        )

        # 6. Fetch recent transactions
        recent_transactions_count = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id
        ).count()

        # 7. Return the complete summary object
        return PortfolioSummary(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            currency=portfolio.currency,
            total_assets=len(portfolio_assets_with_info),
            total_cost_basis=round(total_cost_basis_f, 2),
            total_current_value=round(total_current_value_f, 2),
            today_pnl=round(total_today_pnl, 2),
            today_pnl_percent=round(total_today_pnl_percent, 2),
            total_unrealized_pnl=round(total_unrealized_pnl, 2),
            total_unrealized_pnl_percent=round(total_unrealized_pnl_percent, 2),
            last_updated=portfolio.updated_at,
            recent_transactions=recent_transactions_count,
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
        """
        OPTIMIZED & FIXED: Fetches all asset and market data concurrently for performance.
        """
        # 1. Fetch all assets and their info in ONE database query using a JOIN.
        portfolio_assets_with_info = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        if not portfolio_assets_with_info:
            return []

        # 2. Collect all symbols for batch API calls.
        symbols = [asset.symbol for pa, asset in portfolio_assets_with_info]

        # 3. Concurrently fetch today's and yesterday's market data.
        current_prices, yesterdays_prices = await asyncio.gather(
            self.market_data_service.get_current_prices(symbols),
            self.market_data_service.get_yesterdays_closes(symbols)
        )

        # 4. Build the response with all required fields calculated in the loop.
        holdings = []
        for portfolio_asset, asset_info in portfolio_assets_with_info:
            current_price = current_prices.get(asset_info.symbol)
            yesterday_price = yesterdays_prices.get(asset_info.symbol)

            # Initialize all calculated fields
            current_value = None
            unrealized_pnl = None
            unrealized_pnl_percent = None
            today_pnl = None
            today_pnl_percent = None

            if current_price is not None and portfolio_asset.quantity > 0:
                current_value = current_price * portfolio_asset.quantity
                unrealized_pnl = current_value - portfolio_asset.cost_basis_total
                if portfolio_asset.cost_basis_total > 0:
                    unrealized_pnl_percent = (unrealized_pnl / portfolio_asset.cost_basis_total) * 100

                # Calculate today's P&L for the individual holding
                if yesterday_price:
                    previous_day_value = yesterday_price * portfolio_asset.quantity
                    today_pnl = current_value - previous_day_value
                    if previous_day_value > 0:
                        today_pnl_percent = (today_pnl / previous_day_value) * 100

            # Create the holding object with all required fields
            holding = PortfolioHolding(
                asset_id=portfolio_asset.asset_id,
                symbol=asset_info.symbol,
                name=asset_info.name,
                quantity=float(portfolio_asset.quantity),
                cost_basis=float(portfolio_asset.cost_basis),
                cost_basis_total=float(portfolio_asset.cost_basis_total),
                current_value=float(current_value) if current_value is not None else None,
                unrealized_pnl=float(unrealized_pnl) if unrealized_pnl is not None else None,
                unrealized_pnl_percent=float(unrealized_pnl_percent) if unrealized_pnl_percent is not None else None,
                today_pnl=float(today_pnl) if today_pnl is not None else 0.0,
                today_pnl_percent=float(today_pnl_percent) if today_pnl_percent is not None else 0.0,
                realized_pnl=float(portfolio_asset.realized_pnl),
                realized_pnl_percent=float(
                    portfolio_asset.realized_pnl_percent
                ) if portfolio_asset.realized_pnl_percent is not None else None,
                last_updated=portfolio_asset.last_updated,
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
        """
        OPTIMIZED: Refreshes portfolio values using concurrent API calls.
        """
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        portfolio_assets_with_info = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id, PortfolioAsset.quantity > 0)
            .all()
        )

        if not portfolio_assets_with_info:
            return False  # Nothing to refresh

        symbols = [asset.symbol for pa, asset in portfolio_assets_with_info]
        market_prices = await self.market_data_service.get_current_prices(symbols)

        for portfolio_asset, asset_info in portfolio_assets_with_info:
            current_price = market_prices.get(asset_info.symbol)
            if current_price:
                current_value = current_price * portfolio_asset.quantity
                unrealized_pnl = current_value - portfolio_asset.cost_basis_total

                portfolio_asset.current_value = current_value
                portfolio_asset.unrealized_pnl = unrealized_pnl

                if portfolio_asset.cost_basis_total > 0:
                    portfolio_asset.unrealized_pnl_percent = (unrealized_pnl / portfolio_asset.cost_basis_total) * 100
                else:
                    portfolio_asset.unrealized_pnl_percent = Decimal("0")

        self.db.commit()
        return True

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

    async def recalculate_asset_state(
            self, portfolio_id: int, asset_id: int
    ) -> Optional[PortfolioAsset]:
        """
        Recalculates an asset's complete state from its transaction history.
        This is the single source of truth for quantity, cost basis, and realized P&L.
        """
        buy_first_sort_order = case(
            (Transaction.transaction_type == TransactionType.BUY, 1),
            (Transaction.transaction_type == TransactionType.SELL, 2),
            else_=3,
        )
        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.asset_id == asset_id,
            )
            .order_by(Transaction.transaction_date.asc(), buy_first_sort_order.asc())
            .all()
        )

        buy_lots = []
        realized_pnl = Decimal("0")

        for tx in transactions:
            if tx.transaction_type == TransactionType.BUY:
                buy_lots.append({"quantity": tx.quantity, "total_amount": tx.total_amount})
            elif tx.transaction_type == TransactionType.SELL:
                sell_quantity = tx.quantity
                sell_proceeds = tx.total_amount
                cost_of_goods_sold = Decimal("0")

                while sell_quantity > 0 and buy_lots:
                    oldest_lot = buy_lots[0]
                    quantity_to_sell_from_lot = min(sell_quantity, oldest_lot["quantity"])

                    if oldest_lot["quantity"] > 0:
                        cost_basis_portion = (quantity_to_sell_from_lot / oldest_lot["quantity"]) * oldest_lot[
                            "total_amount"]
                        cost_of_goods_sold += cost_basis_portion
                        oldest_lot["quantity"] -= quantity_to_sell_from_lot
                        oldest_lot["total_amount"] -= cost_basis_portion

                    sell_quantity -= quantity_to_sell_from_lot

                    if oldest_lot["quantity"] <= 0:
                        buy_lots.pop(0)

                realized_pnl += (sell_proceeds - cost_of_goods_sold)

        current_quantity = sum(lot["quantity"] for lot in buy_lots)
        total_cost = sum(lot["total_amount"] for lot in buy_lots)

        portfolio_asset = self.db.query(PortfolioAsset).filter_by(portfolio_id=portfolio_id, asset_id=asset_id).first()

        if not transactions:
            if portfolio_asset:
                self.db.delete(portfolio_asset)
                self.db.commit()
            return None

        if not portfolio_asset:
            portfolio_asset = PortfolioAsset(portfolio_id=portfolio_id, asset_id=asset_id)
            self.db.add(portfolio_asset)

        portfolio_asset.quantity = current_quantity
        portfolio_asset.cost_basis_total = total_cost
        portfolio_asset.cost_basis = total_cost / current_quantity if current_quantity > 0 else Decimal("0")
        portfolio_asset.realized_pnl = realized_pnl

        if current_quantity > 0:
            try:
                asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
                if asset:
                    current_price = await self.market_data_service.get_current_price(asset.symbol)
                    if current_price:
                        current_value = current_price * portfolio_asset.quantity
                        unrealized_pnl = current_value - portfolio_asset.cost_basis_total
                        portfolio_asset.current_value = current_value
                        portfolio_asset.unrealized_pnl = unrealized_pnl
                        if portfolio_asset.cost_basis_total > 0:
                            portfolio_asset.unrealized_pnl_percent = (
                                                                             unrealized_pnl /
                                                                             portfolio_asset.cost_basis_total) * 100
                        else:
                            portfolio_asset.unrealized_pnl_percent = Decimal("0")
            except Exception as e:
                print(f"Error fetching market data for asset {asset_id}: {e}")
                portfolio_asset.current_value = None
                portfolio_asset.unrealized_pnl = None
                portfolio_asset.unrealized_pnl_percent = None
        else:
            portfolio_asset.current_value = Decimal("0")
            portfolio_asset.unrealized_pnl = Decimal("0")
            portfolio_asset.unrealized_pnl_percent = Decimal("0")

        self.db.commit()
        self.db.refresh(portfolio_asset)
        return portfolio_asset
