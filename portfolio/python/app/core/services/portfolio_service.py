import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import case, desc
from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from core.domain.fx import (
    MissingFxError,
    canonical_currency,
    convert_amount,
    convert_trades,
)
from core.domain.positions import (
    OversellError,
    compute_position,
    day_change,
    to_trades,
)
from core.schemas.portfolio import (
    CurrencyTotals,
    PortfolioAssetCreate,
    PortfolioAssetWithDetails,
    PortfolioCreate,
    PortfolioHolding,
    PortfolioStatistics,
    PortfolioSummary,
    PortfolioUpdate,
    TransactionCreate,
    TransactionUpdate,
)
from core.services.fx import load_rates
from core.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

__all__ = ["OversellError", "PortfolioService", "compute_position"]


def _opt_float(value) -> Optional[float]:
    return float(value) if value is not None else None


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
        transaction_date = getattr(asset_data, "transaction_date", date.today())

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
            Transaction.portfolio_id == portfolio_id, Transaction.asset_id == asset_id
        ).delete(synchronize_session=False)

        # Delete the portfolio asset summary
        self.db.query(PortfolioAsset).filter(
            PortfolioAsset.portfolio_id == portfolio_id,
            PortfolioAsset.asset_id == asset_id,
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
        rates = await load_rates(
            self.market_data_service,
            portfolio.currency,
            [asset.currency for _, asset in portfolio_assets_with_info],
            strict=False,
        )

        result = []
        for portfolio_asset, asset_info in portfolio_assets_with_info:
            current_price = market_prices.get(asset_info.symbol)
            if current_price is not None:
                current_price = self._converted(
                    current_price,
                    asset_info.currency,
                    portfolio.currency,
                    date.today(),
                    rates,
                )
            current_value = None
            unrealized_pnl = None
            unrealized_pnl_percent = None

            if current_price is not None:
                current_value = current_price * portfolio_asset.quantity
                unrealized_pnl = current_value - portfolio_asset.cost_basis_total
                if portfolio_asset.cost_basis_total > 0:
                    unrealized_pnl_percent = (
                        unrealized_pnl / portfolio_asset.cost_basis_total
                    ) * 100

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
    def _get_owned_asset(self, asset_id: int, user_id: int) -> Optional[Asset]:
        return (
            self.db.query(Asset)
            .filter(Asset.id == asset_id, Asset.user_id == user_id)
            .first()
        )

    async def add_transaction(
        self, portfolio_id: int, transaction_data: TransactionCreate, user_id: int
    ) -> Optional[Transaction]:
        """
        Add a transaction and recalculate the corresponding asset's state atomically.

        The portfolio comes from `portfolio_id` (never the request body), both the
        portfolio and the asset must belong to the user, and `total_amount` is always
        computed server-side. Raises OversellError if the sell exceeds holdings.
        """
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        asset = self._get_owned_asset(transaction_data.asset_id, user_id)
        if not asset:
            return None
        asset_major, _ = canonical_currency(asset.currency)
        portfolio_major, _ = canonical_currency(portfolio.currency)
        requested_major, _ = canonical_currency(
            transaction_data.currency or asset.currency
        )
        # Cash the user typed in the portfolio currency stays there. A foreign
        # listing otherwise records its own quote currency, which valuation converts.
        if asset_major == portfolio_major or requested_major == portfolio_major:
            cash_currency = portfolio_major
        else:
            cash_currency = asset_major

        values = transaction_data.dict()
        values["portfolio_id"] = portfolio_id
        values["currency"] = cash_currency
        values["total_amount"] = Transaction.compute_total_amount(
            transaction_data.transaction_type,
            transaction_data.quantity,
            transaction_data.price,
            transaction_data.fees,
            transaction_data.taxes,
        )
        transaction = Transaction(**values)

        try:
            self.db.add(transaction)
            self.db.flush()
            await self.recalculate_asset_state(
                portfolio_id, transaction.asset_id, commit=False
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(transaction)
        return transaction

    async def update_transaction(
        self, transaction_id: int, transaction_data: TransactionUpdate, user_id: int
    ) -> Optional[Transaction]:
        """Update a transaction and recalculate the corresponding asset's state atomically."""
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return None

        update_data = transaction_data.dict(exclude_unset=True)
        # total_amount is derived; ignore any client-supplied value
        update_data.pop("total_amount", None)
        for field, value in update_data.items():
            setattr(transaction, field, value)

        transaction.total_amount = Transaction.compute_total_amount(
            transaction.transaction_type,
            transaction.quantity,
            transaction.price,
            transaction.fees,
            transaction.taxes,
        )

        try:
            self.db.flush()
            await self.recalculate_asset_state(
                transaction.portfolio_id, transaction.asset_id, commit=False
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(transaction)
        return transaction

    async def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """Delete a transaction and recalculate the corresponding asset's state atomically."""
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return False

        portfolio_id = transaction.portfolio_id
        asset_id = transaction.asset_id

        try:
            self.db.delete(transaction)
            self.db.flush()
            await self.recalculate_asset_state(portfolio_id, asset_id, commit=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
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
                is_public=portfolio.is_public,
            )

        all_rows = await self._holding_rows(portfolio_id)
        rows = [r for r in all_rows if r[0].quantity > 0]
        priced = [r for r in rows if r[0].current_value is not None]
        total_cost_basis_f = sum(h.cost_basis_total for h, _, _ in rows)
        total_current_value_f = sum(h.current_value for h, _, _ in priced)
        priced_cost = sum(h.cost_basis_total for h, _, _ in priced)
        total_unrealized_pnl = total_current_value_f - priced_cost
        total_unrealized_pnl_percent = (
            total_unrealized_pnl / priced_cost * 100 if priced_cost > 0 else 0
        )
        today_rows = [(pnl, base) for _, pnl, base in rows if base]
        total_today_pnl = float(sum((pnl for pnl, _ in today_rows), Decimal(0)))
        today_base = float(sum((base for _, base in today_rows), Decimal(0)))
        total_today_pnl_percent = (
            total_today_pnl / today_base * 100 if today_base > 0 else 0
        )

        # 6. Fetch recent transactions
        recent_transactions_count = (
            self.db.query(Transaction)
            .filter(Transaction.portfolio_id == portfolio_id)
            .count()
        )

        # 7. Return the complete summary object
        return PortfolioSummary(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            currency=portfolio.currency,
            total_assets=len(rows),
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
            total_realized_pnl=round(
                sum(h.realized_pnl or 0 for h, _, _ in all_rows), 2
            ),
            missing_prices=[h.symbol for h, _, _ in rows if h.current_value is None],
        )

    def _converted(self, amount, currency, portfolio_currency, day, rates):
        if amount is None:
            return None
        try:
            return convert_amount(amount, currency, portfolio_currency, day, rates)
        except MissingFxError:
            return None

    async def _holding_rows(
        self, portfolio_id: int
    ) -> List[Tuple[PortfolioHolding, Optional[Decimal], Optional[Decimal]]]:
        """Each position with live value, P&L and (today's P&L, capital it was earned on)."""
        portfolio_assets_with_info = (
            self.db.query(PortfolioAsset, Asset)
            .join(Asset, PortfolioAsset.asset_id == Asset.id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )
        if not portfolio_assets_with_info:
            return []

        symbols = [asset.symbol for pa, asset in portfolio_assets_with_info]
        current_prices, yesterdays_prices = await asyncio.gather(
            self.market_data_service.get_current_prices(symbols),
            self.market_data_service.get_yesterdays_closes(symbols),
        )
        portfolio = (
            self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        )
        portfolio_currency = portfolio.currency if portfolio else "USD"
        today = date.today()
        yesterday = today - timedelta(days=1)
        session_start = today - timedelta(days=max(0, today.weekday() - 4))
        trades_today = defaultdict(list)
        for tx in (
            self.db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.transaction_date
                >= datetime.combine(session_start, time.min, tzinfo=timezone.utc),
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .all()
        ):
            trades_today[tx.asset_id].append(tx)

        codes = [asset.currency for _, asset in portfolio_assets_with_info]
        for txs in trades_today.values():
            codes.extend(tx.currency for tx in txs)
        rates = await load_rates(
            self.market_data_service, portfolio_currency, codes, strict=False
        )

        rows = []
        for portfolio_asset, asset_info in portfolio_assets_with_info:
            quantity = portfolio_asset.quantity
            price = self._converted(
                current_prices.get(asset_info.symbol),
                asset_info.currency,
                portfolio_currency,
                today,
                rates,
            )
            prev_close = self._converted(
                yesterdays_prices.get(asset_info.symbol),
                asset_info.currency,
                portfolio_currency,
                yesterday,
                rates,
            )
            current_value = unrealized_pnl = unrealized_pnl_percent = None
            today_pnl = today_base = None

            if price is not None and quantity > 0:
                current_value = price * quantity
                unrealized_pnl = current_value - portfolio_asset.cost_basis_total
                if portfolio_asset.cost_basis_total > 0:
                    unrealized_pnl_percent = (
                        unrealized_pnl / portfolio_asset.cost_basis_total * 100
                    )
                if prev_close:
                    priced_trades = []
                    convertible = True
                    for tx in trades_today.get(portfolio_asset.asset_id, []):
                        trade_price = self._converted(
                            tx.price,
                            tx.currency,
                            portfolio_currency,
                            tx.transaction_date,
                            rates,
                        )
                        if trade_price is None:
                            convertible = False
                            break
                        priced_trades.append(
                            SimpleNamespace(
                                quantity=tx.quantity,
                                transaction_type=tx.transaction_type,
                                price=trade_price,
                            )
                        )
                    if convertible:
                        today_pnl, today_base = day_change(
                            quantity, prev_close, price, priced_trades
                        )

            holding = PortfolioHolding(
                asset_id=portfolio_asset.asset_id,
                symbol=asset_info.symbol,
                name=asset_info.name,
                quantity=float(quantity),
                cost_basis=float(portfolio_asset.cost_basis),
                cost_basis_total=float(portfolio_asset.cost_basis_total),
                current_value=_opt_float(current_value),
                unrealized_pnl=_opt_float(unrealized_pnl),
                unrealized_pnl_percent=_opt_float(unrealized_pnl_percent),
                today_pnl=float(today_pnl) if today_pnl is not None else 0.0,
                today_pnl_percent=float(today_pnl / today_base * 100)
                if today_base
                else 0.0,
                current_price=_opt_float(price),
                realized_pnl=float(portfolio_asset.realized_pnl),
                realized_pnl_percent=_opt_float(portfolio_asset.realized_pnl_percent),
                last_updated=portfolio_asset.last_updated,
            )
            rows.append((holding, today_pnl, today_base))

        priced_total = sum(h.current_value for h, _, _ in rows if h.current_value)
        for holding, _, _ in rows:
            if holding.current_value is not None and priced_total > 0:
                holding.weight_percent = holding.current_value / priced_total * 100
        return rows

    async def get_portfolio_holdings(
        self,
        portfolio_id: int,
    ) -> List[PortfolioHolding]:
        """
        Live holdings of a portfolio. Does NOT check ownership: callers must verify
        the portfolio belongs to the user first (see get_user_portfolio_holdings).
        """
        return [holding for holding, _, _ in await self._holding_rows(portfolio_id)]

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

    async def get_portfolio_statistics(self, user_id: int) -> PortfolioStatistics:
        """Totals across the user's active portfolios, per currency, from live holdings."""
        portfolios = self.get_user_portfolios(user_id, include_inactive=True)
        sums: Dict[str, Dict[str, Any]] = {}
        missing: List[str] = []
        for portfolio in portfolios:
            if not portfolio.is_active:
                continue
            bucket = sums.setdefault(
                portfolio.currency,
                {
                    "portfolios": 0,
                    "assets": 0,
                    "value": Decimal(0),
                    "pnl": Decimal(0),
                    "base": Decimal(0),
                },
            )
            bucket["portfolios"] += 1
            for holding, pnl, base in await self._holding_rows(portfolio.id):
                if holding.quantity <= 0:
                    continue
                bucket["assets"] += 1
                if holding.current_value is None:
                    missing.append(holding.symbol)
                    continue
                bucket["value"] += Decimal(str(holding.current_value))
                if base:
                    bucket["pnl"] += pnl
                    bucket["base"] += base

        totals = [
            CurrencyTotals(
                currency=currency,
                portfolios=b["portfolios"],
                total_assets=b["assets"],
                total_value=round(float(b["value"]), 2),
                today_pnl=round(float(b["pnl"]), 2),
                today_pnl_percent=round(float(b["pnl"] / b["base"] * 100), 2)
                if b["base"]
                else 0.0,
            )
            for currency, b in sorted(sums.items(), key=lambda kv: -kv[1]["value"])
        ]
        single = totals[0] if len(totals) == 1 else None
        return PortfolioStatistics(
            total_portfolios=len(portfolios),
            active_portfolios=sum(t.portfolios for t in totals),
            total_assets=sum(t.total_assets for t in totals),
            totals=totals,
            total_value=single.total_value if single else None,
            currency=single.currency if single else None,
            today_pnl=single.today_pnl if single else None,
            today_pnl_percent=single.today_pnl_percent if single else None,
            missing_prices=sorted(set(missing)),
        )

    async def refresh_portfolio_values(self, portfolio_id: int, user_id: int) -> bool:
        """
        OPTIMIZED: Refreshes portfolio values using concurrent API calls.
        """
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        asset_ids = [
            asset_id
            for (asset_id,) in self.db.query(PortfolioAsset.asset_id)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        ]
        if not asset_ids:
            return False

        # Rebuild from transactions so splits since the last trade are applied
        for asset_id in asset_ids:
            await self.recalculate_asset_state(portfolio_id, asset_id, commit=False)
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

    async def get_user_portfolio_holdings(
        self, portfolio_id: int, user_id: int
    ) -> Optional[List[PortfolioHolding]]:
        """Holdings for a portfolio the user owns, or None if it isn't theirs."""
        if not self.get_portfolio(portfolio_id, user_id):
            return None
        return await self.get_portfolio_holdings(portfolio_id)

    async def recalculate_asset_state(
        self, portfolio_id: int, asset_id: int, commit: bool = True
    ) -> Optional[PortfolioAsset]:
        """
        Recalculates an asset's complete state from its transaction history.
        This is the single source of truth for quantity, cost basis, and realized P&L.

        The price is fetched before any read/write so the rest runs without an
        await: concurrent requests for the same asset can't interleave between the
        PortfolioAsset lookup and its insert (unique portfolio_id+asset_id).
        """
        price_error = None
        current_price = None
        splits = []
        asset = None
        try:
            asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                current_price = await self.market_data_service.get_current_price(
                    asset.symbol
                )
                history = await self.market_data_service.get_daily_history(asset.symbol)
                if history is not None:
                    splits = [
                        (day.date(), Decimal(str(ratio)))
                        for day, ratio in history["splits"].items()
                    ]
        except Exception as e:
            price_error = e

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
            .order_by(
                Transaction.transaction_date.asc(),
                buy_first_sort_order.asc(),
                Transaction.id.asc(),
            )
            .all()
        )
        portfolio_row = (
            self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        )
        portfolio_currency = portfolio_row.currency if portfolio_row else "USD"
        raw_trades = to_trades(transactions, {asset_id: splits})
        try:
            rates = await load_rates(
                self.market_data_service,
                portfolio_currency,
                [tx.currency for tx in transactions]
                + ([asset.currency] if asset is not None else []),
            )
            position = compute_position(
                convert_trades(
                    raw_trades,
                    {tx.id: tx.currency for tx in transactions},
                    portfolio_currency,
                    rates,
                )
            )
            if current_price is not None and asset is not None:
                current_price = float(
                    convert_amount(
                        current_price,
                        asset.currency,
                        portfolio_currency,
                        date.today(),
                        rates,
                    )
                )
        except MissingFxError as exc:
            logger.warning("No FX for asset %s: %s", asset_id, exc)
            position = compute_position(raw_trades)
            current_price = None
            price_error = exc
        current_quantity = position["quantity"]
        total_cost = position["cost_basis_total"]

        portfolio_asset = (
            self.db.query(PortfolioAsset)
            .filter_by(portfolio_id=portfolio_id, asset_id=asset_id)
            .first()
        )

        if not transactions:
            if portfolio_asset:
                self.db.delete(portfolio_asset)
                if commit:
                    self.db.commit()
            return None

        if not portfolio_asset:
            portfolio_asset = PortfolioAsset(
                portfolio_id=portfolio_id, asset_id=asset_id
            )
            self.db.add(portfolio_asset)

        portfolio_asset.quantity = current_quantity
        portfolio_asset.cost_basis_total = total_cost
        portfolio_asset.cost_basis = (
            total_cost / current_quantity if current_quantity > 0 else Decimal("0")
        )
        portfolio_asset.realized_pnl = position["realized_pnl"]
        portfolio_asset.realized_pnl_percent = (
            position["realized_pnl"] / position["cost_of_sold"] * 100
            if position["cost_of_sold"] > 0
            else Decimal("0")
        )

        if current_quantity > 0:
            if price_error is not None:
                logger.warning(
                    "Error fetching market data for asset %s: %s",
                    asset_id,
                    price_error,
                )
                portfolio_asset.current_value = None
                portfolio_asset.unrealized_pnl = None
                portfolio_asset.unrealized_pnl_percent = None
            elif current_price:
                # Prices come back as float; convert via str to avoid binary noise
                current_value = Decimal(str(current_price)) * portfolio_asset.quantity
                unrealized_pnl = current_value - portfolio_asset.cost_basis_total
                portfolio_asset.current_value = current_value
                portfolio_asset.unrealized_pnl = unrealized_pnl
                if portfolio_asset.cost_basis_total > 0:
                    portfolio_asset.unrealized_pnl_percent = (
                        unrealized_pnl / portfolio_asset.cost_basis_total
                    ) * 100
                else:
                    portfolio_asset.unrealized_pnl_percent = Decimal("0")
        else:
            portfolio_asset.current_value = Decimal("0")
            portfolio_asset.unrealized_pnl = Decimal("0")
            portfolio_asset.unrealized_pnl_percent = Decimal("0")

        if commit:
            self.db.commit()
            self.db.refresh(portfolio_asset)
        return portfolio_asset
