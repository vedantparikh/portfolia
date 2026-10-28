"""
Returns and risk over a period of the daily value series. Percent units (15.0).
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyxirr

TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.03


def compute_daily_returns(history: pd.DataFrame, opening_value: float) -> pd.Series:
    """
    Cash-flow-adjusted daily returns from a daily value series.

    Buys (`inflow`) are treated as arriving at the start of the day and sales/dividends
    (`outflow`) as leaving at the end of the day:

        r_t = (V_t + outflow_t) / (V_{t-1} + inflow_t) - 1

    This keeps the denominator non-negative, so a full exit is measured correctly
    (instead of producing -100%), and a first purchase measures close vs. cost.
    Days with no capital at risk (denominator <= 0) get NaN.
    """
    prev_value = history["value"].shift(1)
    if len(prev_value):
        prev_value.iloc[0] = opening_value
    denominator = prev_value + history["inflow"]
    numerator = history["value"] + history["outflow"]
    returns = numerator / denominator.where(denominator > 0) - 1
    return returns.replace([np.inf, -np.inf], np.nan)


def twr_pct(returns: pd.Series) -> Optional[float]:
    returns = returns.dropna()
    if returns.empty:
        return None
    return float(((1 + returns).prod() - 1) * 100)


def annualize_pct(total_pct: Optional[float], days: int) -> Optional[float]:
    """Annualised rate, only for periods of about a year or more (shorter ones would extrapolate)."""
    if total_pct is None or days < 360 or total_pct <= -100:
        return None
    return float(((1 + total_pct / 100) ** (365.25 / days) - 1) * 100)


def xirr_pct(flows: List[Tuple[date, float]]) -> Optional[float]:
    """Annualised money-weighted return. Investor view: money in < 0, money out > 0."""
    flows = [(d, a) for d, a in flows if a]
    if not (any(a > 0 for _, a in flows) and any(a < 0 for _, a in flows)):
        return None
    try:
        rate = pyxirr.xirr([d for d, _ in flows], [a for _, a in flows])
    except (pyxirr.InvalidPaymentsError, ValueError):
        return None
    return None if rate is None or not np.isfinite(rate) else float(rate * 100)


def deannualize_pct(rate_pct: Optional[float], days: int) -> Optional[float]:
    """The cumulative return over `days` that an annual rate corresponds to."""
    if rate_pct is None:
        return None
    return float(((1 + rate_pct / 100) ** (days / 365) - 1) * 100)


def volatility_pct(returns: pd.Series) -> Optional[float]:
    returns = returns.dropna()
    if len(returns) < 2:
        return None
    return float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100)


def sharpe_ratio(
    returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE
) -> Optional[float]:
    returns = returns.dropna()
    if len(returns) < 2 or returns.std() == 0:
        return None
    daily_rf = (1 + risk_free_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    return float(
        (returns.mean() - daily_rf) / returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    )


def max_drawdown_pct(returns: pd.Series) -> Optional[float]:
    """Largest fall from a peak of the compounded return curve; the period start counts as a peak."""
    returns = returns.dropna()
    if returns.empty:
        return None
    equity = (1 + returns).cumprod()
    peak = equity.cummax().clip(lower=1.0)
    return float((equity / peak - 1).min() * 100)


def value_at_risk_pct(returns: pd.Series, confidence: float) -> Optional[float]:
    """Historical one-day VaR: the daily return at the (1 - confidence) quantile."""
    returns = returns.dropna()
    if returns.empty:
        return None
    return float(returns.quantile(1 - confidence) * 100)


def split_period(
    series: pd.DataFrame, start: Optional[date]
) -> Tuple[pd.DataFrame, float, date]:
    """
    The rows from `start` on, the value just before it and the period's start date.
    Without a start (or before the first row) the period begins at inception with 0.
    """
    first_day = series.index[0].date()
    if start is None or start <= first_day:
        return series, 0.0, first_day
    before = series[series.index < pd.Timestamp(start)]
    window = series[series.index >= pd.Timestamp(start)]
    return window, float(before["value"].iloc[-1]), start


def period_summary(
    series: pd.DataFrame, start: Optional[date] = None
) -> Dict[str, Any]:
    """Everything the performance view shows for one period, from one daily series."""
    window, opening_value, start_date = split_period(series, start)
    if window.empty:
        return {}
    returns = compute_daily_returns(window, opening_value)
    end_date = window.index[-1].date()
    end_value = float(window["value"].iloc[-1])
    deposits = float(window["inflow"].sum())
    withdrawals = float(window["outflow"].sum())
    net_contributions = deposits - withdrawals
    days = (end_date - start_date).days

    flows = [(start_date - timedelta(days=1), -opening_value)] if opening_value else []
    for day, row in window.iterrows():
        flows.append((day.date(), row["outflow"] - row["inflow"]))
    flows.append((end_date, end_value))

    total = twr_pct(returns)
    mwr_annual = xirr_pct(flows)
    valid = returns.dropna()
    best = valid.idxmax() if not valid.empty else None
    worst = valid.idxmin() if not valid.empty else None
    return {
        "start_date": start_date,
        "end_date": end_date,
        "trading_days": len(window),
        "start_value": opening_value,
        "end_value": end_value,
        "deposits": deposits,
        "withdrawals": withdrawals,
        "net_contributions": net_contributions,
        "profit": end_value - opening_value - net_contributions,
        "twr_pct": total,
        "twr_annualized_pct": annualize_pct(total, days),
        "mwr_pct": deannualize_pct(mwr_annual, (end_date - flows[0][0]).days),
        "mwr_annualized_pct": mwr_annual,
        "volatility_pct": volatility_pct(returns),
        "sharpe_ratio": sharpe_ratio(returns),
        "max_drawdown_pct": max_drawdown_pct(returns),
        "best_day": {"date": best.date(), "return_pct": float(valid[best] * 100)}
        if best is not None
        else None,
        "worst_day": {"date": worst.date(), "return_pct": float(valid[worst] * 100)}
        if worst is not None
        else None,
    }
