"""
Filters and highlights over the user's assets by their cached Yahoo quote.

Quote units: `price_change_percentage_24h` and `dividend_yield` are percent
(Yahoo's `regularMarketChangePercent`, `dividendYield`), `revenue_growth` is a
fraction and comes out here as percent.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple

# |24h change| below this counts as flat, at or above it as up or down
FLAT_CHANGE_PCT = 0.5

Change = Literal["up", "down", "flat"]
Quote = Dict[str, Any]


def _number(quote: Optional[Quote], field: str) -> Optional[float]:
    value = (quote or {}).get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class QuoteFilter:
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    change: Optional[Change] = None

    @property
    def active(self) -> bool:
        return any(
            value is not None
            for value in (
                self.price_min,
                self.price_max,
                self.market_cap_min,
                self.market_cap_max,
                self.change,
            )
        )

    def matches(self, quote: Optional[Quote]) -> bool:
        """Lower bounds are inclusive, upper bounds exclusive; a missing value never matches a set bound."""
        for field, low, high in (
            ("current_price", self.price_min, self.price_max),
            ("market_cap", self.market_cap_min, self.market_cap_max),
        ):
            if low is None and high is None:
                continue
            value = _number(quote, field)
            if value is None:
                return False
            if low is not None and value < low:
                return False
            if high is not None and value >= high:
                return False
        if self.change is not None:
            change = _number(quote, "price_change_percentage_24h")
            if change is None:
                return False
            if self.change == "up":
                return change >= FLAT_CHANGE_PCT
            if self.change == "down":
                return change <= -FLAT_CHANGE_PCT
            return abs(change) < FLAT_CHANGE_PCT
        return True


Pick = Tuple[str, Optional[str], float]


def _best(
    rows: Iterable[Tuple[str, Optional[str], Optional[Quote]]],
    value: Callable[[Optional[Quote]], Optional[float]],
    highest: bool,
) -> Optional[Dict[str, Any]]:
    best: Optional[Pick] = None
    for symbol, name, quote in rows:
        found = value(quote)
        if found is None:
            continue
        if best is None or (found > best[2] if highest else found < best[2]):
            best = (symbol, name, found)
    if best is None:
        return None
    return {"symbol": best[0], "name": best[1], "value": best[2]}


def _positive(field: str) -> Callable[[Optional[Quote]], Optional[float]]:
    def value(quote: Optional[Quote]) -> Optional[float]:
        found = _number(quote, field)
        return found if found is not None and found > 0 else None

    return value


def _growth_pct(quote: Optional[Quote]) -> Optional[float]:
    growth = _number(quote, "revenue_growth")
    return growth * 100 if growth is not None else None


def _of_52w_high_pct(quote: Optional[Quote]) -> Optional[float]:
    price = _number(quote, "current_price")
    high = _number(quote, "high_52w")
    if price is None or not high or high <= 0:
        return None
    return price / high * 100


def highlights(
    rows: List[Tuple[str, Optional[str], Optional[Quote]]],
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Each highlight is {symbol, name, value}, or None when no asset has the field."""

    def change(quote: Optional[Quote]) -> Optional[float]:
        return _number(quote, "price_change_percentage_24h")

    return {
        "top_gainer": _best(rows, change, highest=True),
        "top_loser": _best(rows, change, highest=False),
        "highest_dividend_yield": _best(rows, _positive("dividend_yield"), True),
        "lowest_pe": _best(rows, _positive("trailing_PE"), highest=False),
        "most_traded": _best(rows, _positive("volume_24h"), highest=True),
        "lowest_beta": _best(rows, _positive("beta"), highest=False),
        "highest_revenue_growth": _best(rows, _growth_pct, highest=True),
        "closest_to_52w_high": _best(rows, _of_52w_high_pct, highest=True),
    }
