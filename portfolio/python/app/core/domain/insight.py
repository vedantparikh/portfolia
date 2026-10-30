"""
What drove a period's return, from the daily series and its per-asset frames
(`valuation.daily_series_by_asset`). Percent units (15.0); money in the
portfolio currency.

- Contribution: on each day an asset adds (V_i + out_i − V_i,prev − in_i) to
  the portfolio's day, over the portfolio's denominator (V_prev + in, see
  `compute_daily_returns`). Those parts sum to the day's return, and weighting
  each day by the growth before it makes them sum to the period's TWR exactly:
  Σ_t r_t·G_{t−1} = G_T − 1. Profits sum to the portfolio's profit.
- Calendar returns: the daily returns compounded per month or year.
- Drawdowns: the compounded return curve below its running peak; the period
  start counts as a peak, as in `max_drawdown_pct`.
- Timing effect: actual profit minus the profit of the same flows at a steady
  daily rate equal to the period's TWR. Zero without flows after the start.
- Currency effect: for an asset quoted in another currency, the shares held
  overnight times the converted close times the day's change in the rate,
  q_{t−1}·P_t·(1 − X_{t−1}/X_t). Without trades it equals the asset's
  profit at a constant local price.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Literal, Mapping, Optional

import pandas as pd

from core.domain.returns import compute_daily_returns, split_period, twr_pct

Frequency = Literal["M", "Y"]


@dataclass(frozen=True)
class Contribution:
    asset_id: int
    start_value: float
    end_value: float
    inflow: float
    outflow: float
    profit: float
    contribution_pp: float


def _denominator(window: pd.DataFrame, opening_value: float) -> pd.Series:
    previous = window["value"].shift(1)
    if len(previous):
        previous.iloc[0] = opening_value
    return previous + window["inflow"]


def contributions(
    series: pd.DataFrame,
    assets: Mapping[int, pd.DataFrame],
    start: Optional[date] = None,
) -> List[Contribution]:
    """Every asset with a value or a flow in the period, largest profit first."""
    window, opening_value, _ = split_period(series, start)
    if window.empty:
        return []
    returns = compute_daily_returns(window, opening_value)
    denominator = _denominator(window, opening_value)
    denominator = denominator.where(returns.notna())
    growth_before = (1 + returns.fillna(0)).cumprod().shift(1, fill_value=1.0)

    found = []
    for asset_id, frame in assets.items():
        asset_window, asset_opening, _ = split_period(frame, start)
        if not (
            asset_opening
            or asset_window["value"].any()
            or asset_window["inflow"].any()
            or asset_window["outflow"].any()
        ):
            continue
        previous = asset_window["value"].shift(1)
        previous.iloc[0] = asset_opening
        change = (
            asset_window["value"]
            + asset_window["outflow"]
            - previous
            - asset_window["inflow"]
        )
        part = (change / denominator).fillna(0)
        inflow = float(asset_window["inflow"].sum())
        outflow = float(asset_window["outflow"].sum())
        end_value = float(asset_window["value"].iloc[-1])
        found.append(
            Contribution(
                asset_id=asset_id,
                start_value=asset_opening,
                end_value=end_value,
                inflow=inflow,
                outflow=outflow,
                profit=end_value - asset_opening - inflow + outflow,
                contribution_pp=float((part * growth_before).sum() * 100),
            )
        )
    return sorted(found, key=lambda c: c.profit, reverse=True)


@dataclass(frozen=True)
class CalendarReturn:
    period: str
    start: date
    end: date
    return_pct: float
    partial: bool


def calendar_returns(
    returns: pd.Series, frequency: Frequency, start: date, end: date
) -> List[CalendarReturn]:
    """
    Daily returns compounded per month ("M", "2026-03") or year ("Y", "2026").
    A period the window does not cover from its first to its last calendar day
    (the opening and the current one, usually) is `partial`.
    """
    returns = returns.dropna()
    if returns.empty:
        return []
    periods = returns.index.to_period(frequency)
    found = []
    for period, chunk in returns.groupby(periods):
        first = period.start_time.date()
        last = period.end_time.date()
        found.append(
            CalendarReturn(
                period=str(period),
                start=max(first, start),
                end=min(last, end),
                return_pct=float(((1 + chunk).prod() - 1) * 100),
                partial=start > first or end < last,
            )
        )
    return found


def benchmark_returns(closes: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    """The benchmark's close-to-close return on each portfolio day."""
    closes = closes.dropna().sort_index()
    closes.index = pd.DatetimeIndex(closes.index).tz_localize(None).normalize()
    closes = closes[~closes.index.duplicated(keep="last")]
    known = closes.reindex(closes.index.union(days)).ffill()
    previous = known.shift(1).reindex(days)
    return known.reindex(days) / previous - 1


@dataclass(frozen=True)
class Drawdown:
    peak_date: date
    trough_date: date
    recovery_date: Optional[date]
    depth_pct: float
    days_to_trough: int
    days_to_recover: Optional[int]


@dataclass(frozen=True)
class Drawdowns:
    underwater: pd.Series
    current_pct: float
    max_pct: float
    episodes: List[Drawdown]


def drawdowns(returns: pd.Series, start: date, limit: int = 5) -> Drawdowns:
    """The deepest `limit` falls below a previous peak, deepest first."""
    equity = (1 + returns.fillna(0)).cumprod()
    peak = equity.cummax().clip(lower=1.0)
    underwater = (equity / peak - 1) * 100
    underwater = underwater.where(underwater < -1e-9, 0.0)

    episodes = []
    peak_day = start
    trough_day: Optional[date] = None
    depth = 0.0
    for day, level in underwater.items():
        today = day.date()
        if level < 0:
            if trough_day is None or level < depth:
                trough_day, depth = today, float(level)
            continue
        if trough_day is not None:
            episodes.append(_episode(peak_day, trough_day, today, depth))
            trough_day, depth = None, 0.0
        peak_day = today
    if trough_day is not None:
        episodes.append(_episode(peak_day, trough_day, None, depth))
    episodes.sort(key=lambda e: e.depth_pct)
    return Drawdowns(
        underwater=underwater,
        current_pct=float(underwater.iloc[-1]) if len(underwater) else 0.0,
        max_pct=float(underwater.min()) if len(underwater) else 0.0,
        episodes=episodes[:limit],
    )


def _episode(
    peak: date, trough: date, recovery: Optional[date], depth: float
) -> Drawdown:
    return Drawdown(
        peak_date=peak,
        trough_date=trough,
        recovery_date=recovery,
        depth_pct=depth,
        days_to_trough=(trough - peak).days,
        days_to_recover=(recovery - peak).days if recovery else None,
    )


@dataclass(frozen=True)
class Timing:
    profit: float
    steady_profit: float
    timing_effect: float
    steady_daily_pct: float


def timing_effect(
    series: pd.DataFrame, start: Optional[date] = None
) -> Optional[Timing]:
    """Actual profit against the same flows at the period's steady TWR rate."""
    window, opening_value, _ = split_period(series, start)
    if window.empty:
        return None
    returns = compute_daily_returns(window, opening_value)
    total = twr_pct(returns)
    sessions = int(returns.notna().sum())
    if total is None or not sessions:
        return None
    rate = (1 + total / 100) ** (1 / sessions) - 1
    steady = opening_value
    for (_, row), valid in zip(window.iterrows(), returns.notna()):
        steady = (steady + row["inflow"]) * ((1 + rate) if valid else 1) - row[
            "outflow"
        ]
    net = float(window["inflow"].sum() - window["outflow"].sum())
    profit = float(window["value"].iloc[-1]) - opening_value - net
    steady_profit = steady - opening_value - net
    return Timing(
        profit=profit,
        steady_profit=steady_profit,
        timing_effect=profit - steady_profit,
        steady_daily_pct=rate * 100,
    )


def currency_effect(
    frame: pd.DataFrame, rate: pd.Series, start: Optional[date] = None
) -> float:
    """
    One asset's profit from its exchange rate over the period. `rate` is
    portfolio currency per unit of the quote currency (any minor-unit scaling
    included), indexed by date.
    """
    rate = rate.dropna().sort_index()
    rate.index = pd.DatetimeIndex(rate.index).tz_localize(None).normalize()
    rate = rate[~rate.index.duplicated(keep="last")]
    known = rate.reindex(rate.index.union(frame.index)).ffill().reindex(frame.index)
    held_overnight = frame["quantity"].shift(1, fill_value=0.0)
    daily = (held_overnight * frame["price"] * (1 - known.shift(1) / known)).fillna(0)
    window, _, _ = split_period(daily.to_frame("value"), start)
    return float(window["value"].sum())


def currency_effects(
    assets: Mapping[int, pd.DataFrame],
    rates: Mapping[int, pd.Series],
    start: Optional[date] = None,
) -> Dict[int, float]:
    """`currency_effect` for every asset that has a rate (a foreign quote)."""
    return {
        asset_id: currency_effect(assets[asset_id], rate, start)
        for asset_id, rate in rates.items()
        if asset_id in assets
    }
