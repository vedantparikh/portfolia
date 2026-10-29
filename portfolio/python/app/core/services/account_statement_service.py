import base64
import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, List, Tuple

from sqlalchemy.orm import Session

from core.database.models import Asset, Transaction, TransactionType
from core.domain.fx import canonical_currency
from core.errors import (
    DomainError,
    NotFoundError,
    public_message,
)
from core.schemas.account_statements import (
    AccountStatementProvider,
    BulkCreateSummary,
    BulkTransactionItem,
    CreatedTransaction,
    ImportedCheckRow,
    ParsedData,
    SupportedFormat,
)
from core.services.asset_factory import asset_from_ticker_info
from core.services.market_data_service import MarketDataService
from core.services.parsers.portfolia import PortfoliaParser
from core.services.parsers.pytr_csv import PytrCsvParser
from core.services.parsers.trade_republic import TradeRepublicParser
from modules.portfolios.service import PortfolioService

logger = logging.getLogger(__name__)


def _number(value: Any) -> str:
    return f"{Decimal(value).normalize():f}"


def assign_source_keys(result: ParsedData) -> None:
    """Hash each row's identity (parser-given or date/type/symbol/amounts), numbering repeats."""
    seen: defaultdict[str, int] = defaultdict(int)
    for t in result.transactions:
        base = t.source_key or "|".join(
            [
                t.transaction_date,
                t.transaction_type.value,
                t.symbol or t.name,
                _number(t.quantity),
                _number(t.total_amount),
            ]
        )
        seen[base] += 1
        t.source_key = hashlib.sha256(
            f"{result.provider}|{base}#{seen[base]}".encode()
        ).hexdigest()


def _content(row: Any, isin: str | None) -> tuple:
    day = row.transaction_date
    if isinstance(day, datetime):
        day = (day.astimezone(timezone.utc) if day.tzinfo else day).date().isoformat()
    return (
        day,
        getattr(row.transaction_type, "value", row.transaction_type),
        isin,
        Decimal(row.quantity).quantize(Decimal("0.00000001")),
        Decimal(row.total_amount).quantize(Decimal("0.01")),
    )


class AccountStatementService:
    """Service for account statement parsing and processing."""

    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self.market_data = MarketDataService()
        self._parsers = {
            "trade_republic": TradeRepublicParser(),
            "pytr_csv": PytrCsvParser(),
            "portfolia": PortfoliaParser(),
        }

    def get_supported_providers(self) -> List[AccountStatementProvider]:
        """Get list of supported account statement providers."""
        return [
            AccountStatementProvider(
                id="trade_republic",
                name="Trade Republic",
                description="German neobroker",
                supported_formats=[SupportedFormat.PDF],
                logo_url="/logos/trade_republic.png",
            ),
            AccountStatementProvider(
                id="pytr_csv",
                name="Trade Republic (pytr CSV)",
                description="Full history exported with `pytr export_transactions`",
                supported_formats=[SupportedFormat.CSV],
                logo_url="/logos/trade_republic.png",
            ),
            AccountStatementProvider(
                id="portfolia",
                name="Portfolia",
                description="Portfolia app-generated transaction reports",
                supported_formats=[SupportedFormat.PDF],
                logo_url="/logos/portfolia.png",
            ),
        ]

    def parse_statement(
        self, provider_id: str, file_content: str, filename: str
    ) -> ParsedData:
        """Parse account statement PDF."""
        if provider_id not in self._parsers:
            raise DomainError(f"Unsupported provider: {provider_id}")

        try:
            pdf_content = base64.b64decode(file_content)
        except Exception as e:
            raise DomainError("The uploaded file could not be read") from e

        parser = self._parsers[provider_id]
        result = parser.parse(pdf_content)
        assign_source_keys(result)

        if filename and result.metadata:
            result.metadata.warnings.insert(0, f"Parsed from file: {filename}")

        return result

    def _find_imported(
        self, portfolio_id: int, rows: Iterable[ImportedCheckRow | BulkTransactionItem]
    ) -> Tuple[set, dict]:
        """Keys of rows already in the portfolio, and keyless older imports they match.

        A row matches by `source_key`; failing that, by date, type, ISIN, quantity and
        cash amount against a transaction imported before keys existed (each used once).
        """
        rows = [r for r in rows if r.source_key]
        keys = {r.source_key for r in rows}
        if not keys:
            return set(), {}
        imported = {
            key
            for (key,) in self.db.query(Transaction.source_key).filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.source_key.in_(keys),
            )
        }
        pending = [r for r in rows if r.source_key not in imported]
        legacy = {}
        if pending:
            candidates = defaultdict(list)
            for transaction, isin in (
                self.db.query(Transaction, Asset.isin)
                .join(Asset, Asset.id == Transaction.asset_id)
                .filter(
                    Transaction.portfolio_id == portfolio_id,
                    Transaction.source_key.is_(None),
                )
                .order_by(Transaction.id)
            ):
                candidates[_content(transaction, isin)].append(transaction)
            for row in pending:
                match = candidates.get(_content(row, row.isin))
                if match and row.source_key not in legacy:
                    legacy[row.source_key] = match.pop(0)
        return imported | set(legacy), legacy

    def imported_keys(
        self, portfolio_id: int, rows: List[ImportedCheckRow], user_id: int
    ) -> List[str]:
        if not self.portfolio_service.get_portfolio(portfolio_id, user_id):
            raise NotFoundError("Portfolio not found")
        imported, _ = self._find_imported(portfolio_id, rows)
        return sorted(imported)

    async def _asset_for_symbol(
        self,
        symbol: str,
        isin: str | None,
        user_id: int,
        assets_by_symbol: dict[str, Asset],
        unavailable_symbols: set[str],
    ) -> Asset:
        """The user's asset for a Yahoo ticker, created (unsaved until commit) if missing."""
        if symbol in assets_by_symbol:
            return assets_by_symbol[symbol]
        if symbol in unavailable_symbols:
            raise DomainError(f"No market data for {symbol}")
        ticker_data = await self.market_data.get_ticker_info(symbol)
        if not ticker_data:
            unavailable_symbols.add(symbol)
            raise DomainError(f"No market data for {symbol}")
        asset = asset_from_ticker_info(symbol, ticker_data, user_id, isin)
        self.db.add(asset)
        self.db.flush()
        assets_by_symbol[symbol] = asset
        return asset

    async def asset_for_symbol(
        self, symbol: str, isin: str | None, user_id: int
    ) -> Asset:
        """The user's asset for a Yahoo ticker, created from Yahoo info if missing; remembers the ISIN."""
        owned = {
            a.symbol.upper(): a
            for a in self.db.query(Asset).filter(Asset.user_id == user_id)
        }
        asset = await self._asset_for_symbol(
            symbol.upper(), isin, user_id, owned, set()
        )
        if isin and not asset.isin:
            asset.isin = isin
        return asset

    async def create_bulk_transactions(
        self,
        portfolio_id: int,
        transactions_data: List[BulkTransactionItem],
        user_id: int,
    ) -> Tuple[List[CreatedTransaction], BulkCreateSummary]:
        """Create multiple transactions efficiently and robustly from parsed data."""
        # 1. Verify portfolio access once at the start
        portfolio = self.portfolio_service.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise NotFoundError("Portfolio not found")

        created_transaction_models = []
        errors = []
        skipped = 0
        imported, legacy = self._find_imported(portfolio_id, transactions_data)
        for key, transaction in legacy.items():
            transaction.source_key = key
        affected_asset_ids = set()
        owned = self.db.query(Asset).filter(Asset.user_id == user_id).all()
        assets_by_id = {a.id: a for a in owned}
        assets_by_symbol = {a.symbol.upper(): a for a in owned}
        unavailable_symbols: set[str] = set()

        # 2. Prepare all transaction models and add them to the session
        for i, item in enumerate(transactions_data):
            if item.source_key and item.source_key in imported:
                skipped += 1
                continue
            if item.source_key:
                imported.add(item.source_key)
            try:
                if item.asset_id is not None:
                    asset = assets_by_id.get(item.asset_id)
                    if asset is None:
                        raise NotFoundError(f"Asset {item.asset_id} not found")
                elif item.symbol:
                    asset = await self._asset_for_symbol(
                        item.symbol.upper(),
                        item.isin,
                        user_id,
                        assets_by_symbol,
                        unavailable_symbols,
                    )
                else:
                    raise DomainError("Choose an asset or a ticker")
                cash_currency, _ = canonical_currency(
                    item.currency or portfolio.currency
                )
                if item.isin and not asset.isin:
                    asset.isin = item.isin

                transaction_type = TransactionType(
                    getattr(item.transaction_type, "value", item.transaction_type)
                )
                if transaction_type == TransactionType.DIVIDEND:
                    if item.total_amount <= 0:
                        raise DomainError("Dividend amount must be positive")
                    total_amount = item.total_amount
                else:
                    total_amount = Transaction.compute_total_amount(
                        transaction_type,
                        item.quantity,
                        item.price,
                        item.fees,
                        item.taxes,
                    )
                    if abs(total_amount - item.total_amount) <= Decimal("0.01"):
                        total_amount = item.total_amount
                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    asset_id=asset.id,
                    transaction_type=transaction_type,
                    quantity=item.quantity,
                    price=item.price,
                    total_amount=total_amount,
                    currency=cash_currency,
                    taxes=item.taxes,
                    transaction_date=datetime.strptime(
                        item.transaction_date, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc),
                    fees=item.fees,
                    notes=item.notes,
                    source_key=item.source_key,
                )
                self.db.add(transaction)
                affected_asset_ids.add(asset.id)
                created_transaction_models.append(transaction)

            except ValueError as e:
                errors.append(
                    f"Row {i + 1} ('{item.notes}'): "
                    + public_message(e, "invalid values")
                )
            except Exception:
                logger.exception("Bulk import row %s failed", i + 1)
                errors.append(f"Row {i + 1} ('{item.notes}'): could not be created")

        # 3. Insert all valid transactions and recalculate each affected asset once,
        #    in a single database transaction so holdings never drift from history
        try:
            if created_transaction_models or legacy:
                self.db.flush()
                for asset_id in affected_asset_ids:
                    await self.portfolio_service.recalculate_asset_state(
                        portfolio_id, asset_id
                    )
                self.db.flush()
        except Exception:
            self.db.rollback()
            logger.exception("Bulk import failed for portfolio %s", portfolio_id)
            return [], BulkCreateSummary(
                total_created=0,
                total_failed=len(transactions_data) - skipped,
                total_skipped=skipped,
                errors=["Import failed; no transactions were saved"] + errors,
            )

        # 5. Prepare the successful response data
        final_created_list = [
            CreatedTransaction.model_validate(tx) for tx in created_transaction_models
        ]
        summary = BulkCreateSummary(
            total_created=len(final_created_list),
            total_failed=len(errors),
            total_skipped=skipped,
            errors=errors,
        )
        return final_created_list, summary
