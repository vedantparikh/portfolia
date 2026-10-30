"""
Daily portfolio value history rebuilt from trades and closing prices.

The calendar is the trading days found in the price data. A trade on a
non-trading day counts on the next trading day. Prices are carried forward over
gaps. A close older than STALE_PRICE_DAYS sessions is still used, and the day
is flagged. A held asset with no price at all is an error, never valued at cost.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from core.database.models.transaction import TransactionType
from core.domain.positions import Lots, Trade, realized_proceeds
from core.errors import DomainError


class MissingPriceError(DomainError):
    """A held asset has no closing price on or before a valuation date."""


# Sessions on the portfolio calendar since the last print. A weekend is not a
# session here, because the calendar only contains days that have a price.
STALE_PRICE_DAYS = 5


def _day_index(index: pd.Index) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(index)
    if index.tz is not None:
        index = index.tz_localize(None)
    return index.normalize()


def trading_days(
    closes: Mapping[int, pd.Series], start: date, end: date
) -> pd.DatetimeIndex:
    days = set()
    for series in closes.values():
        index = _day_index(series.index)
        days.update(
            index[(index >= pd.Timestamp(start)) & (index <= pd.Timestamp(end))]
        )
    return pd.DatetimeIndex(sorted(days))


def _price_age(observed: pd.DatetimeIndex, days: pd.DatetimeIndex) -> np.ndarray:
    """Trading days on `days` after the last print, through each day; -1 if none."""
    if observed.empty:
        return np.full(len(days), -1)
    pos = observed.searchsorted(days, side="right") - 1
    last = observed[np.clip(pos, 0, None)]
    ages = days.searchsorted(days, side="right") - days.searchsorted(last, side="right")
    return np.where(pos < 0, -1, ages)


def daily_series(
    trades: Sequence[Trade],
    closes: Mapping[int, pd.Series],
    end: date,
    symbols: Optional[Mapping[int, str]] = None,
) -> pd.DataFrame:
    """
    One row per trading day from the first trade to `end`.

    `closes` maps asset id to a date-indexed series of split-adjusted closes.

    Columns (money as float, rounded only at the API boundary):
        value          market value at the close
        cost_basis     FIFO cost of the open lots, fees included
        net_invested   cumulative cash in (buys) minus cash out (sales, dividends)
        inflow         cash invested that day
        outflow        cash returned that day
        realized_pnl   cumulative realized gain on sales, before tax withheld
        dividends      cumulative dividends received
        stale_price    a held asset's close is more than STALE_PRICE_DAYS sessions old
        stale_symbols  those symbols, or "asset {id}" when no name was given
    """
    return daily_series_by_asset(trades, closes, end, symbols)[0]


def daily_series_by_asset(
    trades: Sequence[Trade],
    closes: Mapping[int, pd.Series],
    end: date,
    symbols: Optional[Mapping[int, str]] = None,
) -> Tuple[pd.DataFrame, Dict[int, pd.DataFrame]]:
    """
    `daily_series` plus one frame per asset on the same days, whose columns
    add up to the portfolio's: value, inflow, outflow (sale cash and that
    asset's dividends), quantity held at the close and the close used (NaN
    while no price is known).
    """
    if not trades:
        return pd.DataFrame(), {}
    symbols = symbols or {}
    days = trading_days(closes, trades[0].transaction_date, end)
    if days.empty:
        raise MissingPriceError("No prices in the valuation period")

    prices: Dict[int, np.ndarray] = {}
    ages: Dict[int, np.ndarray] = {}
    for asset_id, series in closes.items():
        series = (
            pd.Series(series.values, index=_day_index(series.index))
            .dropna()
            .sort_index()
        )
        series = series[~series.index.duplicated(keep="last")]
        prices[asset_id] = (
            series.reindex(series.index.union(days))
            .ffill()
            .reindex(days)
            .to_numpy(dtype=float)
        )
        ages[asset_id] = _price_age(pd.DatetimeIndex(series.index), days)
    lots: Dict[int, Lots] = defaultdict(Lots)
    net_invested = realized = dividends = Decimal(0)
    rows = []
    asset_ids = sorted({trade.asset_id for trade in trades})
    columns = ("value", "inflow", "outflow", "quantity")
    per_asset = {
        asset_id: {column: np.zeros(len(days)) for column in columns}
        for asset_id in asset_ids
    }
    next_trade = 0

    for i, day in enumerate(days):
        inflow = outflow = Decimal(0)
        while (
            next_trade < len(trades)
            and pd.Timestamp(trades[next_trade].transaction_date) <= day
        ):
            trade = trades[next_trade]
            next_trade += 1
            if trade.transaction_type in (
                TransactionType.BUY,
                TransactionType.TRANSFER_IN,
            ):
                lots[trade.asset_id].buy(trade.quantity, trade.total_amount)
                inflow += trade.total_amount
                per_asset[trade.asset_id]["inflow"][i] += float(trade.total_amount)
            elif trade.transaction_type in (
                TransactionType.SELL,
                TransactionType.TRANSFER_OUT,
            ):
                sold = lots[trade.asset_id].sell(trade.quantity, trade.transaction_date)
                realized += realized_proceeds(trade) - sold
                outflow += trade.total_amount
                per_asset[trade.asset_id]["outflow"][i] += float(trade.total_amount)
            elif trade.transaction_type == TransactionType.DIVIDEND:
                dividends += trade.total_amount
                outflow += trade.total_amount
                per_asset[trade.asset_id]["outflow"][i] += float(trade.total_amount)

        value = Decimal(0)
        stale = []
        for asset_id, asset_lots in lots.items():
            quantity = asset_lots.quantity
            if quantity <= 0:
                continue
            close = prices[asset_id][i] if asset_id in prices else float("nan")
            name = symbols.get(asset_id, f"asset {asset_id}")
            if np.isnan(close):
                raise MissingPriceError(
                    f"No price for {name} on or before {day:%Y-%m-%d}"
                )
            if asset_id in ages and ages[asset_id][i] > STALE_PRICE_DAYS:
                stale.append(name)
            held = quantity * Decimal(str(close))
            per_asset[asset_id]["value"][i] = float(held)
            per_asset[asset_id]["quantity"][i] = float(quantity)
            value += held

        net_invested += inflow - outflow
        rows.append(
            {
                "date": day,
                "value": float(value),
                "cost_basis": float(
                    sum((lot.cost for lot in lots.values()), Decimal(0))
                ),
                "net_invested": float(net_invested),
                "inflow": float(inflow),
                "outflow": float(outflow),
                "realized_pnl": float(realized),
                "dividends": float(dividends),
                "stale_price": bool(stale),
                "stale_symbols": sorted(stale),
            }
        )

    portfolio = pd.DataFrame(rows).set_index("date")
    missing = np.full(len(days), np.nan)
    return portfolio, {
        asset_id: pd.DataFrame(
            {**per_asset[asset_id], "price": prices.get(asset_id, missing)},
            index=portfolio.index,
        )
        for asset_id in asset_ids
    }
