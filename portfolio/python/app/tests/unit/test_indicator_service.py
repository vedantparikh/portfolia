"""POST /statistical-indicators/calculate end to end: order, warm-up, several indicator classes."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from core.auth.dependencies import get_optional_current_user
from core.services.enhanced_statistical_service import period_start
from core.services.market_data_service import MarketDataService
from main import app

ta = pytest.importorskip("ta")


@pytest.fixture
def market(monkeypatch):
    days = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=320)
    rng = np.random.default_rng(3)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(days))))
    frame = pd.DataFrame(
        {
            "Date": days,
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 1e6,
        }
    )
    calls = []

    async def fetch(
        self, symbol, period="max", interval="1d", start_date=None, end_date=None
    ):
        calls.append((period, start_date))
        window = (
            frame
            if start_date is None
            else frame[frame["Date"] >= pd.Timestamp(start_date)]
        )
        # like the real service: newest first
        return window.sort_values("Date", ascending=False)

    monkeypatch.setattr(MarketDataService, "fetch_ticker_data", fetch)
    app.dependency_overrides[get_optional_current_user] = lambda: None
    return frame, calls


def _calculate(client, period, *names):
    response = client.post(
        "/api/v1/statistical-indicators/calculate",
        json={
            "symbol": "ACME",
            "period": period,
            "indicators": [{"indicator_name": n, "parameters": {}} for n in names],
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _series(body):
    return {
        s["display_name"].split("(")[-1].rstrip(")"): [p["value"] for p in s["data"]]
        for s in body["indicator_series"]
    }


def test_indicators_are_calculated_forward_in_time_with_warm_up(client, market):
    frame, calls = market
    body = _calculate(client, "30d", "rsi_indicator", "macd_indicator")

    shown = [row["date"][:10] for row in body["data"]]
    assert shown == sorted(shown)
    assert shown[0] >= str(period_start("30d", datetime.now()))
    assert calls[0][1] is not None, "fetched with extra history"

    series = _series(body)
    assert {"rsi", "macd", "signal", "histogram"} <= set(series)
    assert all(len(values) == len(shown) for values in series.values())
    expected_rsi = ta.momentum.RSIIndicator(frame["Close"], 14).rsi().iloc[-1]
    expected_macd = ta.trend.MACD(frame["Close"]).macd().iloc[-1]
    assert series["rsi"][-1] == pytest.approx(expected_rsi)
    assert series["macd"][-1] == pytest.approx(expected_macd)


def test_max_period_fetches_by_period(client, market):
    _, calls = market
    _calculate(client, "max", "rsi_indicator")
    assert calls == [("max", None)]


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("30d", date(2026, 9, 16)),
        ("3mo", date(2026, 7, 17)),
        ("1y", date(2025, 10, 16)),
        ("ytd", date(2026, 1, 1)),
        ("max", None),
        ("bogus", None),
    ],
)
def test_period_start(period, expected):
    assert period_start(period, datetime(2026, 10, 16, 12)) == expected


def test_validation_reports_an_unknown_indicator_instead_of_failing():
    from core.schemas.statistical_indicators import IndicatorConfiguration
    from core.services.indicator_registry_service import IndicatorRegistryService

    errors = IndicatorRegistryService(db=None).validate_indicator_configuration(
        IndicatorConfiguration(id="x", indicator_name="nope", parameters={})
    )

    assert [(e.parameter_name, e.provided_value) for e in errors] == [
        ("indicator_name", "nope")
    ]
