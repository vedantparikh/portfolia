"""
Rule-based signals from daily closes. They describe what the rules say, not
advice; the API and UI label them that way.

- GFS (grandfather-father-son): RSI(14) of monthly, weekly and daily closes.
  All three below 30 → "buy", all three above 70 → "sell", otherwise "hold".
- MACD with a trend filter: MACD(12, 26) crossing its 9-period signal line.
  A cross up below zero while the close is above its 200-day EMA → "buy";
  a cross down above zero while the close is below it → "sell".

RSI and EMAs match the indicator chart: Wilder RSI (EMA alpha 1/n), recursive
EMAs (`adjust=False`).

`backtest` replays a strategy's past signals long only, without costs or
taxes: buy at the close of a buy signal when flat, sell at the close of the
next sell signal; a trade still open is valued at the last close. Past GFS
signals use what each day knew: that day's close ends the current month and
week (`live_rsi`), so nothing from later in the period leaks in.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Literal, Optional

import numpy as np
import pandas as pd

from core.errors import DomainError

RSI_WINDOW = 14
OVERSOLD = 30.0
OVERBOUGHT = 70.0
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
TREND_EMA = 200

Action = Literal["buy", "sell", "hold"]
Timeframe = Literal["monthly", "weekly", "daily"]


def rsi(closes: pd.Series, window: int = RSI_WINDOW) -> pd.Series:
    change = closes.diff()
    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)
    average_gain = gains.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    average_loss = losses.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    strength = average_gain / average_loss
    out = 100 - 100 / (1 + strength)
    # No losses in the window: RSI is 100
    return out.where(average_loss != 0, 100.0).where(average_gain.notna())


def _last_per(closes: pd.Series, rule: str) -> pd.Series:
    return closes.groupby(closes.index.to_period(rule)).last()


@dataclass(frozen=True)
class GfsReading:
    timeframe: Timeframe
    rsi: float
    as_of: date


@dataclass(frozen=True)
class GfsResult:
    readings: List[GfsReading]
    action: Action


def gfs(closes: pd.Series) -> GfsResult:
    """`closes` indexed by date, oldest first. Needs 15 months of history."""
    closes = closes.dropna().sort_index()
    readings = []
    timeframes: tuple[tuple[Timeframe, pd.Series], ...] = (
        ("monthly", _last_per(closes, "M")),
        ("weekly", _last_per(closes, "W")),
        ("daily", closes),
    )
    for timeframe, series in timeframes:
        values = rsi(series).dropna()
        if values.empty:
            raise DomainError(
                f"Not enough price history for a {timeframe} RSI({RSI_WINDOW})"
            )
        moment = values.index[-1]
        as_of = (
            moment.end_time.date() if isinstance(moment, pd.Period) else moment.date()
        )
        readings.append(GfsReading(timeframe, float(values.iloc[-1]), as_of))
    return GfsResult(readings, _gfs_action([r.rsi for r in readings]))


def _gfs_action(values: List[float]) -> Action:
    if all(v < OVERSOLD for v in values):
        return "buy"
    if all(v > OVERBOUGHT for v in values):
        return "sell"
    return "hold"


@dataclass(frozen=True)
class MacdSignal:
    date: date
    action: Literal["buy", "sell"]
    close: float
    macd: float
    signal: float
    trend_ema: float


def macd_signals(closes: pd.Series, since: Optional[date] = None) -> List[MacdSignal]:
    """Crossovers that pass the zero-line and 200-day trend rules, oldest first."""
    closes = closes.dropna().sort_index()
    if len(closes) <= TREND_EMA:
        raise DomainError(
            f"Not enough price history for the {TREND_EMA}-day trend line"
        )
    macd = (
        closes.ewm(span=MACD_FAST, adjust=False).mean()
        - closes.ewm(span=MACD_SLOW, adjust=False).mean()
    )
    signal = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()
    trend = closes.ewm(span=TREND_EMA, adjust=False).mean()
    above = macd > signal
    found = []
    for i in range(TREND_EMA, len(closes)):
        if above.iloc[i] == above.iloc[i - 1]:
            continue
        day = closes.index[i].date()
        if since and day < since:
            continue
        m, s, close, t = macd.iloc[i], signal.iloc[i], closes.iloc[i], trend.iloc[i]
        if above.iloc[i] and m < 0 and close > t:
            action: Literal["buy", "sell"] = "buy"
        elif not above.iloc[i] and m > 0 and close < t:
            action = "sell"
        else:
            continue
        found.append(
            MacdSignal(day, action, float(close), float(m), float(s), float(t))
        )
    return found


def live_rsi(closes: pd.Series, rule: str) -> pd.Series:
    """
    RSI(14) of monthly ("M") or weekly ("W") closes as it read on each day: the
    day's close stands in for the end of its unfinished period. NaN until 14
    period changes exist. On the last day it equals `rsi` of the period closes.
    """
    closes = closes.dropna().sort_index()
    periods = closes.index.to_period(rule)
    ends = closes.groupby(periods).last()
    change = ends.diff()
    alpha = 1 / RSI_WINDOW
    gains = change.clip(lower=0).ewm(alpha=alpha, adjust=False).mean()
    losses = (-change.clip(upper=0)).ewm(alpha=alpha, adjust=False).mean()
    previous = pd.DataFrame(
        {
            "end": ends.shift(1),
            "gain": gains.shift(1),
            "loss": losses.shift(1),
            "count": pd.Series(np.arange(len(ends)), index=ends.index),
        }
    ).reindex(periods)
    day_change = closes.to_numpy() - previous["end"].to_numpy()
    first = previous["gain"].isna().to_numpy()
    gain = np.where(
        first,
        np.clip(day_change, 0, None),
        (1 - alpha) * previous["gain"].to_numpy()
        + alpha * np.clip(day_change, 0, None),
    )
    loss = np.where(
        first,
        np.clip(-day_change, 0, None),
        (1 - alpha) * previous["loss"].to_numpy()
        + alpha * np.clip(-day_change, 0, None),
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(loss == 0, 100.0, 100 - 100 / (1 + gain / loss))
    valid = previous["count"].to_numpy() >= RSI_WINDOW
    return pd.Series(np.where(valid, out, np.nan), index=closes.index)


@dataclass(frozen=True)
class Signal:
    date: date
    action: Literal["buy", "sell"]


def gfs_signals(closes: pd.Series, since: Optional[date] = None) -> List[Signal]:
    """Days the GFS rule turned to buy or to sell, oldest first."""
    closes = closes.dropna().sort_index()
    frame = pd.DataFrame(
        {
            "monthly": live_rsi(closes, "M"),
            "weekly": live_rsi(closes, "W"),
            "daily": rsi(closes),
        }
    ).dropna()
    found = []
    previous: Action = "hold"
    for day, row in frame.iterrows():
        action = _gfs_action([row["monthly"], row["weekly"], row["daily"]])
        if action != previous and action != "hold":
            if since is None or day.date() >= since:
                found.append(Signal(day.date(), action))
        previous = action
    return found


@dataclass(frozen=True)
class Trade:
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    return_pct: float
    open: bool


@dataclass(frozen=True)
class Backtest:
    start: date
    end: date
    trades: List[Trade]
    win_rate_pct: Optional[float]
    average_return_pct: Optional[float]
    total_return_pct: float
    buy_and_hold_pct: float
    days_invested_pct: float


def backtest(closes: pd.Series, signals: List[Signal], start: date) -> Backtest:
    """Long only, one position at a time, from `start` to the last close."""
    closes = closes.dropna().sort_index()
    window = closes[closes.index >= pd.Timestamp(start)]
    if len(window) < 2:
        raise DomainError("Not enough price history for the backtest window")
    trades: List[Trade] = []
    entry: Optional[tuple[date, float]] = None
    invested_days = 0
    for signal in sorted(signals, key=lambda s: s.date):
        if signal.date < start:
            continue
        price = float(window[window.index.date <= signal.date].iloc[-1])
        if signal.action == "buy" and entry is None:
            entry = (signal.date, price)
        elif signal.action == "sell" and entry is not None:
            trades.append(_trade(entry, signal.date, price, False))
            invested_days += _days(window, entry[0], signal.date)
            entry = None
    last_day, last_price = window.index[-1].date(), float(window.iloc[-1])
    if entry is not None:
        trades.append(_trade(entry, last_day, last_price, True))
        invested_days += _days(window, entry[0], last_day)
    returns = [t.return_pct for t in trades]
    growth = float(np.prod([1 + r / 100 for r in returns])) if returns else 1.0
    return Backtest(
        start=window.index[0].date(),
        end=last_day,
        trades=trades,
        win_rate_pct=(
            sum(1 for r in returns if r > 0) / len(returns) * 100 if returns else None
        ),
        average_return_pct=sum(returns) / len(returns) if returns else None,
        total_return_pct=(growth - 1) * 100,
        buy_and_hold_pct=(last_price / float(window.iloc[0]) - 1) * 100,
        days_invested_pct=invested_days / (len(window) - 1) * 100,
    )


def _trade(
    entry: tuple[date, float], exit_day: date, price: float, open: bool
) -> Trade:
    return Trade(
        entry[0], entry[1], exit_day, price, (price / entry[1] - 1) * 100, open
    )


def _days(window: pd.Series, first: date, last: date) -> int:
    """Trading days held: sessions after the entry close up to the exit close."""
    days = window.index.date
    return int(((days > first) & (days <= last)).sum())
