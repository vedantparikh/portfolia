"""
German capital income tax (Abgeltungsteuer) as a German bank applies it to one
account: two loss pots, the Sparerpauschbetrag, the 30 % Teilfreistellung of
equity funds and the Vorabpauschale. Pure functions; money in euros. An
estimate for information, not tax advice.
"""

from dataclasses import dataclass
from datetime import date
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from core.database.models import TransactionType
from core.domain.positions import Trade, realized_proceeds

Kind = Literal["share", "fund", "other"]

FLAT_RATE = 0.25
SOLIDARITY = 0.055
EQUITY_FUND_EXEMPTION = 0.30
BASE_YIELD_SHARE = 0.7
BASISZINS_PCT: Dict[int, float] = {
    2018: 0.87,
    2019: 0.52,
    2020: 0.07,
    2021: -0.45,
    2022: -0.05,
    2023: 2.55,
    2024: 2.29,
    2025: 2.53,
    2026: 3.20,
}
"""BMF Basiszins on the first working day of each year (§ 18 Abs. 4 InvStG)."""


def sparerpauschbetrag(year: int, joint: bool = False) -> float:
    single = 801.0 if year < 2023 else 1000.0
    return single * 2 if joint else single


def tax_rate_pct(church_pct: float = 0.0) -> float:
    """Abgeltungsteuer + Soli (+ church tax, which lowers the 25 % base): 26.375 % without."""
    k = church_pct / 100
    return (1 + SOLIDARITY + k) / (4 + k) * 100


def taxable_share(kind: Kind) -> float:
    """Part of a gain or distribution that is taxed (equity funds: 70 %)."""
    return 1 - EQUITY_FUND_EXEMPTION if kind == "fund" else 1.0


@dataclass(frozen=True)
class SaleLot:
    asset_id: int
    sold_on: date
    bought_on: date
    quantity: float
    cost: float
    proceeds: float

    @property
    def gain(self) -> float:
        return self.proceeds - self.cost


_OPENING = (TransactionType.BUY, TransactionType.TRANSFER_IN)
_CLOSING = (TransactionType.SELL, TransactionType.TRANSFER_OUT)


Lot = List[Any]
"""[bought_on, quantity, cost], shrunk in place as sales close it"""


def _replay(
    trades: Iterable[Trade], until: Optional[date] = None
) -> Tuple[Dict[int, List[Lot]], List[SaleLot]]:
    """FIFO lots per asset and the SaleLots of every sale."""
    lots: Dict[int, List[Lot]] = {}
    sales: List[SaleLot] = []
    for t in trades:
        if until is not None and t.transaction_date > until:
            break
        queue = lots.setdefault(t.asset_id, [])
        if t.transaction_type in _OPENING:
            if t.quantity > 0:
                queue.append(
                    [t.transaction_date, float(t.quantity), float(t.total_amount)]
                )
        elif t.transaction_type in _CLOSING:
            left = float(t.quantity)
            total = left
            proceeds = float(realized_proceeds(t))
            while left > 1e-12 and queue:
                lot = queue[0]
                take = min(left, lot[1])
                cost = lot[2] * take / lot[1]
                if t.transaction_type == TransactionType.SELL:
                    sales.append(
                        SaleLot(
                            t.asset_id,
                            t.transaction_date,
                            lot[0],
                            take,
                            cost,
                            proceeds * take / total if total else 0.0,
                        )
                    )
                lot[1] -= take
                lot[2] -= cost
                left -= take
                if lot[1] <= 1e-12:
                    queue.pop(0)
    return lots, sales


def sale_lots(trades: Iterable[Trade]) -> List[SaleLot]:
    """Every sale split over the FIFO lots it closed (transfers out close lots without a sale)."""
    return _replay(trades)[1]


def open_lots(trades: Iterable[Trade], on: date) -> Dict[int, List[Tuple[date, float]]]:
    """FIFO lots `(bought_on, quantity)` per asset held at the end of `on`."""
    lots = _replay(trades, until=on)[0]
    return {
        asset_id: [(lot[0], lot[1]) for lot in queue]
        for asset_id, queue in lots.items()
        if queue
    }


def vorabpauschale_per_share(
    start_price: float, end_price: float, distributions: float, basiszins_pct: float
) -> float:
    """
    § 18 InvStG: Basisertrag = start × Basiszins × 0.7, capped at the year's gain
    plus distributions, less the distributions; never negative.
    """
    if basiszins_pct <= 0:
        return 0.0
    base = start_price * basiszins_pct / 100 * BASE_YIELD_SHARE
    gain = max(0.0, end_price - start_price + distributions)
    return max(0.0, min(base, gain) - distributions)


def held_fraction(bought_on: date, year: int) -> float:
    """Shares bought in `year` lose 1/12 for each full month before the purchase month."""
    if bought_on.year < year:
        return 1.0
    if bought_on.year > year:
        return 0.0
    return (13 - bought_on.month) / 12


def vorabpauschale(
    lots: Sequence[Tuple[date, float]], per_share: float, year: int
) -> float:
    """The year's Vorabpauschale for the lots held at its end (taxed the next January)."""
    return sum(q * per_share * held_fraction(b, year) for b, q in lots)


def vorabpauschale_credit(
    lot: SaleLot, per_share_by_year: Mapping[int, float]
) -> float:
    """Vorabpauschalen already taxed on the sold shares, deducted from the sale's gain."""
    return sum(
        lot.quantity * v * held_fraction(lot.bought_on, y)
        for y, v in per_share_by_year.items()
        if lot.bought_on <= date(y, 12, 31) < lot.sold_on
    )


@dataclass(frozen=True)
class Settlement:
    share_net: float
    other_net: float
    income: float
    allowance_used: float
    allowance_left: float
    taxable: float
    tax: float
    share_loss_carried: float
    other_loss_carried: float


def settle(
    share_net: float,
    other_net: float,
    allowance: float,
    rate_pct: float,
    share_loss_in: float = 0.0,
    other_loss_in: float = 0.0,
) -> Settlement:
    """
    One year at one bank: share losses offset only share gains; other losses
    (and the other pot's carried loss) offset both. What is left positive uses
    the allowance first. Carried losses are ≤ 0.
    """
    shares = share_net + share_loss_in
    other = other_net + other_loss_in
    if shares < 0:
        share_carry = shares
        income = max(0.0, other)
        other_carry = min(0.0, other)
    else:
        share_carry = 0.0
        combined = shares + other
        income = max(0.0, combined)
        other_carry = min(0.0, combined)
    used = min(allowance, income)
    taxable = income - used
    return Settlement(
        share_net=share_net,
        other_net=other_net,
        income=income,
        allowance_used=used,
        allowance_left=allowance - used,
        taxable=taxable,
        tax=taxable * rate_pct / 100,
        share_loss_carried=share_carry,
        other_loss_carried=other_carry,
    )


def split_allowance(incomes: Mapping[int, float], total: float) -> Dict[int, float]:
    """The allowance per bank: largest income first, each up to its income; any rest to the largest."""
    split = {key: 0.0 for key in incomes}
    left = total
    for key in sorted(incomes, key=lambda k: -incomes[k]):
        take = min(left, max(0.0, incomes[key]))
        split[key] = take
        left -= take
    if incomes and left > 0:
        split[max(incomes, key=lambda k: incomes[k])] += left
    return split
