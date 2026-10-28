"""
Keep a portfolio in step with the Trade Republic export that Bachat refreshes.

The file is only read. Each run parses it with the pytr parser and sends every
row to bulk-create, which skips rows whose source key is already stored, so a
run only adds what is new. Splits and swaps are skipped by the parser: the
listing's Yahoo split ratios restate the old trades.
"""

import base64
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from core.database.models import Asset, Portfolio, User
from core.errors import DomainError
from core.schemas.account_statements import BulkTransactionItem
from core.services.account_statement_service import AccountStatementService
from core.services.isin_resolver import IsinResolver

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
        """Tie an ISIN from the export to a Yahoo ticker; the next sync imports its rows."""
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
        isin_to_asset, unmapped = await self._map_isins(portfolio, parsed.instruments)
        items: List[BulkTransactionItem] = []
        for row in parsed.transactions:
            asset_id = isin_to_asset.get(row.symbol or "")
            if asset_id is None:
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
            "unmapped": unmapped,
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
        a confident resolver match. Everything else is reported, not guessed."""
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
        unresolved = []
        for inst in pending:
            alias = names.get(_name_key(inst.name))
            if alias is not None:
                mapped[inst.isin] = alias
            else:
                unresolved.append(inst)
        unmapped = []
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
                unmapped.append(
                    {
                        "isin": inst.isin,
                        "name": inst.name,
                        "rows": inst.transaction_count,
                        "suggested_symbol": result.suggested_symbol,
                    }
                )
        return mapped, unmapped
