"""
Rule-based signals from daily closes. They describe what the rules say, not
advice; the API and UI label them that way.

- GFS (grandfather-father-son): RSI(14) of monthly, weekly and daily closes.
  All three below 30 → "buy", all three above 70 → "sell", otherwise "hold".
- MACD with a trend filter: MACD(12, 26) crossing its 9-period signal line.
  A cross up below zero while the close is above its 200-day EMA → "buy";
  a cross down above zero while the close is below it → "sell".
- Golden / death cross: the 50-day SMA crossing above / below the 200-day SMA.
- 200-day trend: the close crossing above / below its 200-day SMA.
- RSI mean reversion: daily RSI(14) climbing back above 30 → "buy", falling
  back below 70 → "sell".
- Bollinger reversion: the close returning inside the 20-day, 2σ bands, above
  the lower band → "buy", below the upper band → "sell".
- Breakout: a close above the prior 55-day high → "buy", below the prior
  20-day low → "sell".

Every rule is in `STRATEGIES`; each reads only closes up to the signal day.

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
from typing import Callable, Dict, List, Literal, Optional

import numpy as np
import pandas as pd

from core.errors import DomainError

RSI_WINDOW = 14
OVERSOLD = 30.0
OVERBOUGHT = 70.0
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
TREND_EMA = 200
SMA_FAST, SMA_SLOW = 50, 200
BOLLINGER_WINDOW, BOLLINGER_WIDTH = 20, 2.0
BREAKOUT_ENTRY, BREAKOUT_EXIT = 55, 20

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
    if frame.empty:
        raise DomainError(f"Not enough price history for a monthly RSI({RSI_WINDOW})")
    found = []
    previous: Action = "hold"
    values = frame.to_numpy()
    actions = np.select(
        [(values < OVERSOLD).all(axis=1), (values > OVERBOUGHT).all(axis=1)],
        ["buy", "sell"],
        "hold",
    )
    for day, action in zip(frame.index, actions.tolist()):
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

    @property
    def vs_holding_pp(self) -> float:
        return self.total_return_pct - self.buy_and_hold_pct


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
        price = float(window.iloc[_through(window, signal.date) - 1])
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


def _through(window: pd.Series, day: date) -> int:
    """Number of sessions in `window` up to and including `day`."""
    return int(window.index.searchsorted(pd.Timestamp(day), side="right"))


def _days(window: pd.Series, first: date, last: date) -> int:
    """Trading days held: sessions after the entry close up to the exit close."""
    return _through(window, last) - _through(window, first)


def _sma(closes: pd.Series, window: int) -> pd.Series:
    return closes.rolling(window, min_periods=window).mean()


def _needs(closes: pd.Series, days: int, what: str) -> pd.Series:
    closes = closes.dropna().sort_index()
    if len(closes) <= days:
        raise DomainError(f"Not enough price history for {what}")
    return closes


def _turns(
    buy: pd.Series, sell: pd.Series, since: Optional[date] = None
) -> List[Signal]:
    """A signal on the first of consecutive event days."""
    buy = buy.fillna(False).astype(bool)
    sell = sell.fillna(False).astype(bool)
    starts_buy = buy & ~buy.shift(1, fill_value=True)
    starts_sell = sell & ~sell.shift(1, fill_value=True)
    found = []
    for day, is_buy, is_sell in zip(buy.index, starts_buy, starts_sell):
        if since is not None and day.date() < since:
            continue
        if is_buy:
            found.append(Signal(day.date(), "buy"))
        elif is_sell:
            found.append(Signal(day.date(), "sell"))
    return found


def _crosses(line: pd.Series, level: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Days `line` crosses above and below `level`; nothing until both are known."""
    before, level_before = line.shift(1), level.shift(1)
    return (
        (line > level) & (before <= level_before),
        (line < level) & (before >= level_before),
    )


def golden_cross_signals(
    closes: pd.Series, since: Optional[date] = None
) -> List[Signal]:
    """50-day SMA crossing above (buy) or below (sell) the 200-day SMA."""
    closes = _needs(closes, SMA_SLOW, f"the {SMA_SLOW}-day average")
    return _turns(*_crosses(_sma(closes, SMA_FAST), _sma(closes, SMA_SLOW)), since)


def trend_signals(closes: pd.Series, since: Optional[date] = None) -> List[Signal]:
    """The close crossing above (buy) or below (sell) its 200-day SMA."""
    closes = _needs(closes, SMA_SLOW, f"the {SMA_SLOW}-day average")
    return _turns(*_crosses(closes, _sma(closes, SMA_SLOW)), since)


def rsi_reversion_signals(
    closes: pd.Series, since: Optional[date] = None
) -> List[Signal]:
    """Daily RSI(14) climbing back above 30 (buy) or falling back below 70 (sell)."""
    closes = _needs(closes, RSI_WINDOW, f"RSI({RSI_WINDOW})")
    value = rsi(closes)
    before = value.shift(1)
    return _turns(
        (before < OVERSOLD) & (value >= OVERSOLD),
        (before > OVERBOUGHT) & (value <= OVERBOUGHT),
        since,
    )


def bollinger_signals(closes: pd.Series, since: Optional[date] = None) -> List[Signal]:
    """The close coming back inside the 20-day, 2σ bands: above the lower band
    (buy) or below the upper band (sell)."""
    closes = _needs(closes, BOLLINGER_WINDOW, "Bollinger Bands")
    middle = _sma(closes, BOLLINGER_WINDOW)
    width = BOLLINGER_WIDTH * closes.rolling(BOLLINGER_WINDOW).std(ddof=0)
    lower, upper = middle - width, middle + width
    below, above = closes < lower, closes > upper
    return _turns(
        below.shift(1, fill_value=False) & (closes >= lower),
        above.shift(1, fill_value=False) & (closes <= upper),
        since,
    )


def breakout_signals(closes: pd.Series, since: Optional[date] = None) -> List[Signal]:
    """A close above the prior 55-day high (buy) or below the prior 20-day low (sell)."""
    closes = _needs(closes, BREAKOUT_ENTRY, f"a {BREAKOUT_ENTRY}-day high")
    high = closes.rolling(BREAKOUT_ENTRY).max().shift(1)
    low = closes.rolling(BREAKOUT_EXIT).min().shift(1)
    return _turns(closes > high, closes < low, since)


def _macd_turns(closes: pd.Series, since: Optional[date] = None) -> List[Signal]:
    return [Signal(s.date, s.action) for s in macd_signals(closes, since)]


StrategyId = Literal[
    "gfs",
    "macd",
    "golden_cross",
    "trend_200",
    "rsi_reversion",
    "bollinger_reversion",
    "breakout",
]


@dataclass(frozen=True)
class Strategy:
    id: StrategyId
    name: str
    rule: str
    signals: Callable[[pd.Series, Optional[date]], List[Signal]]


STRATEGIES: Dict[str, Strategy] = {
    s.id: s
    for s in (
        Strategy(
            "gfs",
            "Grandfather-father-son RSI",
            "Buy when monthly, weekly and daily RSI(14) are all below 30; sell when all are above 70",
            gfs_signals,
        ),
        Strategy(
            "macd",
            "MACD with 200-day trend",
            "Buy a MACD up-cross below zero above the 200-day EMA; sell a down-cross above zero below it",
            _macd_turns,
        ),
        Strategy(
            "golden_cross",
            "Golden / death cross",
            "Buy when the 50-day average crosses above the 200-day; sell when it crosses below",
            golden_cross_signals,
        ),
        Strategy(
            "trend_200",
            "200-day trend",
            "Buy when the close crosses above its 200-day average; sell when it crosses below",
            trend_signals,
        ),
        Strategy(
            "rsi_reversion",
            "RSI mean reversion",
            "Buy when daily RSI(14) climbs back above 30; sell when it falls back below 70",
            rsi_reversion_signals,
        ),
        Strategy(
            "bollinger_reversion",
            "Bollinger Band reversion",
            "Buy when the close returns above the lower band (20 days, 2σ); sell when it returns below the upper band",
            bollinger_signals,
        ),
        Strategy(
            "breakout",
            "55/20-day breakout",
            "Buy a close above the prior 55-day high; sell a close below the prior 20-day low",
            breakout_signals,
        ),
    )
}


@dataclass(frozen=True)
class StrategyRun:
    strategy: Strategy
    result: Optional[Backtest]
    last_signal: Optional[Signal]
    error: Optional[str]


def backtest_all(closes: pd.Series, start: date) -> List[StrategyRun]:
    """Every strategy over the same window; a rule without enough history gets its error."""
    runs = []
    for strategy in STRATEGIES.values():
        try:
            signals = strategy.signals(closes, start)
            result = backtest(closes, signals, start)
        except DomainError as error:
            runs.append(StrategyRun(strategy, None, None, str(error)))
            continue
        runs.append(
            StrategyRun(strategy, result, signals[-1] if signals else None, None)
        )
    return runs
