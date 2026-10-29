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
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Literal, Optional

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
    values = [r.rsi for r in readings]
    if all(v < OVERSOLD for v in values):
        action: Action = "buy"
    elif all(v > OVERBOUGHT for v in values):
        action = "sell"
    else:
        action = "hold"
    return GfsResult(readings, action)


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
