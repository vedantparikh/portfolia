"""
Convert market prices and cash into one portfolio currency.

Quote currencies in minor units (London pence `GBp`/`GBX`, Israeli agorot `ILA`)
are scaled to the major unit once. A price series is multiplied by the daily
portfolio-per-1-quote rate, forward-filled. A missing rate on or before a day
raises `MissingFxError` — never a silent unconverted value. Cash uses the rate
on the transaction date, and only when that cash currency is not already the
portfolio currency.
"""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping, Sequence

import pandas as pd

from core.domain.positions import Trade
from core.domain.valuation import MissingPriceError

_MINOR = {
    "GBp": ("GBP", Decimal(100)),
    "GBX": ("GBP", Decimal(100)),
    "ILA": ("ILS", Decimal(100)),
}


class MissingFxError(MissingPriceError):
    """No exchange rate on or before a valuation or transaction date."""

    def __init__(self, quote: str, portfolio: str, day: date | None = None):
        when = f" on or before {day.isoformat()}" if day else ""
        super().__init__(f"No exchange rate from {quote} to {portfolio}{when}")


def canonical_currency(code: str | None) -> tuple[str, Decimal]:
    """`(major currency, divisor)`. `GBp` is 1/100 of `GBP`; unknown codes pass through."""
    raw = (code or "").strip()
    if raw in _MINOR:
        return _MINOR[raw]
    upper = raw.upper()
    if upper in _MINOR:
        return _MINOR[upper]
    return upper, Decimal(1)


def _normalized(series: pd.Series) -> pd.Series:
    values = series.dropna().astype(float)
    index = pd.DatetimeIndex(pd.to_datetime(values.index))
    if index.tz is not None:
        index = index.tz_localize(None)
    values = pd.Series(values.to_numpy(), index=index.normalize())
    return values[~values.index.duplicated(keep="last")].sort_index()


def rate_on(rates: pd.Series, day: date, quote: str, portfolio: str) -> Decimal:
    """Portfolio currency per 1 quote unit, carried forward to `day`."""
    rates = _normalized(rates)
    if rates.empty:
        raise MissingFxError(quote, portfolio, day)
    eligible = rates.loc[: pd.Timestamp(day)]
    if eligible.empty:
        raise MissingFxError(quote, portfolio, day)
    return Decimal(str(eligible.iloc[-1]))


def convert_series(
    prices: pd.Series, rates: pd.Series, quote: str, portfolio: str
) -> pd.Series:
    """`prices` (already in major units) times the forward-filled rate."""
    prices = _normalized(prices)
    rates = _normalized(rates)
    if prices.empty:
        return prices
    if rates.empty:
        raise MissingFxError(quote, portfolio, prices.index[0].date())
    aligned = (
        rates.reindex(rates.index.union(prices.index)).ffill().reindex(prices.index)
    )
    missing = aligned[aligned.isna()]
    if not missing.empty:
        raise MissingFxError(quote, portfolio, missing.index[0].date())
    return prices * aligned


def _factor(
    currency: str | None,
    portfolio_currency: str,
    day: date,
    rates_by_major: Mapping[str, pd.Series],
) -> Decimal:
    major, scale = canonical_currency(currency)
    portfolio, _ = canonical_currency(portfolio_currency)
    factor = Decimal(1) / scale
    if major == portfolio:
        return factor
    rates = rates_by_major.get(major)
    if rates is None:
        raise MissingFxError(major, portfolio, day)
    return factor * rate_on(rates, day, major, portfolio)


def convert_amount(
    amount: Decimal | float | int | str,
    currency: str | None,
    portfolio_currency: str,
    day: date,
    rates_by_major: Mapping[str, pd.Series],
) -> Decimal:
    """One money amount into the portfolio currency."""
    if isinstance(day, datetime):
        day = day.date()
    return Decimal(str(amount)) * _factor(
        currency, portfolio_currency, day, rates_by_major
    )


def convert_closes(
    closes: pd.Series,
    currency: str | None,
    portfolio_currency: str,
    rates_by_major: Mapping[str, pd.Series],
) -> pd.Series:
    """A close series into the portfolio currency. Same currency and major unit is unchanged."""
    major, scale = canonical_currency(currency)
    portfolio, _ = canonical_currency(portfolio_currency)
    if major == portfolio and scale == 1:
        return closes
    scaled = closes.astype(float) / float(scale)
    if major == portfolio:
        return scaled
    rates = rates_by_major.get(major)
    if rates is None:
        raise MissingFxError(major, portfolio)
    return convert_series(scaled, rates, major, portfolio)


def convert_trades(
    trades: Sequence[Trade],
    currency_by_id: Mapping[int, str | None],
    portfolio_currency: str,
    rates_by_major: Mapping[str, pd.Series],
) -> list[Trade]:
    """Scale each trade's cash and price. Identity when the cash is already in the portfolio currency."""
    converted = []
    for trade in trades:
        factor = _factor(
            currency_by_id.get(trade.id),
            portfolio_currency,
            trade.transaction_date,
            rates_by_major,
        )
        if factor == 1:
            converted.append(trade)
        else:
            converted.append(
                replace(
                    trade,
                    price=trade.price * factor,
                    total_amount=trade.total_amount * factor,
                )
            )
    return converted
