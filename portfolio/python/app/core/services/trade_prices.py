"""
Prices for securities Yahoo does not carry (knock-outs, warrants): the asset's own
fills, last fill of each day, carried forward by the valuation like any close.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy.orm import Session

from core.database.models import Asset, Transaction, TransactionStatus, TransactionType

TRADES = "trades"
_PRICED = (
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.TRANSFER_IN,
    TransactionType.TRANSFER_OUT,
)


def is_trade_priced(asset: Optional[Asset]) -> bool:
    return getattr(asset, "price_source", None) == TRADES


def trade_price_history(db: Session, asset: Asset) -> Dict[str, Any]:
    """Same shape as MarketDataService.get_daily_history: naive date index, no splits."""
    fills = (
        db.query(Transaction.transaction_date, Transaction.price)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.transaction_type.in_(_PRICED),
        )
        .order_by(Transaction.transaction_date, Transaction.id)
        .all()
    )
    closes: Dict[pd.Timestamp, float] = {}
    for day, price in fills:
        closes[pd.Timestamp(day.date())] = float(price)
    return {
        "close": pd.Series(closes, dtype=float).sort_index(),
        "splits": pd.Series(dtype=float),
        "dividends": pd.Series(dtype=float),
    }


def last_trade_price(db: Session, asset: Asset) -> Optional[Decimal]:
    closes = trade_price_history(db, asset)["close"]
    return Decimal(str(closes.iloc[-1])) if len(closes) else None
