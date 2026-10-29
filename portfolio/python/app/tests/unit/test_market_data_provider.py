"""Yahoo is the only market-data provider, and symbol search has one path."""

import asyncio
import json
import threading
import time
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pandas as pd

from api.v1.market import stock
from core.database.redis_client import RedisClient
from core.services.market_data import yahoo
from core.services.market_data.yahoo import YahooMarketDataProvider
from core.services.market_data_service import MarketDataService
from main import app


class _Redis:
    def __init__(self):
        self.data = {}
        self.pipelines = []

    def mget(self, keys):
        return {key: self.data[key] for key in keys if key in self.data}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex_seconds=None):
        self.data[key] = value

    def mset(self, items, ex_seconds=None):
        self.pipelines.append(ex_seconds)
        self.data.update(items)


class _Prices:
    def __init__(self):
        self.calls = 0

    async def current_prices(self, symbols):
        self.calls += 1
        return {symbol: Decimal("10") for symbol in symbols}


def test_price_cache_writes_one_pipeline():
    provider = _Prices()
    cache = _Redis()
    service = MarketDataService(provider=provider, redis_client=cache)

    first = asyncio.run(service.get_current_prices(["aapl", "msft"]))
    second = asyncio.run(service.get_current_prices(["AAPL"]))

    assert first == {"AAPL": Decimal("10"), "MSFT": Decimal("10")}
    assert second == {"AAPL": Decimal("10")}
    assert provider.calls == 1
    assert cache.pipelines == [service.price_cache_ttl]


def test_holdings_read_the_price_cache_and_do_not_call_yahoo():
    provider = _Prices()
    service = MarketDataService(provider=provider, redis_client=_Redis())

    prices = asyncio.run(service.get_current_prices(["AAPL"], fetch=False))

    assert prices == {}
    assert provider.calls == 0


def test_worker_refresh_stores_prices_for_two_intervals():
    from config import settings

    provider = _Prices()
    cache = _Redis()
    service = MarketDataService(provider=provider, redis_client=cache)

    asyncio.run(service.get_current_prices(["AAPL"], refresh=True))

    assert provider.calls == 1
    assert cache.pipelines == [
        max(service.price_cache_ttl, 2 * settings.WORKER_INTERVAL_SECONDS)
    ]


def test_search_listings_drop_non_tradeable_quotes():
    class Provider:
        async def search(self, query):
            return [
                {
                    "symbol": "AAPL",
                    "exchange": "Nasdaq",
                    "quote_type": "EQUITY",
                    "long_name": "Apple",
                    "short_name": "Apple",
                },
                {
                    "symbol": "^GSPC",
                    "exchange": "SNP",
                    "quote_type": "INDEX",
                    "long_name": "S&P 500",
                    "short_name": "S&P 500",
                },
            ]

    service = MarketDataService(provider=Provider(), redis_client=_Redis())
    listings = asyncio.run(service.search_listings("apple"))
    assert listings == [
        {
            "symbol": "AAPL",
            "exchange": "Nasdaq",
            "quote_type": "EQUITY",
            "name": "Apple",
        }
    ]


def test_daily_history_is_split_adjusted_not_dividend_adjusted(monkeypatch):
    index = pd.date_range("2024-01-02", periods=2, tz="UTC")
    frame = pd.DataFrame(
        {
            "Close": [10.0, 11.0],
            "Stock Splits": [0.0, 2.0],
            "Dividends": [0.0, 0.4],
        },
        index=index,
    )
    seen = {}

    class Ticker:
        def __init__(self, symbol):
            seen["symbol"] = symbol

        def history(self, **kwargs):
            seen["kwargs"] = kwargs
            return frame

    monkeypatch.setattr(yahoo.yf, "Ticker", Ticker)
    provider = YahooMarketDataProvider(attempts=1)
    result = asyncio.run(provider.daily_history("aapl"))

    assert seen["kwargs"]["auto_adjust"] is False
    assert seen["kwargs"]["actions"] is True
    assert result["close"]["2024-01-02"] == 10.0
    assert result["splits"] == {"2024-01-03": 2.0}
    assert result["dividends"] == {"2024-01-03": 0.4}


def test_yahoo_retries_then_returns(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(yahoo.asyncio, "sleep", fake_sleep)
    calls = {"n": 0}

    def work():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("down")
        return "ok"

    provider = YahooMarketDataProvider(attempts=3, base_delay=0.5)
    assert asyncio.run(provider.run(work)) == "ok"
    assert sleeps == [0.5, 1.0]


def test_yahoo_limits_concurrent_calls():
    provider = YahooMarketDataProvider(concurrency=1, attempts=1)
    state = {"current": 0, "peak": 0}
    lock = threading.Lock()

    def work():
        with lock:
            state["current"] += 1
            state["peak"] = max(state["peak"], state["current"])
        time.sleep(0.05)
        with lock:
            state["current"] -= 1
        return 1

    async def main():
        await asyncio.gather(*(provider.run(work) for _ in range(3)))

    asyncio.run(main())
    assert state["peak"] == 1


def test_redis_mset_uses_one_pipeline(monkeypatch):
    pipe = MagicMock()
    client = MagicMock()
    client.pipeline.return_value = pipe

    class Ctx:
        def __init__(self, pool):
            self.pool = pool

        def __enter__(self):
            return client

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(RedisClient, "RedisContextManager", Ctx)
    redis = RedisClient.__new__(RedisClient)
    redis.ex_seconds = 60
    redis.connection_pool = object()
    redis.mset({"yfinance:price:AAPL": "10"}, ex_seconds=60)

    key, value = pipe.set.call_args.args
    assert json.loads(key) == "yfinance:price:AAPL"
    assert json.loads(value) == "10"
    assert pipe.set.call_args.kwargs["ex"] == 60
    pipe.execute.assert_called_once()


def test_symbol_search_is_the_only_endpoint(monkeypatch):
    async def quotes(query):
        if query == "AAPL":
            return [
                {
                    "symbol": "AAPL",
                    "short_name": "Apple",
                    "long_name": "Apple Inc.",
                    "quote_type": "EQUITY",
                    "exchange": "Nasdaq",
                    "market": "us_market",
                    "currency": "USD",
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "market_cap": 1,
                }
            ]
        return []

    monkeypatch.setattr(stock.market_data_service, "search_quotes", quotes)
    monkeypatch.setattr(stock, "is_rate_limited", lambda *args, **kwargs: False)
    app.dependency_overrides[stock.get_optional_current_user] = lambda: None
    try:
        from fastapi.testclient import TestClient

        client = TestClient(app)
        found = client.get("/api/v1/stock/symbols?name=AAPL")
        missing = client.get("/api/v1/stock/symbols?name=NOPE")
        gone = client.get("/api/v1/market-data/search?query=AAPL")
    finally:
        app.dependency_overrides.clear()

    assert found.status_code == 200
    assert found.json()[0]["symbol"] == "AAPL"
    assert missing.status_code == 404
    assert gone.status_code == 404


def test_ranges_request_unadjusted_bars(monkeypatch):
    seen = {}

    class Ticker:
        def __init__(self, symbol):
            self.splits = pd.Series({pd.Timestamp("2024-06-01"): 2.0})
            self.history_metadata = {"currency": "EUR"}

        def history(self, **kwargs):
            seen.update(kwargs)
            return pd.DataFrame(
                {"Low": [1.0], "High": [2.0]},
                index=pd.date_range("2024-01-02", periods=1, tz="UTC"),
            )

    monkeypatch.setattr(yahoo.yf, "Ticker", Ticker)
    result = asyncio.run(
        YahooMarketDataProvider(attempts=1).ranges(
            "SAP.DE", date(2024, 1, 1), date(2024, 1, 31)
        )
    )
    assert seen["auto_adjust"] is False
    assert result["currency"] == "EUR"
    assert result["ranges"]["2024-01-02"] == [1.0, 2.0]
    assert result["splits"]["2024-06-01"] == 2.0


def test_a_frozen_quote_gives_way_to_the_last_daily_close(monkeypatch):
    now = pd.Timestamp.now(tz="UTC").floor("D")
    bars = pd.DataFrame(
        {"Close": [25.02, 26.04]}, index=[now - pd.Timedelta(days=2), now]
    )

    class Ticker:
        def __init__(self, symbol, quoted_at):
            self.ticker = symbol
            self.info = {"regularMarketPrice": 18.705, "regularMarketTime": quoted_at}

        def history(self, **kwargs):
            return bars

    class Tickers:
        def __init__(self, symbols):
            fresh = int(now.timestamp()) + 3600
            self.tickers = {
                "82W.SG": Ticker("82W.SG", 1721764800),
                "SAP.F": Ticker("SAP.F", fresh),
            }

    monkeypatch.setattr(yahoo.yf, "Tickers", Tickers)
    prices = asyncio.run(
        YahooMarketDataProvider(attempts=1).current_prices(["82W.SG", "SAP.F"])
    )

    assert prices == {"82W.SG": Decimal("26.04"), "SAP.F": Decimal("18.705")}
