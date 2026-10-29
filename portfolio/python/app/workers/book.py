"""Holding prices, FX and performance snapshots for the background worker.

A snapshot is written when a transaction is newer than the last snapshot, and
once after 22:00 UTC if today's close is not stored yet. Request handlers do
not write snapshots.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database.models import Asset, Portfolio, PortfolioAsset, Transaction
from core.database.models.portfolio_analytics import PortfolioPerformanceHistory
from core.domain.fx import MissingFxError, canonical_currency
from core.errors import DomainError
from core.services.market_data_service import MarketDataService
from modules.analytics.service import PortfolioAnalyticsService

logger = logging.getLogger(__name__)

DAILY_CLOSE_HOUR_UTC = 22


def _utc(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def snapshot_due(
    latest_transaction_at: datetime | None,
    latest_snapshot_at: datetime | None,
    now: datetime,
) -> bool:
    """True when a trade landed after the last snapshot, or the daily close is missing."""
    now = _utc(now)
    latest_transaction_at = _utc(latest_transaction_at)
    latest_snapshot_at = _utc(latest_snapshot_at)
    if latest_transaction_at is not None and (
        latest_snapshot_at is None or latest_transaction_at > latest_snapshot_at
    ):
        return True
    close = now.replace(hour=DAILY_CLOSE_HOUR_UTC, minute=0, second=0, microsecond=0)
    if now < close:
        return False
    return latest_snapshot_at is None or latest_snapshot_at < close


async def refresh_book(
    db: Session, market: MarketDataService | None = None, now: datetime | None = None
) -> dict:
    """Refresh prices and FX for held symbols, then write the snapshots that are due."""
    now = _utc(now or datetime.now(timezone.utc))
    held = (
        db.query(Asset.symbol, Asset.currency, Portfolio.currency, Portfolio.id)
        .join(PortfolioAsset, PortfolioAsset.asset_id == Asset.id)
        .join(Portfolio, Portfolio.id == PortfolioAsset.portfolio_id)
        .filter(Portfolio.is_active.is_(True), Asset.price_source.is_(None))
        .all()
    )
    symbols = sorted({symbol.upper() for symbol, _, _, _ in held if symbol})
    pairs = set()
    portfolio_ids = set()
    for _, quote, portfolio_currency, portfolio_id in held:
        portfolio_ids.add(portfolio_id)
        quote_major, _ = canonical_currency(quote)
        portfolio_major, _ = canonical_currency(portfolio_currency)
        if quote_major and portfolio_major and quote_major != portfolio_major:
            pairs.add((quote_major, portfolio_major))

    if not held:
        return {"holding_symbols": 0, "fx_pairs": 0, "snapshots": 0}
    market = market or MarketDataService()

    if symbols:
        await market.get_current_prices(symbols, refresh=True)
        await market.get_yesterdays_closes(symbols)
        for symbol in symbols:
            await market.get_daily_history(symbol)

    fx_pairs = 0
    for quote, portfolio_currency in sorted(pairs):
        try:
            await market.get_fx_rates(quote, portfolio_currency)
            fx_pairs += 1
        except MissingFxError:
            logger.warning("No exchange rate from %s to %s", quote, portfolio_currency)

    written = await _write_due_snapshots(db, portfolio_ids, now)
    return {
        "holding_symbols": len(symbols),
        "fx_pairs": fx_pairs,
        "snapshots": written,
    }


async def _write_due_snapshots(
    db: Session, portfolio_ids: set[int], now: datetime
) -> int:
    if not portfolio_ids:
        return 0
    transaction_at = dict(
        db.query(Transaction.portfolio_id, func.max(Transaction.updated_at))
        .filter(Transaction.portfolio_id.in_(portfolio_ids))
        .group_by(Transaction.portfolio_id)
        .all()
    )
    snapshot_at = dict(
        db.query(
            PortfolioPerformanceHistory.portfolio_id,
            func.max(PortfolioPerformanceHistory.created_at),
        )
        .filter(PortfolioPerformanceHistory.portfolio_id.in_(portfolio_ids))
        .group_by(PortfolioPerformanceHistory.portfolio_id)
        .all()
    )
    analytics = PortfolioAnalyticsService(db)
    written = 0
    for portfolio_id in sorted(portfolio_ids):
        if not snapshot_due(
            transaction_at.get(portfolio_id), snapshot_at.get(portfolio_id), now
        ):
            continue
        try:
            await analytics.create_performance_snapshot(portfolio_id, now)
            db.commit()
            written += 1
        except DomainError:
            db.rollback()
            logger.info("Portfolio %s has nothing to snapshot", portfolio_id)
        except Exception:
            db.rollback()
            logger.exception("Snapshot failed for portfolio %s", portfolio_id)
    return written
