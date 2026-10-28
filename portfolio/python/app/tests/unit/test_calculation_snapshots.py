"""
Characterisation snapshots of the calculation engine and the technical indicators.

Inputs are generated with plain math (no RNG), so they are identical across numpy /
pandas / polars versions; only our outputs can change. A failure means a number the
app shows has changed: either it is an intended fix (regenerate with
UPDATE_SNAPSHOTS=1 and explain the change in the commit) or a regression.
"""

import json
import math
import os
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import polars as pl
import pytest

from core.database.models import Transaction, TransactionType
from modules.analytics.advance_risk import (
    PortfolioAdvanceRiskMetricsService,
)
from modules.analytics.calculations import PortfolioCalculationService
from modules.analytics.risk import PortfolioRiskMetricsService
from modules.portfolios.service import compute_position
from utils.indicators.momentum_indicators import MomentumIndicators
from utils.indicators.trend_indicators import TrendIndicators
from utils.indicators.volatility_indicators import VolatilityIndicators
from utils.indicators.volume_indicators import VolumeIndicators

SNAPSHOT = Path(__file__).parent / "snapshots" / "calculations.json"
DAYS = pd.bdate_range("2024-01-01", periods=320)


def _price(asset, i):
    drift = 1.0006 if asset == 1 else 1.0002
    wave = 0.08 * math.sin(i / (6.0 + asset)) + 0.03 * math.cos(i / 2.3)
    return round(100 * asset * (drift**i) * (1 + wave), 4)


def _ohlcv():
    rows = []
    for i in range(len(DAYS)):
        close = _price(1, i)
        rows.append(
            {
                "Open": round(close * (1 + 0.004 * math.sin(i)), 4),
                "High": round(close * (1.01 + 0.004 * abs(math.cos(i))), 4),
                "Low": round(close * (0.99 - 0.004 * abs(math.sin(i / 3))), 4),
                "Close": close,
                "Volume": float(1_000_000 + 250_000 * math.sin(i / 4)),
            }
        )
    return pl.DataFrame(rows)


def _tx(asset, kind, qty, price, day, fees="1.5"):
    t = Transaction(
        asset_id=asset,
        transaction_type=kind,
        quantity=Decimal(str(qty)),
        price=Decimal(str(price)),
        fees=Decimal(fees),
        taxes=Decimal("0"),
        transaction_date=DAYS[day]
        .to_pydatetime()
        .replace(hour=12, tzinfo=timezone.utc),
    )
    t.total_amount = Transaction.compute_total_amount(
        kind, t.quantity, t.price, t.fees, t.taxes
    )
    return t


def _transactions():
    B, S, D = TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND
    return [
        _tx(1, B, 10, _price(1, 0), 0),
        _tx(2, B, 5, _price(2, 3), 3),
        _tx(1, B, 7.5, _price(1, 60), 60),
        _tx(1, D, 17.5, "0.42", 90, fees="0"),
        _tx(2, B, 3, _price(2, 120), 120),
        _tx(1, S, 8, _price(1, 180), 180),
        _tx(2, S, 2, _price(2, 240), 240),
        _tx(1, B, 4, _price(1, 300), 300),
    ]


def _num(x):
    if x is None:
        return None
    x = float(x)
    if math.isnan(x) or math.isinf(x):
        return str(x)
    return round(x, 8)


async def _engine_outputs(monkeypatch):
    calc = PortfolioCalculationService(db=None)
    frames = {
        a: pd.DataFrame(
            {"Close": [_price(a, i) for i in range(len(DAYS))]},
            index=[d.date() for d in DAYS],
        )
        for a in (1, 2)
    }
    txs = _transactions()
    end = DAYS[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    combined = await _combined_history(calc, frames, txs, end, monkeypatch)

    twr = calc._calculate_twr(combined)
    current_value = float(combined["value"].iloc[-1])
    out = {
        "positions": {
            str(a): {
                k: _num(v)
                for k, v in compute_position(
                    [
                        t
                        for t in txs
                        if t.asset_id == a
                        and t.transaction_type != TransactionType.DIVIDEND
                    ]
                ).items()
                if not isinstance(v, list)
            }
            for a in (1, 2)
        },
        "history": {
            "rows": len(combined),
            "value_sum": _num(combined["value"].sum()),
            "value_last": _num(current_value),
            "inflow_sum": _num(combined["inflow"].sum()),
            "outflow_sum": _num(combined["outflow"].sum()),
            "sample": {
                str(d): _num(combined.loc[d, "value"]) for d in combined.index[::40]
            },
        },
        "twr": _num(twr),
        "cagr": _num(calc._calculate_cagr(twr, txs[0].transaction_date, end)),
        "volatility": _num(calc._calculate_volatility(combined)),
        "max_drawdown": _num(calc._calculate_max_drawdown(combined)),
        "xirr": _num(await calc._calculate_xirr(txs, current_value, None, end)),
    }

    risk = PortfolioRiskMetricsService.__new__(PortfolioRiskMetricsService)
    risk.TRADING_DAYS_PER_YEAR = 252
    risk.ANNUALIZED_RISK_FREE_RATE = 0.03
    returns = combined["daily_return"].dropna()
    mdd = risk._calculate_max_drawdown(returns)
    out["risk"] = {
        "volatility": _num(risk._calculate_volatility(returns)),
        "sharpe": _num(risk._calculate_sharpe_ratio(returns)),
        "sortino": _num(risk._calculate_sortino_ratio(returns)),
        "var95": _num(risk._calculate_var(returns)),
        "cvar95": _num(risk._calculate_cvar(returns)),
        "max_drawdown": _num(mdd),
        "calmar": _num(risk._calculate_calmar_ratio(returns, mdd)),
    }
    return out


async def _combined_history(calc, frames, txs, end, monkeypatch):
    by_symbol = {"A1": frames[1], "A2": frames[2]}

    class _Db:
        def __init__(self):
            self._asset = None

        def query(self, *a, **k):
            return self

        def filter(self, *conditions, **k):
            # Asset.id == <n>: pick the symbol from the right-hand literal
            for c in conditions:
                value = getattr(getattr(c, "right", None), "value", None)
                if value in (1, 2):
                    self._asset = value
            return self

        def first(self):
            return SimpleNamespace(symbol=f"A{self._asset}")

    calc.db = _Db()

    async def daily_history(symbol):
        frame = by_symbol[symbol]
        return {
            "close": pd.Series(
                frame["Close"].values, index=pd.to_datetime(frame.index)
            ),
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    monkeypatch.setattr(calc.market_data_service, "get_daily_history", daily_history)
    return await calc.get_portfolio_history(txs, None, end)


def _indicator_outputs():
    df = _ohlcv()
    out = {}
    for name, cls, method in [
        ("momentum", MomentumIndicators, "all_momentum_indicators"),
        ("trend", TrendIndicators, "all_trend_indicators"),
        ("volatility", VolatilityIndicators, "all_volatility_indicators"),
        ("volume", VolumeIndicators, "all_volume_indicators"),
    ]:
        result = getattr(cls(df.clone()), method)()
        tail = result.tail(5)
        out[name] = {
            col: [_num(v) for v in tail[col].to_list()]
            for col in sorted(result.columns)
            if result[col].dtype.is_numeric()
        }
    return out


def _price_frame(asset, gaps=False):
    close = [_price(asset, i) for i in range(len(DAYS))]
    df = pd.DataFrame(
        {
            "Open": [round(c * 0.998, 4) for c in close],
            "High": [round(c * 1.012, 4) for c in close],
            "Low": [round(c * 0.988, 4) for c in close],
            "Close": close,
            "Volume": [1_000_000 + 1000 * (i % 37) for i in range(len(DAYS))],
        },
        index=DAYS,
    )
    if gaps:
        # Holiday-like gaps exercise the forward-fill before pct_change
        df.loc[df.index[5::17], "Close"] = float("nan")
    return df


def _numbers(d):
    return {
        k: _num(v)
        if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)
        else str(v)
        for k, v in sorted(d.items())
    }


def _analytics_outputs():
    p1, p2 = _price_frame(1), _price_frame(2, gaps=True)
    adv = PortfolioAdvanceRiskMetricsService(db=None)
    beta, alpha = adv._calculate_beta_and_alpha(p1["Close"].pct_change().dropna(), p2)
    weights = pd.Series({"A1": 0.6, "A2": 0.4})
    asset_prices = pd.concat(
        [p1["Close"].rename("A1"), p2["Close"].rename("A2")], axis=1
    )
    return {
        "beta": _num(beta),
        "alpha": _num(alpha),
        "concentration": _num(adv._calculate_concentration_risk(weights)),
        "diversification": _num(
            adv._calculate_diversification_ratio(
                weights, asset_prices.ffill().pct_change().dropna()
            )
        ),
    }


def _compare(expected, actual, path=""):
    if isinstance(expected, dict):
        assert set(expected) == set(actual), (
            f"{path}: keys {set(expected) ^ set(actual)}"
        )
        for k in expected:
            _compare(expected[k], actual[k], f"{path}.{k}")
    elif isinstance(expected, list):
        assert len(expected) == len(actual), f"{path}: length"
        for i, (e, a) in enumerate(zip(expected, actual)):
            _compare(e, a, f"{path}[{i}]")
    elif isinstance(expected, float) and isinstance(actual, (int, float)):
        assert actual == pytest.approx(expected, rel=1e-7, abs=1e-7), path
    else:
        assert expected == actual, path


async def test_calculation_snapshots(monkeypatch):
    actual = {
        "engine": await _engine_outputs(monkeypatch),
        "indicators": _indicator_outputs(),
        "analytics": _analytics_outputs(),
    }
    actual = json.loads(json.dumps(actual))
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(actual, indent=1, sort_keys=True) + "\n")
        pytest.skip("snapshot written")
    _compare(json.loads(SNAPSHOT.read_text()), actual)
