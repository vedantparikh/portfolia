"""
Dividend income: what was received per month and year, the next 12 months
expected from today's holdings, yields and dividend growth. Pure functions;
money in the portfolio currency, per-share amounts in today's share units.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple

Event = Tuple[date, float]
"""(ex-date, or pay date when no ex-dates are known; dividend per share)"""

YEAR = 365
MAX_PAY_LAG_DAYS = 90


@dataclass(frozen=True)
class Payment:
    asset_id: int
    day: date
    gross: float
    tax: float

    @property
    def net(self) -> float:
        return self.gross - self.tax


@dataclass(frozen=True)
class Income:
    period: date
    gross: float
    tax: float
    net: float
    payments: int


@dataclass(frozen=True)
class Expected:
    asset_id: int
    day: date
    per_share: float
    amount: float


def _start(day: date, unit: Literal["month", "year"]) -> date:
    return date(day.year, 1 if unit == "year" else day.month, 1)


def _next(period: date, unit: Literal["month", "year"]) -> date:
    if unit == "year":
        return date(period.year + 1, 1, 1)
    return date(period.year + period.month // 12, period.month % 12 + 1, 1)


def income_by(
    payments: Sequence[Payment], unit: Literal["month", "year"], until: date
) -> List[Income]:
    """Every month (or year) from the first payment's to `until`'s, empty ones as zero."""
    if not payments:
        return []
    totals: Dict[date, List[float]] = {}
    for p in payments:
        row = totals.setdefault(_start(p.day, unit), [0.0, 0.0, 0])
        row[0] += p.gross
        row[1] += p.tax
        row[2] += 1
    period = min(totals)
    last = max(max(totals), _start(until, unit))
    rows = []
    while period <= last:
        gross, tax, count = totals.get(period, [0.0, 0.0, 0])
        rows.append(Income(period, gross, tax, gross - tax, int(count)))
        period = _next(period, unit)
    return rows


def trailing(events: Iterable[Event], today: date, days: int = YEAR) -> float:
    """Dividends per share with an ex-date in (today − days, today]."""
    return sum(v for d, v in events if today - timedelta(days=days) < d <= today)


def per_share_by_year(events: Iterable[Event]) -> Dict[int, float]:
    years: Dict[int, float] = {}
    for d, v in events:
        years[d.year] = years.get(d.year, 0.0) + v
    return dict(sorted(years.items()))


def growth_pct(events: Sequence[Event], today: date) -> Optional[float]:
    """Last complete calendar year's dividend per share against the year before."""
    years = per_share_by_year(events)
    last, before = years.get(today.year - 1, 0.0), years.get(today.year - 2, 0.0)
    if last <= 0 or before <= 0:
        return None
    return (last / before - 1) * 100


def pay_lag_days(events: Sequence[Event], paid_on: Iterable[date]) -> int:
    """Median days from ex-date to the payment that followed it (0 when none match)."""
    ex_dates = sorted(d for d, _ in events)
    lags = []
    for day in paid_on:
        before = [d for d in ex_dates if d <= day]
        if before and (day - before[-1]).days <= MAX_PAY_LAG_DAYS:
            lags.append((day - before[-1]).days)
    return int(median(lags)) if lags else 0


def _a_year_later(day: date) -> date:
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)


def expected_payments(
    asset_id: int,
    events: Sequence[Event],
    quantity: float,
    today: date,
    lag_days: int = 0,
) -> List[Expected]:
    """Each dividend of the last 12 months repeated a year later for the shares held now."""
    return [
        Expected(
            asset_id,
            _a_year_later(d) + timedelta(days=lag_days),
            v,
            v * quantity,
        )
        for d, v in sorted(events)
        if today - timedelta(days=YEAR) < d <= today
    ]


def expected_by_month(
    expected: Sequence[Expected], today: date
) -> List[Tuple[date, float, List[Expected]]]:
    """Months from today's to the last expected payment's, with their payments."""
    if not expected:
        return []
    months: Dict[date, List[Expected]] = {}
    for e in expected:
        months.setdefault(_start(e.day, "month"), []).append(e)
    period, last = _start(today, "month"), max(months)
    rows = []
    while period <= last:
        payments = sorted(months.get(period, []), key=lambda e: e.day)
        rows.append((period, sum(e.amount for e in payments), payments))
        period = _next(period, "month")
    return rows


def yield_pct(per_share: float, price: Optional[float]) -> Optional[float]:
    """Dividend per share as a percent of a price (current price or average cost)."""
    if price is None or price <= 0:
        return None
    return per_share / price * 100


def tax_rate_pct(payments: Sequence[Payment], today: date) -> float:
    """Tax withheld ÷ gross over the last 12 months' payments, else all of them."""
    recent = [p for p in payments if today - timedelta(days=YEAR) < p.day <= today]
    basis = recent or list(payments)
    gross = sum(p.gross for p in basis)
    return sum(p.tax for p in basis) / gross * 100 if gross > 0 else 0.0
