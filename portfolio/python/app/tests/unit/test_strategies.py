"""Rule-based strategy signals: RSI, GFS and MACD with the trend filter."""

from datetime import date

import numpy as np
import pandas as pd
import polars as pl
import pytest

from core.auth.dependencies import get_current_user
from core.database.models import User
from core.domain.strategies import gfs, macd_signals, rsi
from core.errors import DomainError
from core.services.market_data_service import market_data_service
from main import app
from utils.indicators.momentum_indicators import MomentumIndicators


def daily(values, start="2022-01-03"):
    return pd.Series(
        values, index=pd.bdate_range(start, periods=len(values)), dtype=float
    )


def test_rsi_matches_the_indicator_chart():
    rng = np.random.default_rng(7)
    closes = daily(100 + rng.normal(0, 1, 300).cumsum())
    chart = MomentumIndicators(
        pl.DataFrame({"close": closes.to_numpy()})
    ).rsi_indicator()

    # Both start the Wilder average differently; after a warm-up they agree
    assert np.allclose(rsi(closes).to_numpy()[250:], chart["rsi"].to_numpy()[250:])


def test_rsi_by_hand():
    # 14 rises of 1 then a fall of 7: avg gain 1 → 13/14, avg loss 0 → 7/14 → RSI 65
    closes = daily([float(i) for i in range(15)] + [7.0])
    assert rsi(closes).iloc[14] == 100.0
    assert rsi(closes).iloc[15] == pytest.approx(100 - 100 / (1 + (13 / 14) / (7 / 14)))


def test_gfs_buy_sell_and_hold():
    falling = daily(np.linspace(300, 50, 800))
    rising = daily(np.linspace(50, 300, 800))
    mixed = daily(
        np.concatenate([np.linspace(50, 300, 760), np.linspace(300, 250, 40)])
    )

    result = gfs(falling)
    assert result.action == "buy"
    assert [r.timeframe for r in result.readings] == ["monthly", "weekly", "daily"]
    assert all(r.rsi < 30 for r in result.readings)
    assert result.readings[2].as_of == falling.index[-1].date()
    assert gfs(rising).action == "sell"
    assert gfs(mixed).action == "hold"


def test_gfs_needs_fifteen_months():
    with pytest.raises(DomainError):
        gfs(daily(np.linspace(50, 100, 200)))


def test_macd_buy_after_a_dip_in_an_uptrend():
    closes = daily(
        np.concatenate(
            [
                np.linspace(50, 200, 300),
                np.linspace(200, 185, 12),
                np.linspace(185, 215, 30),
            ]
        )
    )

    found = macd_signals(closes)

    assert [s.action for s in found] == ["buy"]
    (buy,) = found
    assert buy.macd < 0 < buy.close - buy.trend_ema
    assert buy.macd > buy.signal
    assert buy.date > closes.index[311].date()
    assert macd_signals(closes, since=date(2099, 1, 1)) == []


def test_macd_sell_after_a_bounce_in_a_downtrend():
    closes = daily(
        np.concatenate(
            [
                np.linspace(200, 50, 300),
                np.linspace(50, 65, 12),
                np.linspace(65, 35, 30),
            ]
        )
    )

    assert [s.action for s in macd_signals(closes)] == ["sell"]


def test_macd_needs_the_trend_line():
    with pytest.raises(DomainError):
        macd_signals(daily(np.linspace(50, 60, 150)))


@pytest.fixture
def signed_in(monkeypatch):
    histories = {}

    async def history(symbol):
        closes = histories.get(symbol)
        return None if closes is None else {"close": closes}

    monkeypatch.setattr(market_data_service, "get_daily_history", history)
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username="u")
    yield histories
    app.dependency_overrides.pop(get_current_user, None)


def test_strategy_endpoints(client, signed_in):
    signed_in["DOWN"] = daily(np.linspace(300, 50, 800))
    signed_in["DIP"] = daily(
        np.concatenate(
            [
                np.linspace(50, 200, 300),
                np.linspace(200, 185, 12),
                np.linspace(185, 215, 30),
            ]
        )
    )

    body = client.get(
        "/api/v1/statistical-indicators/strategies/gfs?symbol=down"
    ).json()
    assert (body["symbol"], body["action"]) == ("DOWN", "buy")
    assert [r["timeframe"] for r in body["readings"]] == ["monthly", "weekly", "daily"]

    body = client.get(
        "/api/v1/statistical-indicators/strategies/macd?symbol=DIP&since=2022-01-01"
    ).json()
    assert [s["action"] for s in body["signals"]] == ["buy"]

    missing = client.get("/api/v1/statistical-indicators/strategies/gfs?symbol=NONE")
    assert missing.status_code == 404
    short = client.get("/api/v1/statistical-indicators/strategies/macd?symbol=DOWN")
    assert short.status_code == 200
    signed_in["NEW"] = daily(np.linspace(50, 60, 100))
    too_short = client.get("/api/v1/statistical-indicators/strategies/gfs?symbol=NEW")
    assert too_short.status_code == 400
