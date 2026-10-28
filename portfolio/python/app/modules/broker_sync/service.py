"""
Keep a portfolio in step with the Trade Republic export that Bachat refreshes.

The file is only read. Each run parses it with the pytr parser and sends every
row to bulk-create, which skips rows whose source key is already stored, so a
run only adds what is new. Splits and swaps are skipped by the parser: the
listing's Yahoo split ratios restate the old trades.

Securities Yahoo does not carry (knock-outs, warrants) are imported as assets
priced from their own fills. pytr writes a knock-out's redemption ("Tilgung") as
a Dividend row for the whole position; when the security is no longer among
Trade Republic's current positions (portfolio.csv), that row is booked as a sale
of every share at the redeemed amount, so the loss is realised on that day.
"""

import base64
import csv
import hashlib
import io
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from core.database.models import Asset, Portfolio, TransactionType, User
from core.database.models.asset import AssetType
from core.errors import DomainError
from core.schemas.account_statements import BulkTransactionItem
from core.services.account_statement_service import AccountStatementService
from core.services.isin_resolver import IsinResolver
from core.services.parsers.pytr_csv import parse_number
from core.services.trade_prices import TRADES, is_trade_priced
from modules.portfolios.service import PortfolioService

logger = logging.getLogger(__name__)

SOURCE = "pytr"
_CONFIDENT = ("existing", "matched")


def _name_key(name: str) -> str:
    return " ".join(name.casefold().split())


class PytrSyncService:
    def __init__(self, db: Session, path: Optional[str] = None):
        self.db = db
        self.path = Path(path if path is not None else settings.PYTR_EXPORT_PATH)
        self.statements = AccountStatementService(db)

    def available_for(self, user: User) -> bool:
        allowed = {u.casefold() for u in settings.PYTR_SYNC_USERS}
        return (
            bool(str(self.path))
            and str(self.path) != "."
            and user.username.casefold() in allowed
        )

    def file_info(self) -> Dict[str, Any]:
        if not self.path.is_file():
            return {"exists": False, "updated_at": None}
        stat = self.path.stat()
        return {
            "exists": True,
            "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        }

    def link(self, portfolio: Portfolio, user: User, enabled: bool) -> None:
        if enabled:
            if not self.available_for(user):
                raise DomainError("Trade Republic sync is not set up for this account")
            if (portfolio.currency or "").upper() != "EUR":
                raise DomainError(
                    "A Trade Republic account is in EUR; use an EUR portfolio"
                )
            portfolio.sync_source = SOURCE
        else:
            portfolio.sync_source = None
        portfolio.sync_digest = None

    async def map_instrument(
        self, portfolio: Portfolio, isin: str, symbol: str
    ) -> Asset:
        """Tie an ISIN from the export to a Yahoo ticker; its rows then use market prices."""
        priced = (
            self.db.query(Asset)
            .filter(Asset.user_id == portfolio.user_id, Asset.isin == isin)
            .first()
        )
        if priced is not None and is_trade_priced(priced):
            info = await self.statements.market_data.get_ticker_info(symbol.upper())
            if not info:
                raise DomainError(f"No market data for {symbol.upper()}")
            priced.symbol = symbol.upper()
            priced.price_source = None
            priced.currency = (info.get("currency") or priced.currency)[:3]
            self.db.flush()
            await PortfolioService(self.db).recalculate_asset_state(
                portfolio.id, priced.id, commit=False
            )
            portfolio.sync_digest = None
            return priced
        asset = await self.statements.asset_for_symbol(symbol, isin, portfolio.user_id)
        if asset.isin and asset.isin != isin:
            raise DomainError(f"{asset.symbol} already belongs to ISIN {asset.isin}")
        asset.isin = isin
        portfolio.sync_digest = None
        return asset

    async def sync(self, portfolio: Portfolio, force: bool = False) -> Dict[str, Any]:
        if portfolio.sync_source != SOURCE:
            raise DomainError("This portfolio is not linked to Trade Republic")
        if not self.path.is_file():
            raise DomainError(
                "The Trade Republic export is not available on this server"
            )
        content = self.path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if not force and digest == portfolio.sync_digest:
            return portfolio.sync_report or {}

        parsed = self.statements.parse_statement(
            "pytr_csv", base64.b64encode(content).decode("ascii"), self.path.name
        )
        isin_to_asset, trade_priced = await self._map_isins(
            portfolio, parsed.instruments
        )
        redemptions = self._redemptions(content)
        redeemed = {(r["isin"], r["date"], r["amount"]) for r in redemptions}
        items: List[BulkTransactionItem] = []
        for row in parsed.transactions:
            asset_id = isin_to_asset.get(row.symbol or "")
            if asset_id is None:
                continue
            if (
                row.transaction_type == TransactionType.DIVIDEND
                and (row.symbol, row.transaction_date, row.total_amount) in redeemed
            ):
                continue
            items.append(
                BulkTransactionItem(
                    transaction_date=row.transaction_date,
                    asset_id=asset_id,
                    transaction_type=row.transaction_type,
                    quantity=row.quantity,
                    price=row.price or 0,
                    total_amount=row.total_amount,
                    fees=row.fees,
                    taxes=row.taxes,
                    currency=row.currency,
                    notes=row.name,
                    source_key=row.source_key,
                )
            )
        for r in redemptions:
            asset_id = isin_to_asset.get(r["isin"])
            if asset_id is None:
                continue
            items.append(
                BulkTransactionItem(
                    transaction_date=r["date"],
                    asset_id=asset_id,
                    transaction_type=TransactionType.SELL,
                    quantity=r["shares"],
                    price=r["amount"] / r["shares"],
                    total_amount=r["amount"],
                    taxes=r["taxes"],
                    currency="EUR",
                    notes=f"{r['name']}: redeemed (Tilgung)",
                    source_key=r["source_key"],
                )
            )
        _, summary = await self.statements.create_bulk_transactions(
            portfolio.id, items, portfolio.user_id
        )
        skipped_reasons: Dict[str, int] = {}
        for row in parsed.skipped:
            skipped_reasons[row.reason] = skipped_reasons.get(row.reason, 0) + 1
        report = {
            "file_updated_at": self.file_info()["updated_at"].isoformat(),
            "created": summary.total_created,
            "already_imported": summary.total_skipped,
            "failed": summary.total_failed,
            "errors": summary.errors[:20],
            "trade_priced": trade_priced,
            "redeemed": [
                {
                    "isin": r["isin"],
                    "name": r["name"],
                    "date": r["date"],
                    "amount": str(r["amount"]),
                }
                for r in redemptions
            ],
            "not_imported": skipped_reasons,
        }
        # A failed batch is rolled back by bulk-create; keep the digest empty so it retries
        portfolio.sync_digest = digest if not summary.errors else None
        portfolio.sync_report = report
        portfolio.synced_at = datetime.now(timezone.utc)
        self.db.commit()
        logger.info("pytr sync for portfolio %s: %s", portfolio.id, report)
        return report

    async def _map_isins(self, portfolio: Portfolio, instruments) -> tuple:
        """ISIN -> asset id: the user's asset with that ISIN, the same name as a
        mapped ISIN (a security that changed ISIN, e.g. after a reverse split), or
        a confident resolver match. Anything else gets an asset priced from its
        own fills, listed in the report so a ticker can be given later."""
        by_isin = {
            a.isin: a
            for a in self.db.query(Asset).filter(
                Asset.user_id == portfolio.user_id, Asset.isin.isnot(None)
            )
        }
        mapped: Dict[str, int] = {}
        names: Dict[str, int] = {}
        pending = []
        for inst in instruments:
            asset = by_isin.get(inst.isin)
            if asset is not None:
                mapped[inst.isin] = asset.id
                names.setdefault(_name_key(inst.name), asset.id)
            else:
                pending.append(inst)
        trade_priced = [
            {"isin": a.isin, "name": a.name, "suggested_symbol": None}
            for a in by_isin.values()
            if is_trade_priced(a) and a.isin in mapped
        ]
        unresolved = []
        for inst in pending:
            alias = names.get(_name_key(inst.name))
            if alias is not None:
                mapped[inst.isin] = alias
            else:
                unresolved.append(inst)
        if unresolved:
            results = await IsinResolver(self.db).resolve(unresolved, portfolio.user_id)
            for inst, result in zip(unresolved, results):
                if result.status in _CONFIDENT and result.suggested_symbol:
                    try:
                        asset = await self.statements.asset_for_symbol(
                            result.suggested_symbol, inst.isin, portfolio.user_id
                        )
                        mapped[inst.isin] = asset.id
                        continue
                    except DomainError:
                        pass
                asset = Asset(
                    symbol=inst.isin,
                    name=inst.name[:255],
                    asset_type=AssetType.OTHER,
                    currency="EUR",
                    isin=inst.isin,
                    price_source=TRADES,
                    user_id=portfolio.user_id,
                )
                self.db.add(asset)
                self.db.flush()
                mapped[inst.isin] = asset.id
                trade_priced.append(
                    {
                        "isin": inst.isin,
                        "name": inst.name,
                        "suggested_symbol": result.suggested_symbol,
                    }
                )
        return mapped, trade_priced

    def _current_isins(self) -> Optional[set]:
        """ISINs Trade Republic still holds (pytr's portfolio.csv next to the export)."""
        current = self.path.with_name("portfolio.csv")
        if not current.is_file():
            return None
        text = current.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        return {(row.get("ISIN") or "").strip() for row in reader} - {""}

    def _redemptions(self, content: bytes) -> List[Dict[str, Any]]:
        """
        Dividend rows that are really a knock-out's redemption of the whole position:
        the ISIN is no longer held at Trade Republic, the row comes after its last
        buy or sell, and its share count is exactly what those trades leave open.
        """
        current = self._current_isins()
        if current is None:
            return []
        rows = list(
            csv.reader(io.StringIO(content.decode("utf-8-sig")), delimiter=";")
        )[1:]
        rows = sorted((r for r in rows if len(r) >= 8), key=lambda r: r[0])
        open_shares: Dict[str, Decimal] = defaultdict(Decimal)
        last_trade: Dict[str, str] = {}
        payouts: Dict[str, List[list]] = defaultdict(list)
        for r in rows:
            kind, isin = r[1].strip().lower(), r[4].strip()
            if not isin or isin in current:
                continue
            try:
                shares = parse_number(r[5]) or Decimal(0)
            except (InvalidOperation, ValueError):
                continue
            if kind in ("buy", "kauf"):
                open_shares[isin] += shares
                last_trade[isin] = r[0]
            elif kind in ("sell", "verkauf"):
                open_shares[isin] -= shares
                last_trade[isin] = r[0]
            elif kind in ("dividend", "dividende"):
                payouts[isin].append(r)
        redemptions = []
        for isin, held in open_shares.items():
            if held <= Decimal("0.000001"):
                continue
            after = [r for r in payouts.get(isin, []) if r[0] > last_trade[isin]]
            if not after:
                continue
            r = after[-1]
            shares = parse_number(r[5]) or Decimal(0)
            if abs(shares - held) >= Decimal("0.000001"):
                continue
            redemptions.append(
                {
                    "isin": isin,
                    "name": r[3].strip() or isin,
                    "date": r[0][:10],
                    "shares": shares,
                    "amount": parse_number(r[2]) or Decimal(0),
                    "taxes": abs(parse_number(r[7]) or Decimal(0)),
                    "source_key": hashlib.sha256(
                        f"pytr-redemption|{r[0]}|{isin}|{shares}".encode()
                    ).hexdigest(),
                }
            )
        return sorted(redemptions, key=lambda x: x["date"])
