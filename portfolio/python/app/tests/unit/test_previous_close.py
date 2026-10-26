"""Previous close is the last finished session, in that listing's timezone."""

from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from core.services.market_data import yahoo
from core.services.market_data.sessions import previous_session_close
from core.services.market_data.yahoo import YahooMarketDataProvider
from core.services.market_data_service import MarketDataService


def _bars(dates, values, tz=None):
    index = pd.to_datetime(dates)
    if tz:
        index = index.tz_localize(tz)
    return pd.Series(values, index=index)


def test_weekend_uses_friday_not_the_older_row():
    bars = _bars(["2025-01-02", "2025-01-03"], [10, 12])
    now = datetime(2025, 1, 4, 15, tzinfo=timezone.utc)
    assert previous_session_close(bars, now) == Decimal("12.0")


def test_open_session_uses_the_prior_bar():
    bars = _bars(["2025-01-03", "2025-01-06"], [12, 13])
    now = datetime(2025, 1, 6, 15, tzinfo=timezone.utc)
    assert previous_session_close(bars, now) == Decimal("12.0")


def test_next_morning_uses_the_session_that_finished():
    bars = _bars(["2025-01-03", "2025-01-06"], [12, 13])
    now = datetime(2025, 1, 7, 8, tzinfo=timezone.utc)
    assert previous_session_close(bars, now) == Decimal("13.0")


def test_exchange_timezone_keeps_the_session_open_after_utc_midnight():
    bars = _bars(["2025-01-03", "2025-01-06"], [100, 110], tz="America/New_York")
    now = datetime(2025, 1, 7, 0, 30, tzinfo=timezone.utc)
    assert previous_session_close(bars, now) == Decimal("100.0")


def test_only_the_current_session_has_no_previous_close():
    bars = _bars(["2025-01-06"], [13])
    now = datetime(2025, 1, 6, 15, tzinfo=timezone.utc)
    assert previous_session_close(bars, now) is None


def test_close_series_accepts_price_then_ticker():
    columns = pd.MultiIndex.from_product([["Close", "Open"], ["AAPL"]])
    data = pd.DataFrame(
        [[12.0, 1.0]], index=pd.to_datetime(["2025-01-03"]), columns=columns
    )
    assert float(yahoo._close_series(data, "aapl").iloc[0]) == 12.0


def test_provider_reads_a_single_symbol_and_a_batch(monkeypatch):
    now = datetime(2025, 1, 4, 15, tzinfo=timezone.utc)
    index = pd.to_datetime(["2025-01-02", "2025-01-03"])
    seen = {}

    def download(**kwargs):
        seen.update(kwargs)
        if kwargs["tickers"] == ["AAPL"]:
            return pd.DataFrame(
                {"Close": [10.0, 12.0], "Open": [1.0, 1.0]}, index=index
            )
        columns = pd.MultiIndex.from_product([["MSFT", "SAP.DE"], ["Close", "Open"]])
        return pd.DataFrame(
            [[20.0, 1, 30.0, 1], [22.0, 1, 33.0, 1]], index=index, columns=columns
        )

    monkeypatch.setattr(yahoo.yf, "download", download)
    provider = YahooMarketDataProvider(attempts=1)
    assert provider._previous_closes(["AAPL"], now=now) == {"AAPL": Decimal("12.0")}
    assert provider._previous_closes(["MSFT", "SAP.DE"], now=now) == {
        "MSFT": Decimal("22.0"),
        "SAP.DE": Decimal("33.0"),
    }
    assert seen["period"] == "10d"
    assert seen["auto_adjust"] is False


def test_previous_close_cache_key_includes_the_utc_date():
    service = MarketDataService(provider=object(), redis_client=object())
    key = service._get_yesterdays_close_cache_key("aapl")
    assert key == (
        "yfinance:yesterday_close:AAPL:" + datetime.now(timezone.utc).date().isoformat()
    )
