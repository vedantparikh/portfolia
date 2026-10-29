"""Rule-based strategy signals: RSI, GFS and MACD with the trend filter."""

from datetime import date

import numpy as np
import pandas as pd
import polars as pl
import pytest

from core.auth.dependencies import get_current_user
from core.database.models import User
from core.domain.strategies import (
    Signal,
    _last_per,
    backtest,
    gfs,
    gfs_signals,
    live_rsi,
    macd_signals,
    rsi,
)
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
    body = client.get(
        "/api/v1/statistical-indicators/strategies/backtest?symbol=DIP&strategy=macd&years=20"
    ).json()
    assert [(t["open"], t["entry_price"] > 185) for t in body["trades"]] == [
        (True, True)
    ]
    assert body["buy_and_hold_pct"] > body["total_return_pct"] > 0
    gfs_run = client.get(
        "/api/v1/statistical-indicators/strategies/backtest?symbol=DOWN&strategy=gfs&years=20"
    ).json()
    assert gfs_run["trades"][0]["open"] is True
    bad = client.get(
        "/api/v1/statistical-indicators/strategies/backtest?symbol=DIP&strategy=other"
    )
    assert bad.status_code == 422
    signed_in["NEW"] = daily(np.linspace(50, 60, 100))
    too_short = client.get("/api/v1/statistical-indicators/strategies/gfs?symbol=NEW")
    assert too_short.status_code == 400


@pytest.mark.parametrize("rule", ["M", "W"])
def test_live_rsi_only_uses_what_each_day_knew(rule):
    rng = np.random.default_rng(3)
    closes = daily(100 * np.exp(rng.normal(0, 0.02, 700).cumsum()))
    live = live_rsi(closes, rule)

    for i in [400, 401, 455, 512, 699]:
        known = closes.iloc[: i + 1]
        assert live.iloc[i] == pytest.approx(rsi(_last_per(known, rule)).iloc[-1])
    assert live.iloc[:30].isna().all()


def test_past_gfs_signals_end_in_todays_reading():
    falling = daily(np.linspace(300, 50, 800))

    found = gfs_signals(falling)

    assert found and found[-1].action == "buy"
    assert gfs(falling).action == "buy"
    assert gfs_signals(falling, since=date(2099, 1, 1)) == []


def test_backtest_by_hand():
    closes = daily([100, 100, 105, 110, 104, 105, 120, 126])
    days = [d.date() for d in closes.index]
    signals = [
        Signal(days[1], "buy"),
        Signal(days[2], "buy"),
        Signal(days[3], "sell"),
        Signal(days[4], "sell"),
        Signal(days[5], "buy"),
    ]

    result = backtest(closes, signals, days[0])

    assert [(t.entry_price, t.exit_price, t.open) for t in result.trades] == [
        (100.0, 110.0, False),
        (105.0, 126.0, True),
    ]
    assert [t.return_pct for t in result.trades] == pytest.approx([10.0, 20.0])
    assert result.total_return_pct == pytest.approx(32.0)
    assert result.win_rate_pct == 100.0
    assert result.average_return_pct == pytest.approx(15.0)
    assert result.buy_and_hold_pct == pytest.approx(26.0)
    # Held over sessions 2-3 and 6-7 of 7
    assert result.days_invested_pct == pytest.approx(4 / 7 * 100)


def test_backtest_without_trades_and_without_history():
    closes = daily([100, 90, 95])
    result = backtest(
        closes, [Signal(closes.index[1].date(), "sell")], closes.index[0].date()
    )
    assert (result.trades, result.win_rate_pct, result.total_return_pct) == (
        [],
        None,
        0.0,
    )
    assert result.buy_and_hold_pct == pytest.approx(-5.0)
    with pytest.raises(DomainError):
        backtest(closes, [], date(2099, 1, 1))
