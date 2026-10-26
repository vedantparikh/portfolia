"""
Positions from transactions: FIFO lots, fees in the cost basis, and stock splits.

Market prices from Yahoo are split-adjusted back in time, so every trade is
converted into *today's* share units: a buy of 10 shares before a 2:1 split
becomes 20 shares at half the price. Quantity x adjusted close is then the true
value on every date, and holdings show the current share count without anyone
having to record SPLIT transactions. A transfer in opens a lot at the given
cost. A transfer out closes lots at the given proceeds.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from core.database.models.transaction import TransactionStatus, TransactionType
from core.errors import DomainError

Split = Tuple[date, Decimal]

_SAME_DAY_ORDER = {
    TransactionType.BUY: 0,
    TransactionType.TRANSFER_IN: 0,
    TransactionType.SELL: 1,
    TransactionType.TRANSFER_OUT: 1,
}

_OPENING = (TransactionType.BUY, TransactionType.TRANSFER_IN)
_CLOSING = (TransactionType.SELL, TransactionType.TRANSFER_OUT)


class OversellError(DomainError):
    """Raised when a sell exceeds the quantity held at that point in time."""


@dataclass(frozen=True)
class Trade:
    """A completed transaction in today's share units."""

    id: int
    asset_id: int
    transaction_type: TransactionType
    transaction_date: date
    quantity: Decimal
    price: Decimal
    total_amount: Decimal


def split_factor(splits: Iterable[Split], on: date) -> Decimal:
    """Product of the split ratios that take effect after `on` (ex-date > on)."""
    factor = Decimal(1)
    for ex_date, ratio in splits:
        if ex_date > on:
            factor *= Decimal(ratio)
    return factor


def _as_date(value) -> date:
    return value.date() if isinstance(value, datetime) else value


def to_trades(
    transactions: Iterable,
    splits_by_asset: Optional[Mapping[int, Sequence[Split]]] = None,
) -> List[Trade]:
    """
    Completed transactions as split-adjusted trades in canonical order:
    by date, buys and transfer-ins before sells and transfer-outs on the same day, then by id.
    """
    splits_by_asset = splits_by_asset or {}
    trades = []
    for tx in transactions:
        status = getattr(tx, "status", None)
        if status not in (None, TransactionStatus.COMPLETED):
            continue
        day = _as_date(tx.transaction_date)
        factor = split_factor(splits_by_asset.get(tx.asset_id, ()), day)
        quantity = Decimal(tx.quantity)
        price = Decimal(tx.price)
        if tx.transaction_type in _OPENING or tx.transaction_type in _CLOSING:
            quantity *= factor
            price /= factor
        trades.append(
            Trade(
                id=getattr(tx, "id", 0) or 0,
                asset_id=tx.asset_id,
                transaction_type=tx.transaction_type,
                transaction_date=day,
                quantity=quantity,
                price=price,
                total_amount=Decimal(tx.total_amount),
            )
        )
    trades.sort(
        key=lambda t: (
            t.transaction_date,
            _SAME_DAY_ORDER.get(t.transaction_type, 2),
            t.id,
        )
    )
    return trades


class Lots:
    """FIFO lots of one asset. Cost includes fees and taxes (the cash paid)."""

    def __init__(self) -> None:
        self._lots: List[List[Decimal]] = []

    @property
    def quantity(self) -> Decimal:
        return sum((q for q, _ in self._lots), Decimal(0))

    @property
    def cost(self) -> Decimal:
        return sum((c for _, c in self._lots), Decimal(0))

    def buy(self, quantity: Decimal, cost: Decimal) -> None:
        if quantity > 0:
            self._lots.append([quantity, cost])

    def sell(self, quantity: Decimal, on: date) -> Decimal:
        """Remove `quantity` FIFO and return the cost of the shares sold."""
        held = self.quantity
        if quantity > held:
            raise OversellError(
                f"Sell of {quantity} on {on:%Y-%m-%d} exceeds the {held} units held at that date"
            )
        cost_sold = Decimal(0)
        while quantity > 0:
            lot = self._lots[0]
            take = min(quantity, lot[0])
            portion = take / lot[0] * lot[1]
            cost_sold += portion
            lot[0] -= take
            lot[1] -= portion
            quantity -= take
            if lot[0] <= 0:
                self._lots.pop(0)
        return cost_sold


def compute_position(transactions: Iterable) -> Dict[str, Decimal]:
    """
    Rebuild one asset's position from its transactions (chronological, completed).

    `total_amount` is the cash or the given transfer cost, so opening lots include
    fees and closing proceeds are net of fees and taxes. A transfer in opens a
    lot at that cost. A transfer out closes lots FIFO and realises the given
    proceeds against that cost. Raises OversellError if a close exceeds the holding.
    """
    lots = Lots()
    realized_pnl = Decimal(0)
    cost_of_sold = Decimal(0)
    for tx in transactions:
        if tx.transaction_type in _OPENING:
            lots.buy(Decimal(tx.quantity), Decimal(tx.total_amount))
        elif tx.transaction_type in _CLOSING:
            sold = lots.sell(Decimal(tx.quantity), _as_date(tx.transaction_date))
            realized_pnl += Decimal(tx.total_amount) - sold
            cost_of_sold += sold
    return {
        "quantity": lots.quantity,
        "cost_basis_total": lots.cost,
        "realized_pnl": realized_pnl,
        "cost_of_sold": cost_of_sold,
    }


def day_change(
    quantity_now: Decimal,
    prev_close: Decimal,
    price_now: Decimal,
    trades_today: Iterable,
) -> Tuple[Decimal, Decimal]:
    """
    Today's P&L of one position and the capital it was earned on.

    Shares held all day move from the previous close. Shares bought or transferred
    in today move from their own price, and shares sold or transferred out today
    realise their price against the previous close. The base is the start-of-day
    value plus the cost of shares added today, so an arrival is not a gain.
    """
    bought = sold = Decimal(0)
    pnl = Decimal(0)
    invested_today = Decimal(0)
    for trade in trades_today:
        quantity = Decimal(trade.quantity)
        if trade.transaction_type in _OPENING:
            bought += quantity
            pnl += quantity * (price_now - Decimal(trade.price))
            invested_today += quantity * Decimal(trade.price)
        elif trade.transaction_type in _CLOSING:
            sold += quantity
            pnl += quantity * (Decimal(trade.price) - prev_close)
    held_all_day = quantity_now - bought
    pnl += held_all_day * (price_now - prev_close)
    base = (held_all_day + sold) * prev_close + invested_today
    return pnl, base
